"""The room a student shares with the rest of their own class.

A room is a grade and a group together. Pre-Medical XI and Pre-Engineering XI
sit different papers, so they are different rooms; there is no all-of-NISAAB
room, because a question about Biology helps nobody studying Computer Science.

A student only ever reads and writes in their own room. That is not a setting
but the shape of the thing: the room is worked out from their profile on every
call and never taken from the request, so there is nothing to tamper with.
"""

import logging
from contextlib import contextmanager
from uuid import uuid4

from edu_db.models import CommunityPost, StudentProfile, User
from edu_db.session import get_session_factory

from edu_core.community_rules import (
    MAX_REPLIES,
    PAGE_SIZE,
    check_body,
    display_name,
    room_name,
)
from edu_core.exceptions import NotFoundError
from edu_core.schemas.community import CommunityPostDto, CommunityRoomDto

logger = logging.getLogger(__name__)

class CommunityService:
    """Reading and writing in a student's own class room."""

    @contextmanager
    def _session(self):
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _room_of(db, user_id: str) -> tuple[int, str]:
        """The grade and group this student belongs to.

        Read from their profile every time rather than passed in, so a student
        cannot post into a class they are not in by changing a request.
        """
        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == user_id)
            .first()
        )
        if profile is None or not profile.group_code:
            raise NotFoundError(
                "Finish onboarding first - the room is your grade and group"
            )
        return profile.grade, profile.group_code

    def get_room(self, user_id: str) -> CommunityRoomDto:
        """The student's room, newest posts first, each with its replies."""
        with self._session() as db:
            grade, group_code = self._room_of(db, user_id)

            members = (
                db.query(StudentProfile)
                .filter(
                    StudentProfile.grade == grade,
                    StudentProfile.group_code == group_code,
                )
                .count()
            )

            rows = (
                db.query(CommunityPost, User)
                .outerjoin(User, CommunityPost.user_id == User.id)
                .filter(
                    CommunityPost.grade == grade,
                    CommunityPost.group_code == group_code,
                )
                .order_by(CommunityPost.created_at.desc())
                .limit(PAGE_SIZE * (MAX_REPLIES + 1))
                .all()
            )

            # One query for the whole room, then threaded here. Asking the
            # database again for every post's replies is the kind of thing
            # that reads fine with ten posts and falls over with a thousand.
            replies: dict[str, list[CommunityPostDto]] = {}
            tops: list[tuple[CommunityPost, User]] = []
            for post, user in rows:
                if post.parent_id:
                    replies.setdefault(post.parent_id, []).append(
                        self._as_dto(post, user, user_id)
                    )
                else:
                    tops.append((post, user))

            posts = []
            for post, user in tops[:PAGE_SIZE]:
                dto = self._as_dto(post, user, user_id)
                # Replies read oldest first - a conversation, not a stack
                dto.replies = sorted(
                    replies.get(post.id, []), key=lambda r: r.created_at
                )[:MAX_REPLIES]
                posts.append(dto)

            return CommunityRoomDto(
                grade=grade,
                group_code=group_code,
                room_name=room_name(grade, group_code),
                member_count=members,
                posts=posts,
            )

    def add_post(
        self, user_id: str, body: str, parent_id: str | None = None
    ) -> CommunityPostDto:
        """Write in the student's own room, or reply to something in it."""
        said = check_body(body)

        with self._session() as db:
            grade, group_code = self._room_of(db, user_id)

            parent = None
            if parent_id:
                parent = (
                    db.query(CommunityPost)
                    .filter(CommunityPost.id == parent_id)
                    .first()
                )
                # A reply must be to something in this student's own room, and
                # to a post rather than to another reply - one level, so a
                # thread stays readable.
                if (
                    parent is None
                    or parent.grade != grade
                    or parent.group_code != group_code
                ):
                    raise NotFoundError("That post is not in your room")
                if parent.parent_id:
                    parent_id = parent.parent_id

            post = CommunityPost(
                id=str(uuid4()),
                grade=grade,
                group_code=group_code,
                user_id=user_id,
                body=said,
                parent_id=parent_id,
            )
            db.add(post)
            db.commit()
            db.refresh(post)
            user = db.query(User).filter(User.id == user_id).first()
            return self._as_dto(post, user, user_id)

    def delete_post(self, user_id: str, post_id: str) -> None:
        """Remove something the student wrote. Only ever their own."""
        with self._session() as db:
            post = (
                db.query(CommunityPost)
                .filter(
                    CommunityPost.id == post_id,
                    CommunityPost.user_id == user_id,
                )
                .first()
            )
            if post is None:
                raise NotFoundError("That post is not yours, or no longer exists")
            db.delete(post)
            db.commit()

    @staticmethod
    def _as_dto(post: CommunityPost, user: User | None, reader_id: str) -> CommunityPostDto:
        return CommunityPostDto(
            id=post.id,
            body=post.body,
            author_name=display_name(
                getattr(user, "name", None), getattr(user, "email", None)
            ),
            is_mine=post.user_id == reader_id,
            created_at=post.created_at,
            replies=[],
        )
