"""Shared SLO content bank: serve reviewed items to students, and the teacher review queue.

Items are generated ahead of time as drafts (scripts/content/generate_bank.py).
Students get approved items first, then drafts; rejected items are never served.
"""

import random
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import ContentItem, CurriculumDomain, Slo
from edu_db.session import get_session_factory
from sqlalchemy import case, func

from edu_core.exceptions import NotFoundError
from edu_core.schemas.content import (
    ContentItemDto,
    ContentSummaryDto,
    SloExplainerDto,
)

REVIEW_STATUSES = ("draft", "approved", "rejected")


def usable_items(db, grade_subject_id: str, slo_code: str, kind: str) -> list[ContentItem]:
    """Non-rejected bank items for an SLO, approved ones first, otherwise shuffled."""
    items = (
        db.query(ContentItem)
        .filter(
            ContentItem.grade_subject_id == grade_subject_id,
            ContentItem.slo_code == slo_code,
            ContentItem.kind == kind,
            ContentItem.review_status != "rejected",
        )
        .all()
    )
    random.shuffle(items)
    return sorted(items, key=lambda item: item.review_status != "approved")


class ContentService:
    """Service for the shared SLO content bank."""

    def get_explainer(self, grade_subject_id: str, slo_code: str) -> SloExplainerDto | None:
        """The explainer for an SLO, or None if none has been written yet."""
        with self._get_db_session() as db:
            items = usable_items(db, grade_subject_id, slo_code, "explainer")
            if not items:
                return None
            item = items[0]
            return SloExplainerDto(
                slo_code=slo_code,
                title=item.payload.get("title", f"SLO {slo_code}"),
                content=item.payload.get("content", ""),
                reviewed=item.review_status == "approved",
            )

    def list_items(
        self,
        grade_subject_id: str,
        domain_code: str | None = None,
        kind: str | None = None,
        review_status: str | None = None,
        slo_code: str | None = None,
    ) -> list[ContentItemDto]:
        """Items for the review queue, in syllabus order."""
        with self._get_db_session() as db:
            query = (
                db.query(ContentItem, Slo, CurriculumDomain)
                .join(
                    Slo,
                    (Slo.grade_subject_id == ContentItem.grade_subject_id)
                    & (Slo.code == ContentItem.slo_code),
                )
                .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
                .filter(ContentItem.grade_subject_id == grade_subject_id)
            )
            if domain_code:
                query = query.filter(CurriculumDomain.code == domain_code)
            if kind:
                query = query.filter(ContentItem.kind == kind)
            if review_status:
                query = query.filter(ContentItem.review_status == review_status)
            if slo_code:
                query = query.filter(ContentItem.slo_code == slo_code)
            kind_order = case(
                (ContentItem.kind == "explainer", 0), (ContentItem.kind == "mcq", 1), else_=2
            )
            rows = query.order_by(
                CurriculumDomain.sort_order, Slo.sort_order, kind_order, ContentItem.created_at
            ).all()
            return [self._to_dto(item, slo) for item, slo, _ in rows]

    def summary(self, grade_subject_id: str) -> list[ContentSummaryDto]:
        """Counts per kind and review status."""
        with self._get_db_session() as db:
            rows = (
                db.query(ContentItem.kind, ContentItem.review_status, func.count(ContentItem.id))
                .filter(ContentItem.grade_subject_id == grade_subject_id)
                .group_by(ContentItem.kind, ContentItem.review_status)
                .all()
            )
            return [
                ContentSummaryDto(kind=kind, review_status=status, count=count)
                for kind, status, count in rows
            ]

    def review(
        self,
        item_id: str,
        reviewer: str,
        review_status: str,
        review_note: str | None = None,
    ) -> ContentItemDto:
        """Approve or reject an item (a note explains what to fix).

        Raises:
            NotFoundError: If the item does not exist
        """
        if review_status not in REVIEW_STATUSES:
            raise ValueError(f"Unknown review status {review_status}")
        with self._get_db_session() as db:
            item = db.get(ContentItem, item_id)
            if item is None:
                raise NotFoundError(f"Content item {item_id} not found")
            item.review_status = review_status
            item.review_note = review_note
            item.reviewed_by = reviewer
            item.reviewed_at = datetime.now(timezone.utc)
            db.commit()
            slo = (
                db.query(Slo)
                .filter(Slo.grade_subject_id == item.grade_subject_id, Slo.code == item.slo_code)
                .first()
            )
            return self._to_dto(item, slo)

    @staticmethod
    def _to_dto(item: ContentItem, slo: Slo | None) -> ContentItemDto:
        return ContentItemDto(
            id=item.id,
            grade_subject_id=item.grade_subject_id,
            slo_code=item.slo_code,
            slo_description=slo.description if slo else "",
            kind=item.kind,
            payload=item.payload,
            review_status=item.review_status,
            review_note=item.review_note,
            reviewed_by=item.reviewed_by,
            created_at=item.created_at,
        )

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
