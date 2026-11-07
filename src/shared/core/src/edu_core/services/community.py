"""The room a student shares with the rest of their own class.

A room is a grade and a group together. Pre-Medical XI and Pre-Engineering XI
sit different papers, so they are different rooms; there is no all-of-NISAAB
room, because a question about Biology helps nobody studying Computer
Science.

A student only ever reads and writes in their own room. That is not a setting
but the shape of the thing: the room is worked out from their profile on every
call and never taken from the request, so there is nothing to tamper with.

Moderation runs in four parts, and they are deliberately different from each
other:

The pattern filter refuses outright, before anything is stored. Contact
details have a shape, so there is no reason to let one through and clean up
afterwards.

The model flags but never deletes. It reads every post and says what it sees;
an administrator decides. A model that removed posts would one day remove a
good question and nobody would ever know.

Students report, and five students agreeing is a stronger signal than any
model.

The author is warned once, by the system rather than by a person, so a
teacher does not have to have the same conversation two hundred times.

None of it blocks the student. If the model is unreachable the post goes
through unreviewed, because a room that stops working whenever Vertex has a
bad minute costs more than the posts it would have caught.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from edu_db.models import (
    CommunityAttachment,
    CommunityPollOption,
    CommunityPollVote,
    CommunityPost,
    CommunityReport,
    StudentProfile,
    User,
)
from edu_db.session import get_session_factory

from edu_core.community_media import (
    MAX_ATTACHMENTS,
    check_attachment_count,
    check_upload,
    stored_path,
)
from edu_core.community_poll import check_options, check_question, tally, winning
from edu_core.community_review import (
    SELF_HARM,
    Review,
    message_for,
    read_review,
    review_prompt,
)
from edu_core.community_rules import (
    MAX_REPLIES,
    PAGE_SIZE,
    check_body,
    display_name,
    room_name,
)
from edu_core.exceptions import NotFoundError
from edu_core.personal_details import find_personal_details, refusal_message
from edu_core.schemas.community import (
    CommunityAttachmentDto,
    CommunityPollDto,
    CommunityPollOptionDto,
    CommunityPostDto,
    CommunityRoomDto,
    CommunityWarningDto,
)

logger = logging.getLogger(__name__)

# How long an attachment link lasts. Long enough to read a thread and play a
# voice note, short enough that a copied link is not a permanent public URL.
LINK_SECONDS = 6 * 60 * 60

# How many posts one student may write in a day. Generous for someone
# actually studying, and a ceiling on how much one person can fill a room
# with when nobody but an administrator can remove it.
DEFAULT_DAILY_POSTS = 40


class CommunityService:
    """Reading and writing in a student's own class room."""

    def __init__(self, storage=None, reviewer=None, daily_posts: int = DEFAULT_DAILY_POSTS):
        """
        storage: where attachments live. Optional, so a room with no
            attachments works in a setup without a bucket.
        reviewer: what reads each post. Injected so the service can be
            exercised without a model, and so a failing model is one
            argument rather than a network stub.
        """
        self.storage = storage
        self.reviewer = reviewer
        self.daily_posts = daily_posts

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

    # ---- who is where ---------------------------------------------------

    @staticmethod
    def _room_of(db, user_id: str) -> tuple[int, str]:
        """The grade and group this student belongs to.

        Read from their profile every time rather than passed in, so a
        student cannot post into a class they are not in by changing a
        request.
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

    # ---- reading --------------------------------------------------------

    def get_room(self, user_id: str, posts_left: int = 0) -> CommunityRoomDto:
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

            post_ids = [post.id for post, _ in rows]
            extras = self._extras_for(db, post_ids, user_id)

            # One query for the whole room, then threaded here. Asking the
            # database again for every post's replies is the kind of thing
            # that reads fine with ten posts and falls over with a thousand.
            replies: dict[str, list[CommunityPostDto]] = {}
            tops: list[tuple[CommunityPost, User]] = []
            for post, user in rows:
                if post.parent_id:
                    replies.setdefault(post.parent_id, []).append(
                        self._as_dto(post, user, user_id, extras)
                    )
                else:
                    tops.append((post, user))

            posts = []
            for post, user in tops[:PAGE_SIZE]:
                dto = self._as_dto(post, user, user_id, extras)
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
                posts_left_today=posts_left,
                warnings=self._warnings_for(db, user_id),
            )

    def _extras_for(self, db, post_ids: list[str], reader_id: str) -> dict:
        """Attachments, polls and the reader's own reports, in three queries.

        Fetched for the whole page at once. Asking per post would be four
        more queries per row, which is the difference between a page that
        opens and one that times out when a room gets busy.
        """
        if not post_ids:
            return {"attachments": {}, "options": {}, "votes": {}, "my_vote": {}, "reported": set()}

        attachments: dict[str, list[CommunityAttachment]] = {}
        for row in (
            db.query(CommunityAttachment)
            .filter(CommunityAttachment.post_id.in_(post_ids))
            .order_by(CommunityAttachment.position)
            .all()
        ):
            attachments.setdefault(row.post_id, []).append(row)

        options: dict[str, list[CommunityPollOption]] = {}
        for row in (
            db.query(CommunityPollOption)
            .filter(CommunityPollOption.post_id.in_(post_ids))
            .order_by(CommunityPollOption.position)
            .all()
        ):
            options.setdefault(row.post_id, []).append(row)

        votes: dict[str, int] = {}
        my_vote: dict[str, str] = {}
        for row in (
            db.query(CommunityPollVote)
            .filter(CommunityPollVote.post_id.in_(post_ids))
            .all()
        ):
            votes[row.option_id] = votes.get(row.option_id, 0) + 1
            if row.user_id == reader_id:
                my_vote[row.post_id] = row.option_id

        reported = {
            row.post_id
            for row in db.query(CommunityReport)
            .filter(
                CommunityReport.post_id.in_(post_ids),
                CommunityReport.user_id == reader_id,
            )
            .all()
        }

        return {
            "attachments": attachments,
            "options": options,
            "votes": votes,
            "my_vote": my_vote,
            "reported": reported,
        }

    def _warnings_for(self, db, user_id: str) -> list[CommunityWarningDto]:
        """Messages from moderation this student has not read yet."""
        rows = (
            db.query(CommunityPost)
            .filter(
                CommunityPost.user_id == user_id,
                CommunityPost.warned_at.isnot(None),
                CommunityPost.warning_seen_at.is_(None),
            )
            .order_by(CommunityPost.warned_at.desc())
            .limit(5)
            .all()
        )
        return [
            CommunityWarningDto(
                post_id=post.id,
                message=post.warning_text or "",
                created_at=post.warned_at,
                is_support=post.review_finding == SELF_HARM,
            )
            for post in rows
            if post.warning_text
        ]

    def mark_warnings_seen(self, user_id: str) -> None:
        """The student has read them, so stop showing them."""
        now = datetime.now(timezone.utc)
        with self._session() as db:
            (
                db.query(CommunityPost)
                .filter(
                    CommunityPost.user_id == user_id,
                    CommunityPost.warned_at.isnot(None),
                    CommunityPost.warning_seen_at.is_(None),
                )
                .update({"warning_seen_at": now}, synchronize_session=False)
            )
            db.commit()

    # ---- writing --------------------------------------------------------

    def add_post(
        self,
        user_id: str,
        body: str,
        parent_id: str | None = None,
        uploads: list[tuple[str, str, bytes, int | None]] | None = None,
        poll_question: str | None = None,
        poll_options: list[str] | None = None,
    ) -> CommunityPostDto:
        """Write in the student's own room, or reply to something in it.

        uploads are (filename, content_type, data, duration_seconds).

        The order matters. Contact details are refused before anything is
        stored, because a post that is going to be rejected should not leave
        files in the bucket. Attachments are checked next, before the post
        row exists, for the same reason.
        """
        has_poll = bool((poll_question or "").strip())
        uploads = uploads or []

        # A post has to be something. Text, a file, or a poll - but a reply
        # that is only a photo is fine, and so is a poll with no preamble.
        said = (body or "").strip()
        if not said and not uploads and not has_poll:
            raise ValueError("A post cannot be empty")
        if said:
            said = check_body(said)

        found = find_personal_details(said)
        if has_poll:
            found = found or find_personal_details(poll_question or "")
            for option in poll_options or []:
                found = found or find_personal_details(option)
        if found:
            raise ValueError(refusal_message(found))

        check_attachment_count(len(uploads))
        checked = []
        for filename, content_type, data, duration in uploads:
            kind, name = check_upload(
                filename, content_type, len(data), data[:16]
            )
            checked.append((kind, name, content_type, data, duration))

        question = check_question(poll_question) if has_poll else None
        options = check_options(poll_options) if has_poll else []

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
                poll_question=question,
            )
            db.add(post)
            db.flush()

            for index, option in enumerate(options):
                db.add(
                    CommunityPollOption(
                        id=str(uuid4()),
                        post_id=post.id,
                        text=option,
                        position=index,
                    )
                )

            for index, (kind, name, content_type, data, duration) in enumerate(checked):
                extension = "." + name.rsplit(".", 1)[1] if "." in name else ""
                path = stored_path(grade, group_code, post.id, index, extension)
                self._store(path, data, content_type)
                db.add(
                    CommunityAttachment(
                        id=str(uuid4()),
                        post_id=post.id,
                        kind=kind,
                        filename=name,
                        content_type=content_type,
                        size_bytes=len(data),
                        storage_path=path,
                        duration_seconds=duration,
                        position=index,
                    )
                )

            # The model reads it before the student sees it appear, which is
            # the only moment the text is guaranteed to be in hand. It never
            # stops the post: a failure here leaves review_finding null, and
            # null means "nobody has looked", which the admin queue shows.
            review = self._review(said or question or "", grade, group_code)
            if review is not None:
                post.review_finding = review.finding
                post.review_confidence = review.confidence
                post.review_why = review.why
                post.review_severity = review.severity
                warning = message_for(review)
                if warning:
                    post.warned_at = datetime.now(timezone.utc)
                    post.warning_text = warning

            db.commit()
            db.refresh(post)
            user = db.query(User).filter(User.id == user_id).first()
            extras = self._extras_for(db, [post.id], user_id)
            return self._as_dto(post, user, user_id, extras)

    def _store(self, path: str, data: bytes, content_type: str) -> None:
        if self.storage is None:
            raise ValueError(
                "Sharing files is not available on this setup."
            )
        self.storage.upload(path, data, content_type=content_type)

    def _review(self, body: str, grade: int, group_code: str) -> Review | None:
        """What the model makes of a post, or None if it could not say.

        Every failure is None rather than an exception. The student is
        waiting, the post is already written, and refusing to store it
        because a model timed out would be a worse room than an unreviewed
        post in it.
        """
        if self.reviewer is None or not body.strip():
            return None
        try:
            reply = self.reviewer(review_prompt(body, room_name(grade, group_code)))
            return read_review(reply)
        except Exception as error:  # noqa: BLE001 - never lose a post to the reviewer
            logger.warning("Community review failed, post left unreviewed: %s", error)
            return None

    # ---- deleting -------------------------------------------------------

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
            self._drop_files(db, post_id)
            db.delete(post)
            db.commit()

    def _drop_files(self, db, post_id: str) -> None:
        """Take a post's attachments out of the bucket.

        The database rows go by cascade. The bytes do not, and a bucket full
        of files belonging to posts nobody can see is both a cost and a
        quiet way to keep something that was deleted for a reason.
        """
        paths = [
            row.storage_path
            for row in db.query(CommunityAttachment)
            .filter(CommunityAttachment.post_id == post_id)
            .all()
        ]
        if paths and self.storage is not None:
            try:
                self.storage.delete(paths)
            except Exception as error:  # noqa: BLE001
                # The post still goes. An orphaned file is a tidying problem;
                # a post that cannot be removed is a moderation one.
                logger.warning("Could not delete attachments for %s: %s", post_id, error)

    # ---- reporting ------------------------------------------------------

    def report_post(
        self, user_id: str, post_id: str, reason: str | None = None, note: str | None = None
    ) -> None:
        """A student says this needs looking at.

        Reporting twice is not an error. The student pressed the button and
        the post is reported; telling them off for a double tap teaches them
        not to use it.
        """
        with self._session() as db:
            grade, group_code = self._room_of(db, user_id)
            post = (
                db.query(CommunityPost)
                .filter(
                    CommunityPost.id == post_id,
                    CommunityPost.grade == grade,
                    CommunityPost.group_code == group_code,
                )
                .first()
            )
            if post is None:
                raise NotFoundError("That post is not in your room")

            already = (
                db.query(CommunityReport)
                .filter(
                    CommunityReport.post_id == post_id,
                    CommunityReport.user_id == user_id,
                )
                .first()
            )
            if already is not None:
                return

            db.add(
                CommunityReport(
                    id=str(uuid4()),
                    post_id=post_id,
                    user_id=user_id,
                    reason=(reason or "").strip()[:60] or None,
                    note=(note or "").strip()[:500] or None,
                )
            )
            # A reported post goes back into the queue even if an
            # administrator has already cleared it. Students see things a
            # model does not, and "we looked once" is not a reason to stop
            # looking when somebody asks.
            post.reviewed_at = None
            db.commit()

    # ---- polls ----------------------------------------------------------

    def vote(self, user_id: str, post_id: str, option_id: str) -> CommunityPostDto:
        """Pick an option, or change an earlier pick.

        Changing a vote is allowed. A poll about which chapter is hardest is
        not an election, and a student who misreads an option should not be
        stuck with it.
        """
        with self._session() as db:
            grade, group_code = self._room_of(db, user_id)
            post = (
                db.query(CommunityPost)
                .filter(
                    CommunityPost.id == post_id,
                    CommunityPost.grade == grade,
                    CommunityPost.group_code == group_code,
                )
                .first()
            )
            if post is None or not post.poll_question:
                raise NotFoundError("That poll is not in your room")

            option = (
                db.query(CommunityPollOption)
                .filter(
                    CommunityPollOption.id == option_id,
                    CommunityPollOption.post_id == post_id,
                )
                .first()
            )
            if option is None:
                raise NotFoundError("That option is not on this poll")

            existing = (
                db.query(CommunityPollVote)
                .filter(
                    CommunityPollVote.post_id == post_id,
                    CommunityPollVote.user_id == user_id,
                )
                .first()
            )
            if existing is not None:
                existing.option_id = option_id
            else:
                db.add(
                    CommunityPollVote(
                        id=str(uuid4()),
                        post_id=post_id,
                        option_id=option_id,
                        user_id=user_id,
                    )
                )
            db.commit()

            db.refresh(post)
            user = db.query(User).filter(User.id == post.user_id).first()
            extras = self._extras_for(db, [post_id], user_id)
            return self._as_dto(post, user, user_id, extras)

    # ---- one attachment, on demand --------------------------------------

    def attachment_bytes(self, user_id: str, attachment_id: str) -> tuple[bytes, str, str]:
        """A file's bytes, name and type, for a student in the same room.

        Downloads go through here rather than straight to a signed URL so
        that the room is checked. A link that works for anyone holding it is
        fine for six hours inside a page; it is not a way to reach a file
        from another class.
        """
        with self._session() as db:
            grade, group_code = self._room_of(db, user_id)
            row = (
                db.query(CommunityAttachment)
                .join(CommunityPost, CommunityAttachment.post_id == CommunityPost.id)
                .filter(
                    CommunityAttachment.id == attachment_id,
                    CommunityPost.grade == grade,
                    CommunityPost.group_code == group_code,
                )
                .first()
            )
            if row is None:
                raise NotFoundError("That file is not in your room")
            if self.storage is None:
                raise NotFoundError("That file is not available")
            return (
                self.storage.download(row.storage_path),
                row.filename,
                row.content_type,
            )

    # ---- turning rows into what the page needs --------------------------

    def _attachment_dto(self, row: CommunityAttachment) -> CommunityAttachmentDto:
        url = download = ""
        if self.storage is not None:
            try:
                url = self.storage.signed_url(row.storage_path, expires_in=LINK_SECONDS)
                download = self.storage.signed_url(
                    row.storage_path, expires_in=LINK_SECONDS, download=True
                )
            except Exception as error:  # noqa: BLE001
                # A link that cannot be signed leaves the attachment listed
                # with no URL, which the page shows as unavailable. Better
                # than failing the whole room over one file.
                logger.warning("Could not sign %s: %s", row.storage_path, error)
        return CommunityAttachmentDto(
            id=row.id,
            kind=row.kind,
            filename=row.filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            duration_seconds=row.duration_seconds,
            url=url,
            download_url=download,
        )

    def _poll_dto(self, post: CommunityPost, extras: dict, reader_id: str) -> CommunityPollDto | None:
        if not post.poll_question:
            return None
        options = extras["options"].get(post.id, [])
        counts = [extras["votes"].get(o.id, 0) for o in options]
        shares = tally(counts)
        leaders = winning(counts)
        mine = extras["my_vote"].get(post.id)
        return CommunityPollDto(
            question=post.poll_question,
            options=[
                CommunityPollOptionDto(
                    id=option.id,
                    text=option.text,
                    votes=counts[i],
                    percent=shares[i],
                    is_mine=option.id == mine,
                    is_winning=i in leaders,
                )
                for i, option in enumerate(options)
            ],
            total_votes=sum(counts),
            has_voted=mine is not None,
        )

    def _as_dto(
        self,
        post: CommunityPost,
        user: User | None,
        reader_id: str,
        extras: dict | None = None,
    ) -> CommunityPostDto:
        extras = extras or {
            "attachments": {}, "options": {}, "votes": {}, "my_vote": {}, "reported": set()
        }
        return CommunityPostDto(
            id=post.id,
            body=post.body,
            author_name=display_name(
                getattr(user, "name", None), getattr(user, "email", None)
            ),
            is_mine=post.user_id == reader_id,
            created_at=post.created_at,
            attachments=[
                self._attachment_dto(row)
                for row in extras["attachments"].get(post.id, [])
            ],
            poll=self._poll_dto(post, extras, reader_id),
            reported_by_me=post.id in extras["reported"],
            replies=[],
        )


# Re-exported so a router can say how many files are allowed without
# reaching past the service into the rules module.
__all__ = ["CommunityService", "MAX_ATTACHMENTS", "DEFAULT_DAILY_POSTS"]
