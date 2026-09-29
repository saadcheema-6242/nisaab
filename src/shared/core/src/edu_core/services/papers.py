"""FBISE-style practice papers: assembled from the SLO bank, answered by typing, marked.

A paper has Section A (MCQs, marked instantly), Section B (short questions, SRQ) and,
for the standard length, Section C (one long question, ERQ). Written answers are
marked point by point like any SRQ, all at the same time, and everything counts
towards SLO mastery.
"""

import asyncio
import random
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from edu_db.models import (
    CurriculumDomain,
    GradeSubject,
    PracticeAttempt,
    PracticePaper,
    PracticeRecord,
    Project,
    Slo,
    SrqQuestion,
)
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.grading import grade_for
from edu_core.schemas.papers import (
    PaperDto,
    PaperItemDto,
    PaperItemResultDto,
    PaperResultDto,
    PaperSectionDto,
    PaperSectionResultDto,
    PaperSummaryDto,
)
from edu_core.services.content import usable_items
from edu_core.services.srq import SrqService

LENGTHS = {
    "mini": {"mcq": 8, "srq": 2, "erq": 0, "minutes": 20},
    "standard": {"mcq": 12, "srq": 4, "erq": 1, "minutes": 45},
}
GRADE_NAMES = {11: "XI", 12: "XII"}


