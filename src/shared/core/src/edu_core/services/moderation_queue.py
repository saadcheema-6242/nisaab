"""What an administrator looks at, and what they can do about it.

The room could not be moderated at all before this. A student could delete
their own post and nobody else could delete anything, including the person
running the service. Combined with no rate limit, one person could fill a
room with things that could not be taken down.

The queue is ordered by how soon an adult is needed rather than by time. A
student who sounds like they are in distress comes before a threat, a threat
before spam, and a post five students have reported comes before one the
model merely wondered about. Sorting by newest would mean the worst thing in
the room sinks as the room gets busy, which is exactly backwards.

Three states are kept apart on purpose:

- flagged by the model
- reported by students
- never reviewed

The third is not the same as clean. A post written while Vertex was
unreachable has no verdict, and showing it as fine would be a quiet way for
something to sit unnoticed. It is counted separately and shown as what it
is.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import (
    CommunityAttachment,
    CommunityPost,
    CommunityReport,
    User,
)
from edu_db.session import get_session_factory
from sqlalchemy import func, or_

from edu_core.community_review import LABELS, URGENT
from edu_core.community_rules import display_name, room_name
from edu_core.exceptions import NotFoundError
from edu_core.schemas.community import (
    ModerationItemDto,
    ModerationQueueDto,
    ModerationReportDto,
)

logger = logging.getLogger(__name__)

# How many posts the queue shows at once. An administrator working through a
# backlog wants a page, not everything ever written.
QUEUE_SIZE = 100


class ModerationQueueService:
    """The administrator's view of the class rooms."""

    def __init__(self, storage=None):
        self.storage = storage

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

    def queue(self, include_cleared: bool = False) -> ModerationQueueDto:
        """Everything worth an administrator's attention, worst first."""
        with self._session() as db:
            # Report counts for every post that has one, in a single
            # grouped query rather than a count per row.
            counts = dict(
                db.query(CommunityReport.post_id, func.count(CommunityReport.id))
                .group_by(CommunityReport.post_id)
                .all()
            )

            query = db.query(CommunityPost, User).outerjoin(
                User, CommunityPost.user_id == User.id
            )
            # A post is interesting if the model flagged it, a student
            # reported it, or nobody has ever looked at it.
            reported_ids = list(counts)
            interesting = or_(
                CommunityPost.review_severity > 0,
                CommunityPost.review_finding.is_(None),
                CommunityPost.id.in_(reported_ids) if reported_ids else False,
            )
            query = query.filter(interesting)
            if not include_cleared:
                query = query.filter(CommunityPost.reviewed_at.is_(None))

            rows = query.order_by(
                CommunityPost.review_severity.desc(),
                CommunityPost.created_at.desc(),
            ).limit(QUEUE_SIZE).all()

            post_ids = [post.id for post, _ in rows]
            details = self._reports_for(db, post_ids)
            files = self._attachment_counts(db, post_ids)

            items = [
                self._item(post, user, counts.get(post.id, 0), details.get(post.id, []), files.get(post.id, 0))
                for post, user in rows
            ]

            # A post reported by students outranks one the model merely
            # wondered about, whatever the model said. Students see things a
            # model does not, and several of them agreeing is the strongest
            # signal available.
            items.sort(key=lambda i: (i.severity, i.report_count * 25, i.created_at.timestamp()), reverse=True)

            return ModerationQueueDto(
                items=items,
                urgent_count=sum(1 for i in items if i.is_urgent),
                flagged_count=sum(1 for i in items if i.severity > 0),
                reported_count=sum(1 for i in items if i.report_count > 0),
                unreviewed_count=sum(1 for i in items if i.finding is None),
            )

    def _reports_for(self, db, post_ids: list[str]) -> dict[str, list[ModerationReportDto]]:
        if not post_ids:
            return {}
        out: dict[str, list[ModerationReportDto]] = {}
        for report, user in (
            db.query(CommunityReport, User)
            .outerjoin(User, CommunityReport.user_id == User.id)
            .filter(CommunityReport.post_id.in_(post_ids))
            .order_by(CommunityReport.created_at.desc())
            .all()
        ):
            out.setdefault(report.post_id, []).append(
                ModerationReportDto(
                    reporter_name=display_name(
                        getattr(user, "name", None), getattr(user, "email", None)
                    ),
                    reason=report.reason,
                    note=report.note,
                    created_at=report.created_at,
                )
            )
        return out

    def _attachment_counts(self, db, post_ids: list[str]) -> dict[str, int]:
        if not post_ids:
            return {}
        return dict(
            db.query(CommunityAttachment.post_id, func.count(CommunityAttachment.id))
            .filter(CommunityAttachment.post_id.in_(post_ids))
            .group_by(CommunityAttachment.post_id)
            .all()
        )

    @staticmethod
    def _item(
        post: CommunityPost,
        user: User | None,
        report_count: int,
        reports: list[ModerationReportDto],
        attachment_count: int,
    ) -> ModerationItemDto:
        finding = post.review_finding
        return ModerationItemDto(
            post_id=post.id,
            body=post.body or "",
            room_name=room_name(post.grade, post.group_code),
            grade=post.grade,
            group_code=post.group_code,
            author_id=post.user_id,
            author_name=display_name(
                getattr(user, "name", None), getattr(user, "email", None)
            ),
            # The one place an email is shown. An administrator deciding
            # whether to suspend somebody needs to know who they are; the
            # room never does.
            author_email=getattr(user, "email", None),
            created_at=post.created_at,
            finding=finding,
            finding_label=LABELS.get(finding, "not reviewed") if finding else "not reviewed",
            confidence=post.review_confidence,
            why=post.review_why,
            severity=post.review_severity or 0,
            is_urgent=finding in URGENT if finding else False,
            report_count=report_count,
            reports=reports,
            warned_at=post.warned_at,
            reviewed_at=post.reviewed_at,
            attachment_count=attachment_count,
        )

    # ---- acting ---------------------------------------------------------

    def delete_post(self, admin_id: str, post_id: str) -> None:
        """Remove any post, whoever wrote it.

        Replies go with it, by cascade, which is what an administrator
        removing an abusive thread expects: leaving the answers to a deleted
        post is leaving half the conversation.
        """
        with self._session() as db:
            post = (
                db.query(CommunityPost)
                .filter(CommunityPost.id == post_id)
                .first()
            )
            if post is None:
                raise NotFoundError("That post no longer exists")

            # Files for the post and everything under it.
            ids = [post_id] + [
                row.id
                for row in db.query(CommunityPost)
                .filter(CommunityPost.parent_id == post_id)
                .all()
            ]
            paths = [
                row.storage_path
                for row in db.query(CommunityAttachment)
                .filter(CommunityAttachment.post_id.in_(ids))
                .all()
            ]
            db.delete(post)
            db.commit()

        if paths and self.storage is not None:
            try:
                self.storage.delete(paths)
            except Exception as error:  # noqa: BLE001
                logger.warning("Removed post %s but not its files: %s", post_id, error)

    def clear_post(self, admin_id: str, post_id: str) -> None:
        """Looked at it, it is fine, take it out of the queue.

        The finding is kept. An administrator disagreeing with the model is
        worth knowing about later, and deleting the verdict would hide that
        the model was wrong.
        """
        with self._session() as db:
            post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
            if post is None:
                raise NotFoundError("That post no longer exists")
            post.reviewed_at = datetime.now(timezone.utc)
            post.reviewed_by = admin_id
            db.commit()
