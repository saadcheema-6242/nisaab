"""Everything a student has made, and everything they have uploaded.

Both of these already existed, one project at a time. A student who
wanted to find the quiz they made last week had to remember which
subject it was under and open that workspace first, which is a question
about NISAAB's filing rather than about their work.

So: two cross-project reads, one for generated things and one for
uploads, each carrying the subject so a page can group by it.

Nothing here generates, writes or deletes. It is a different view over
rows the other services already own, which is why it is a read service
with no counterpart in edu_core's pure modules: there are no rules here,
only a query.
"""

import logging
from contextlib import contextmanager

from edu_db.models import (
    Document,
    Flashcard,
    FlashcardGroup,
    GradeSubject,
    MindMap,
    Note,
    PracticePaper,
    Project,
    Quiz,
    QuizQuestion,
    StudyPlan,
    Subject,
)
from edu_db.session import get_session_factory
from sqlalchemy import func

logger = logging.getLogger(__name__)

# One page of history. Generous, because a student in their second year
# may genuinely have made a few hundred things, and the page groups by
# subject rather than paginating.
LIMIT = 400


class LibraryService:
    @contextmanager
    def _session(self):
        factory = get_session_factory()
        db = factory()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _subject_of(db, user_id: str) -> dict[str, dict]:
        """Which subject each of this student's projects belongs to.

        Read once and used for every row rather than joined into each
        query: there are at most a dozen projects, and five separate
        joins to the same two tables is five times the work for the same
        answer.

        A project the student made themselves has no grade subject, so
        it has no subject code; the page shows those under "My projects".
        """
        rows = (
            db.query(Project, GradeSubject, Subject)
            .outerjoin(GradeSubject, Project.grade_subject_id == GradeSubject.id)
            .outerjoin(Subject, GradeSubject.subject_id == Subject.id)
            .filter(Project.owner_id == user_id, Project.archived_at.is_(None))
            .all()
        )
        return {
            project.id: {
                "project_id": project.id,
                "project_name": project.name,
                "subject_code": subject.code if subject else None,
                "subject_name": subject.name if subject else None,
                "grade": grade_subject.grade if grade_subject else None,
            }
            for project, grade_subject, subject in rows
        }

    # ---- what the student has made --------------------------------------

    def history(self, user_id: str) -> dict:
        """Everything generated, across every subject, newest first."""
        with self._session() as db:
            where = self._subject_of(db, user_id)
            if not where:
                return {"items": [], "subjects": []}
            ids = list(where.keys())
            items: list[dict] = []

            def add(kind, rows, name_of, when_of, extra=lambda r: {}):
                for r in rows:
                    items.append(
                        {
                            "id": r.id,
                            "kind": kind,
                            "name": name_of(r) or "Untitled",
                            "created_at": when_of(r),
                            **where.get(r.project_id, {}),
                            **extra(r),
                        }
                    )

            # Counts in one grouped query each, rather than one query per
            # row: a history page of three hundred items would otherwise
            # make three hundred round trips to say "12 questions".
            q_counts = dict(
                db.query(QuizQuestion.quiz_id, func.count(QuizQuestion.id))
                .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
                .filter(Quiz.project_id.in_(ids))
                .group_by(QuizQuestion.quiz_id)
                .all()
            )
            f_counts = dict(
                db.query(Flashcard.group_id, func.count(Flashcard.id))
                .join(FlashcardGroup, FlashcardGroup.id == Flashcard.group_id)
                .filter(FlashcardGroup.project_id.in_(ids))
                .group_by(Flashcard.group_id)
                .all()
            )

            add(
                "quiz",
                db.query(Quiz).filter(Quiz.project_id.in_(ids)).all(),
                lambda r: r.name,
                lambda r: r.created_at,
                lambda r: {"count": q_counts.get(r.id, 0), "slo_code": r.slo_code},
            )
            add(
                "flashcards",
                db.query(FlashcardGroup)
                .filter(FlashcardGroup.project_id.in_(ids))
                .all(),
                lambda r: r.name,
                lambda r: r.created_at,
                lambda r: {"count": f_counts.get(r.id, 0)},
            )
            add(
                "note",
                db.query(Note).filter(Note.project_id.in_(ids)).all(),
                lambda r: r.title,
                lambda r: r.created_at,
            )
            add(
                "mind_map",
                db.query(MindMap).filter(MindMap.project_id.in_(ids)).all(),
                lambda r: r.title,
                # A mind map records when it was generated, not created.
                lambda r: r.generated_at,
            )
            add(
                "study_plan",
                db.query(StudyPlan).filter(StudyPlan.project_id.in_(ids)).all(),
                # A plan has no title column; its name lives in the JSON
                # it was generated as, so fall back to something true
                # rather than inventing a column.
                lambda r: (r.content or {}).get("title")
                if isinstance(r.content, dict)
                else None,
                lambda r: r.created_at,
            )
            add(
                "paper",
                db.query(PracticePaper)
                .filter(PracticePaper.project_id.in_(ids))
                .all(),
                lambda r: r.title,
                lambda r: r.created_at,
                # Whether it was sat, so the page can say so. A paper a
                # student never opened is the thing they are looking for.
                lambda r: {
                    "status": r.status,
                    "total_marks": r.total_marks,
                },
            )

            items.sort(key=lambda i: i["created_at"] or 0, reverse=True)
            return {
                "items": items[:LIMIT],
                "subjects": self._subjects_in(where),
            }

    # ---- what the student has uploaded ----------------------------------

    def library(self, user_id: str) -> dict:
        """Every uploaded document, across every subject, newest first."""
        with self._session() as db:
            where = self._subject_of(db, user_id)
            rows = (
                db.query(Document)
                .filter(Document.owner_id == user_id)
                .order_by(Document.uploaded_at.desc())
                .limit(LIMIT)
                .all()
            )
            return {
                "items": [
                    {
                        "id": d.id,
                        "file_name": d.file_name,
                        "file_type": d.file_type,
                        "file_size": d.file_size,
                        "status": d.status,
                        "summary": d.summary,
                        "uploaded_at": d.uploaded_at,
                        **where.get(d.project_id, {"project_id": d.project_id}),
                    }
                    for d in rows
                ],
                "subjects": self._subjects_in(where),
            }

    @staticmethod
    def _subjects_in(where: dict) -> list[dict]:
        """The tabs the page should offer, in a stable order.

        Built from the student's own projects rather than from the list
        of FSc subjects, so an ICS student is never offered a Biology
        tab that could only ever be empty.
        """
        seen: dict[str, dict] = {}
        for meta in where.values():
            code = meta.get("subject_code")
            if code and code not in seen:
                seen[code] = {
                    "code": code,
                    "name": meta.get("subject_name") or code,
                }
        return sorted(seen.values(), key=lambda s: s["name"])