class PaperService:
    """Service for practice papers."""

    async def create(
        self,
        project_id: str,
        user_id: str,
        length: str = "mini",
        topic: str | None = None,
    ) -> PaperDto:
        """Assemble a paper from the examined SLOs of the workspace's subject.

        topic may be a domain name (e.g. "Mechanics") or any topic; without it the
        whole syllabus is used.

        Raises:
            NotFoundError: If the project is not an FBISE subject workspace with SLOs
        """
        from edu_ai.agents.bank_agent import generate_mcqs
        from edu_ai.agents.slo_context import load_slo
        from edu_ai.llm import GENERATION, create_chat_model
        from edu_ai.tools.syllabus import search_slos

        plan = LENGTHS.get(length, LENGTHS["mini"])
        with self._get_db_session() as db:
            project = self._get_project(db, project_id, user_id)
            grade_subject = (
                db.get(GradeSubject, project.grade_subject_id) if project.grade_subject_id else None
            )
            if grade_subject is None:
                raise NotFoundError("Practice papers are available in FBISE subject workspaces")
            rows = (
                db.query(Slo, CurriculumDomain)
                .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
                .filter(Slo.grade_subject_id == grade_subject.id, Slo.assessment_form == "summative")
                .order_by(CurriculumDomain.sort_order, Slo.sort_order)
                .all()
            )
            if not rows:
                raise NotFoundError("This subject's syllabus map is not available yet")
            subject_title = f"{grade_subject.subject.name} {GRADE_NAMES.get(grade_subject.grade, grade_subject.grade)}"
            grade_subject_id = grade_subject.id

            # Scope: a domain, a topic, or the whole syllabus
            scope = "whole syllabus"
            wanted = (topic or "").strip().lower()
            candidates = [slo for slo, _ in rows]
            if wanted:
                domain = next(
                    (d for _, d in rows if d.name.lower() in wanted or wanted in d.name.lower()), None
                )
                if domain is not None:
                    candidates = [slo for slo, d in rows if d.id == domain.id]
                    scope = domain.name
                else:
                    codes = {m["code"] for m in search_slos(grade_subject_id, topic, limit=10)}
                    matched = [slo for slo in candidates if slo.code in codes]
                    if matched:
                        candidates = matched
                        scope = topic.strip()
            slo_info = {
                slo.code: {"code": slo.code, "levels": list(slo.cognitive_levels or [])}
                for slo in candidates
            }
            order = list(slo_info)
            random.shuffle(order)

            # Section A: one bank MCQ per SLO (teacher-approved first), spread over the SLOs
            mcqs = []
            for code in order * 2:  # a second pass takes a second question per SLO if needed
                if len(mcqs) >= plan["mcq"]:
                    break
                used = {m["bank_id"] for m in mcqs}
                item = next(
                    (i for i in usable_items(db, grade_subject_id, code, "mcq") if i.id not in used),
                    None,
                )
                if item is not None:
                    mcqs.append({"bank_id": item.id, "slo_code": code, **item.payload})
            fill_codes = order[:2]
            slo_contexts = {
                code: load_slo(db, code, grade_subject_id=grade_subject_id) for code in fill_codes
            }

        # Top up with new MCQs when the bank is short (e.g. before content generation)
        missing = plan["mcq"] - len(mcqs)
        if missing > 0:
            llm = create_chat_model(task=GENERATION, temperature=0.5)
            for index, code in enumerate(fill_codes):
                share = missing // len(fill_codes) + (1 if index < missing % len(fill_codes) else 0)
                if share and slo_contexts.get(code):
                    for payload in (await generate_mcqs(llm, slo_contexts[code], share))[:share]:
                        mcqs.append({"bank_id": None, "slo_code": code, **payload})

        # Sections B and C: written questions on SLOs that ask for understanding or application
        written_pool = [c for c in order if {"U", "A"} & set(slo_info[c]["levels"])] or order
        srq_codes = written_pool[: plan["srq"]]
        erq_codes = [c for c in written_pool if c not in srq_codes][: plan["erq"]] or written_pool[: plan["erq"]]
        srq_service = SrqService()
        written = await asyncio.gather(
            *(srq_service.generate(project_id, user_id, code) for code in srq_codes),
            *(srq_service.generate(project_id, user_id, code, long=True) for code in erq_codes),
        )
        srqs, erqs = written[: len(srq_codes)], written[len(srq_codes) :]

        sections = [
            {
                "id": "A",
                "title": "Section A: Multiple choice questions",
                "items": [
                    {
                        "id": f"m{index + 1}",
                        "type": "mcq",
                        "marks": 1,
                        "slo_code": m["slo_code"],
                        "cognitive_level": m.get("cognitive_level"),
                        "question": m.get("question_text", ""),
                        "options": {k: m.get(f"option_{k}", "") for k in ("a", "b", "c", "d")},
                        "correct_option": (m.get("correct_option") or "").lower()[:1],
                        "explanation": m.get("explanation"),
                    }
                    for index, m in enumerate(mcqs)
                ],
            },
            {
                "id": "B",
                "title": "Section B: Short questions",
                "items": [
                    {"id": q.id, "type": "srq", "marks": q.marks, "slo_code": q.slo_code,
                     "cognitive_level": q.cognitive_level}
                    for q in srqs
                ],
            },
        ]
        if erqs:
            sections.append(
                {
                    "id": "C",
                    "title": "Section C: Long question",
                    "items": [
                        {"id": q.id, "type": "erq", "marks": q.marks, "slo_code": q.slo_code,
                         "cognitive_level": q.cognitive_level}
                        for q in erqs
                    ],
                }
            )
        total = sum(item["marks"] for section in sections for item in section["items"])

        with self._get_db_session() as db:
            paper = PracticePaper(
                id=str(uuid4()),
                project_id=project_id,
                user_id=user_id,
                title=f"{subject_title} practice paper: {scope}",
                length=length if length in LENGTHS else "mini",
                time_limit_minutes=plan["minutes"],
                sections=sections,
                total_marks=float(total),
                answers={},
                status="ready",
            )
            db.add(paper)
            db.commit()
            db.refresh(paper)
            return self._to_dto(db, paper)

    def get(self, paper_id: str, user_id: str) -> PaperDto:
        """Raises NotFoundError if the paper does not exist."""
        with self._get_db_session() as db:
            return self._to_dto(db, self._get_paper(db, paper_id, user_id))

    def list_papers(self, project_id: str, user_id: str) -> list[PaperSummaryDto]:
        with self._get_db_session() as db:
            self._get_project(db, project_id, user_id)
            papers = (
                db.query(PracticePaper)
                .filter(PracticePaper.project_id == project_id, PracticePaper.user_id == user_id)
                .order_by(PracticePaper.created_at.desc())
                .all()
            )
            return [
                PaperSummaryDto(
                    id=p.id,
                    title=p.title,
                    length=p.length,
                    status=p.status,
                    total_marks=p.total_marks,
                    score=(p.result or {}).get("score"),
                    created_at=p.created_at,
                )
                for p in papers
            ]

    def save_answers(self, paper_id: str, user_id: str, answers: dict[str, str]) -> None:
        """Save answers while the student works, so nothing is lost on a refresh."""
        with self._get_db_session() as db:
            paper = self._get_paper(db, paper_id, user_id)
            if paper.status == "ready":
                paper.answers = {k: v[:6000] for k, v in answers.items() if isinstance(v, str)}
                db.commit()

    async def submit(self, paper_id: str, user_id: str, answers: dict[str, str]) -> PaperDto:
        """Mark the paper: MCQs instantly, written answers all at once."""
        with self._get_db_session() as db:
            paper = self._get_paper(db, paper_id, user_id)
            if paper.status == "submitted":
                return self._to_dto(db, paper)
            project_id = paper.project_id
            sections = paper.sections
            written_ids = [
                item["id"] for s in sections for item in s["items"] if item["type"] != "mcq"
            ]
            written = {
                q.id: q for q in db.query(SrqQuestion).filter(SrqQuestion.id.in_(written_ids))
            }
            model_answers = {qid: q.model_answer for qid, q in written.items()}

        srq_service = SrqService()
        to_mark = [
            item
            for s in sections
            for item in s["items"]
            if item["type"] != "mcq" and (answers.get(item["id"]) or "").strip()
        ]
        markings = await asyncio.gather(
            *(
                srq_service.mark(project_id, item["id"], user_id, answers[item["id"]].strip())
                for item in to_mark
            )
        )
        marking_by_id = {item["id"]: m for item, m in zip(to_mark, markings)}

        item_results = []
        section_results = []
        with self._get_db_session() as db:
            for section in sections:
                score = 0.0
                for item in section["items"]:
                    chosen = (answers.get(item["id"]) or "").strip()
                    if item["type"] == "mcq":
                        chosen_option = chosen.lower()[:1] or None
                        correct = item.get("correct_option")
                        awarded = float(item["marks"]) if chosen_option == correct else 0.0
                        item_results.append(
                            PaperItemResultDto(
                                id=item["id"], type="mcq", marks=item["marks"], awarded=awarded,
                                chosen=chosen_option, correct_option=correct,
                                explanation=item.get("explanation"),
                            )
                        )
                        if chosen_option:
                            db.add(
                                PracticeRecord(
                                    id=str(uuid4()), user_id=user_id, project_id=project_id,
                                    item_type="paper_mcq", item_id=f"{paper_id}:{item['id']}",
                                    topic=item["question"][:100], user_answer=chosen_option,
                                    correct_answer=correct or "", was_correct=awarded > 0,
                                    slo_code=item.get("slo_code"),
                                )
                            )
                    else:
                        marking = marking_by_id.get(item["id"])
                        awarded = marking.awarded_marks if marking else 0.0
                        item_results.append(
                            PaperItemResultDto(
                                id=item["id"], type=item["type"], marks=item["marks"],
                                awarded=awarded, answer=chosen or None, marking=marking,
                                model_answer=model_answers.get(item["id"]),
                            )
                        )
                    score += awarded
                section_results.append(
                    PaperSectionResultDto(
                        id=section["id"], title=section["title"], score=score,
                        max_score=float(sum(i["marks"] for i in section["items"])),
                    )
                )

            paper = self._get_paper(db, paper_id, user_id)
            total = sum(s.score for s in section_results)
            percent = round(100 * total / paper.total_marks) if paper.total_marks else 0
            grade, descriptor = grade_for(percent)
            result = PaperResultDto(
                score=total, max_score=paper.total_marks, percent=percent, grade=grade,
                descriptor=descriptor, sections=section_results, items=item_results,
            )
            paper.answers = {k: v[:6000] for k, v in answers.items() if isinstance(v, str)}
            paper.result = result.model_dump(mode="json")
            paper.status = "submitted"
            paper.submitted_at = datetime.now(timezone.utc)
            db.add(
                PracticeAttempt(
                    id=str(uuid4()), user_id=user_id, project_id=project_id, kind="paper",
                    ref_id=paper_id, answers=[], score=total, max_score=paper.total_marks,
                )
            )
            db.commit()
            db.refresh(paper)
            return self._to_dto(db, paper)

    def _to_dto(self, db, paper: PracticePaper) -> PaperDto:
        submitted = paper.status == "submitted"
        written_ids = [
            item["id"] for s in paper.sections for item in s["items"] if item["type"] != "mcq"
        ]
        questions = {
            q.id: q.question
            for q in db.query(SrqQuestion).filter(SrqQuestion.id.in_(written_ids))
        }
        sections = [
            PaperSectionDto(
                id=s["id"],
                title=s["title"],
                items=[
                    PaperItemDto(
                        id=item["id"],
                        type=item["type"],
                        marks=item["marks"],
                        slo_code=item.get("slo_code"),
                        cognitive_level=item.get("cognitive_level"),
                        question=item["question"] if item["type"] == "mcq" else questions.get(item["id"], ""),
                        options=item.get("options"),
                    )
                    for item in s["items"]
                ],
            )
            for s in paper.sections
        ]
        return PaperDto(
            id=paper.id,
            project_id=paper.project_id,
            title=paper.title,
            length=paper.length,
            time_limit_minutes=paper.time_limit_minutes,
            total_marks=paper.total_marks,
            status=paper.status,
            sections=sections,
            answers=paper.answers or {},
            result=PaperResultDto(**paper.result) if submitted and paper.result else None,
            created_at=paper.created_at,
            submitted_at=paper.submitted_at,
        )

    @staticmethod
    def _get_project(db, project_id: str, user_id: str) -> Project:
        project = (
            db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
        )
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    @staticmethod
    def _get_paper(db, paper_id: str, user_id: str) -> PracticePaper:
        paper = (
            db.query(PracticePaper)
            .filter(PracticePaper.id == paper_id, PracticePaper.user_id == user_id)
            .first()
        )
        if paper is None:
            raise NotFoundError(f"Paper {paper_id} not found")
        return paper

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
