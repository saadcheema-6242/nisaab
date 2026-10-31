"""FBISE-style practice papers: assembled from the SLO bank, answered by typing, marked.

Quick papers (mini, standard) have Section A (MCQs, marked instantly), Section B (short
questions, SRQ) and, for standard, Section C (one long question, ERQ); they are built
while the student waits.

Board papers follow FBISE's new pattern (50% MCQs and 50% descriptive, model papers of
August 2026), in full ("board", 3 hours) or half length ("half"): Section A has straight
MCQs plus stimulus sets (a scenario with four MCQs), Sections B and C have questions with
an internal choice (answer (a) OR (b)). They need about twenty AI-written items, so they
are built by the worker in the background while the paper shows "preparing".

Written answers are marked point by point like any SRQ, all at the same time, and
everything counts towards SLO mastery.
"""

import asyncio
import random
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from edu_db.models import (
    ContentItem,
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

from edu_core import paper_blueprint as blueprint
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

if TYPE_CHECKING:
    from edu_queue.service import QueueService

LENGTHS = {
    "mini": {"mcq": 8, "srq": 2, "erq": 0, "minutes": 20},
    "standard": {"mcq": 12, "srq": 4, "erq": 1, "minutes": 45},
}
# FBISE's new pattern (50% MCQs, 50% descriptive). Sciences and Computer Science:
# 56 MCQs + 6 stimulus sets of 4 at 0.5 marks, 7 SRQs x 4, 2 ERQs x 6 = 80 marks.
# Mathematics: 40 MCQs + 6 sets of 4 at 0.75 marks, 7 SRQs x 4, 3 ERQs x 8 = 100 marks
# (two ERQs without parts, one with parts). Section A takes 1 h 40 min, B and C 1 h 20 min.
# What one question is worth, per subject. A shorter paper asks FEWER questions;
# it never changes what a question is worth, so a student practising on a mini
# paper learns the same weights they will meet in the exam hall.
QUESTION_MARKS = {
    "default": {"mcq": 0.5, "srq": 4, "erq": 6},
    "MATH": {"mcq": 0.75, "srq": 4, "erq": 8},
}

# How many questions each paper length asks for. Marks come from QUESTION_MARKS.
BOARD = {
    "board": {
        "default": {"mcq": 56, "stimulus": 6, "srq": 7,
                    "erq": 2, "erq_parts": [True, True], "minutes": 180},
        "MATH": {"mcq": 40, "stimulus": 6, "srq": 7,
                 "erq": 3, "erq_parts": [False, False, True], "minutes": 180},
    },
    "half": {
        "default": {"mcq": 28, "stimulus": 3, "srq": 4,
                    "erq": 1, "erq_parts": [True], "minutes": 90},
        "MATH": {"mcq": 20, "stimulus": 3, "srq": 4,
                 "erq": 2, "erq_parts": [False, True], "minutes": 90},
    },
}


def question_marks(subject_code: str) -> dict:
    """What one MCQ, SRQ and ERQ is worth in this subject, at any paper length."""
    return QUESTION_MARKS.get(subject_code, QUESTION_MARKS["default"])
STIMULUS_SIZE = 4
# Eight at once was enough to rate-limit ourselves at Vertex, and every 429 is
# paid for twice: once in the backoff, once in the retry.
AI_CONCURRENCY = 5
# A board paper is the longest thing the worker builds. Past this it is stuck,
# not slow: fail it so the student is offered another go instead of a spinner
# that never ends.
BUILD_TIMEOUT_SECONDS = 9 * 60
GRADE_NAMES = {11: "XI", 12: "XII"}


def board_plan(length: str, subject_code: str) -> dict:
    plans = BOARD[length]
    plan = dict(plans.get(subject_code, plans["default"]))
    marks = question_marks(subject_code)
    plan["mcq_marks"], plan["srq_marks"], plan["erq_marks"] = (
        marks["mcq"],
        marks["srq"],
        marks["erq"],
    )
    return plan


def board_total(plan: dict) -> float:
    mcqs = plan["mcq"] + plan["stimulus"] * STIMULUS_SIZE
    return mcqs * plan["mcq_marks"] + plan["srq"] * plan["srq_marks"] + plan["erq"] * plan["erq_marks"]


class PaperService:
    """Service for practice papers."""

    def __init__(self, queue_service: "QueueService | None" = None):
        self.queue_service = queue_service

    async def create(
        self,
        project_id: str,
        user_id: str,
        length: str = "mini",
        topic: str | None = None,
    ) -> PaperDto:
        """Assemble a paper from the examined SLOs of the workspace's subject.

        topic may be a domain name (e.g. "Mechanics") or any topic; without it the
        whole syllabus is used. Board papers are queued and built in the background
        (or right away when there is no queue, e.g. in tests).

        Raises:
            NotFoundError: If the project is not an FBISE subject workspace with SLOs
        """
        if length in BOARD:
            return await self._create_board(project_id, user_id, length, topic)

        from edu_ai.agents.bank_agent import generate_mcqs
        from edu_ai.agents.slo_context import load_slo
        from edu_ai.llm import GENERATION, create_chat_model

        plan = LENGTHS.get(length, LENGTHS["mini"])
        with self._get_db_session() as db:
            scope_info = self._scope(db, project_id, user_id, topic)
            grade_subject_id = scope_info["grade_subject_id"]
            slo_info, order = scope_info["slo_info"], scope_info["order"]
            domain_of = scope_info["domain_of"]
            mcqs = self._bank_mcqs(db, grade_subject_id, order, plan["mcq"])
            # Which SLO to ask about and at which level, decided before anything
            # is written. A short paper asks fewer questions; it still spreads
            # them over the scope and still carries recall as well as application.
            levels_of = {code: slo_info[code]["levels"] for code in order}
            missing = plan["mcq"] - len(mcqs)
            mcq_orders = blueprint.group_by_slo(
                blueprint.assign_levels(
                    blueprint.mcq_pool(order, domain_of, missing),
                    levels_of, missing, domain_of,
                )
            )
            written_levels = blueprint.choice_pairs(
                order, levels_of, plan["srq"] + plan["erq"], domain_of
            )
            fill_codes = [code for code, _ in mcq_orders]
            slo_contexts = {
                code: load_slo(db, code, grade_subject_id=grade_subject_id)
                for code in {*fill_codes, *(c for pair in written_levels for c in pair[:2])}
            }

        # Top up with new MCQs when the bank is short (e.g. before content generation)
        if missing > 0:
            llm = create_chat_model(task=GENERATION, temperature=0.5)
            bank_asked: dict[str, list[str]] = {}
            for taken in mcqs:
                bank_asked.setdefault(taken.get("slo_code") or "", []).append(
                    taken.get("question_text", "")
                )
            written_mcqs = await asyncio.gather(
                *(
                    generate_mcqs(
                        llm, slo_contexts[code], sum(mix.values()),
                        level_mix=mix, avoid=bank_asked.get(code, []),
                    )
                    for code, mix in mcq_orders
                    if slo_contexts.get(code)
                ),
                return_exceptions=True,
            )
            usable = [(code, mix) for code, mix in mcq_orders if slo_contexts.get(code)]
            for (code, _), result in zip(usable, written_mcqs):
                if isinstance(result, list):
                    mcqs.extend({"bank_id": None, "slo_code": code, **p} for p in result)
            mcqs = blueprint.dedupe(mcqs)[: plan["mcq"]]

        # Sections B and C: one question per SLO, at the level the paper planned
        srq_plan = written_levels[: plan["srq"]]
        erq_plan = written_levels[plan["srq"] : plan["srq"] + plan["erq"]]
        srq_service = SrqService()
        marks = question_marks(scope_info["subject_code"])
        written = await asyncio.gather(
            *(
                srq_service.generate(project_id, user_id, code, marks=marks["srq"], level=level)
                for code, _, level in srq_plan
            ),
            *(
                srq_service.generate(
                    project_id, user_id, code, long=True, marks=marks["erq"], level=level
                )
                for code, _, level in erq_plan
            ),
        )
        srqs, erqs = written[: len(srq_plan)], written[len(srq_plan) :]

        sections = [
            {
                "id": "A",
                "title": "Section A: Multiple choice questions",
                "items": [
                    self._mcq_item(f"m{index + 1}", m, marks["mcq"])
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

        with self._get_db_session() as db:
            paper = PracticePaper(
                id=str(uuid4()),
                project_id=project_id,
                user_id=user_id,
                title=f"{scope_info['subject_title']} practice paper: {scope_info['scope']}",
                length=length if length in LENGTHS else "mini",
                time_limit_minutes=plan["minutes"],
                sections=sections,
                total_marks=float(self._max_marks(sections)),
                answers={},
                status="ready",
            )
            db.add(paper)
            db.commit()
            db.refresh(paper)
            return self._to_dto(db, paper)

    async def _create_board(
        self, project_id: str, user_id: str, length: str, topic: str | None
    ) -> PaperDto:
        """Create a board paper in the "preparing" state and queue its building."""
        with self._get_db_session() as db:
            scope_info = self._scope(db, project_id, user_id, topic)
            plan = board_plan(length, scope_info["subject_code"])
            label = "FBISE board paper" if length == "board" else "FBISE half paper"
            paper = PracticePaper(
                id=str(uuid4()),
                project_id=project_id,
                user_id=user_id,
                title=f"{scope_info['subject_title']} {label} (new pattern): {scope_info['scope']}",
                length=length,
                time_limit_minutes=plan["minutes"],
                sections=[],
                total_marks=float(board_total(plan)),
                answers={},
                status="preparing",
            )
            db.add(paper)
            db.commit()
            paper_id = paper.id

        data = {"paper_id": paper_id, "project_id": project_id, "user_id": user_id, "length": length}
        if topic:
            data["topic"] = topic
        if self.queue_service is not None:
            from edu_queue.schemas import TaskType

            self.queue_service.send_message({"type": TaskType.PAPER_GENERATION, "data": data})
        else:
            await self.build_board(**data)
        return self.get(paper_id, user_id)

    async def build_board(
        self, paper_id: str, project_id: str, user_id: str, length: str, topic: str | None = None
    ) -> None:
        """Build a queued board paper (run by the worker). Marks it failed on errors."""
        try:
            await asyncio.wait_for(
                self._build_board(paper_id, project_id, user_id, length, topic),
                timeout=BUILD_TIMEOUT_SECONDS,
            )
        except Exception:
            with self._get_db_session() as db:
                paper = db.get(PracticePaper, paper_id)
                if paper is not None and paper.status == "preparing":
                    paper.status = "failed"
                    db.commit()
            raise

    async def _build_board(
        self, paper_id: str, project_id: str, user_id: str, length: str, topic: str | None
    ) -> None:
        from edu_ai.agents.bank_agent import generate_mcqs, generate_stimulus_set
        from edu_ai.agents.slo_context import load_slo
        from edu_ai.llm import GENERATION, create_chat_model

        with self._get_db_session() as db:
            paper = db.get(PracticePaper, paper_id)
            if paper is None or paper.status != "preparing":
                return
            scope_info = self._scope(db, project_id, user_id, topic)
            plan = board_plan(length, scope_info["subject_code"])
            grade_subject_id = scope_info["grade_subject_id"]
            slo_info, order, domain_of = scope_info["slo_info"], scope_info["order"], scope_info["domain_of"]
            language_code = db.get(Project, project_id).language_code

            # Section A: straight MCQs from the bank, one per SLO first
            mcqs = self._bank_mcqs(db, grade_subject_id, order, plan["mcq"])

            # Stimulus sets on SLOs that ask for understanding or application.
            # blueprint.spread never repeats a code, so a narrow scope yields
            # fewer sets instead of printing one scenario three times over.
            deep = [c for c in order if {"U", "A"} & set(slo_info[c]["levels"])] or order
            stimulus_codes = blueprint.spread(deep, domain_of, plan["stimulus"])
            stimuli: dict[str, dict] = {}
            used_sets: set[str] = set()
            for code in stimulus_codes:
                item = next(
                    (i for i in usable_items(db, grade_subject_id, code, "stimulus") if i.id not in used_sets),
                    None,
                )
                if item is not None:
                    used_sets.add(item.id)
                    stimuli[code] = dict(item.payload)

            # What the AI still has to write for Section A, and at which level.
            # Every SLO in scope is drawn on and the levels follow the
            # framework's weighting, decided here before anything is written.
            levels_of = {code: slo_info[code]["levels"] for code in order}
            missing = plan["mcq"] - len(mcqs)
            mcq_orders = blueprint.group_by_slo(
                blueprint.assign_levels(
                    blueprint.mcq_pool(order, domain_of, missing),
                    levels_of, missing, domain_of,
                )
            )

            # Sections B and C: each choice offers two comparable alternatives -
            # the same cognitive level, and one domain wherever the scope allows
            written_codes = [c for c in order if c not in stimulus_codes] or order
            pairs = blueprint.choice_pairs(
                written_codes, levels_of, plan["srq"] + plan["erq"], domain_of
            )

            wanted_codes = {code for code, _ in mcq_orders} | set(stimulus_codes)
            for first, second, _ in pairs:
                wanted_codes.update((first, second))
            contexts = {
                code: load_slo(db, code, grade_subject_id=grade_subject_id)
                for code in wanted_codes
            }

        llm = create_chat_model(task=GENERATION, temperature=0.6)
        limit = asyncio.Semaphore(AI_CONCURRENCY)

        async def limited(coro):
            async with limit:
                return await coro

        # Top up the straight MCQs and write the missing stimulus sets, in parallel.
        # One call per SLO for its whole share: a single call can see everything
        # it has written, so it cannot repeat itself, and the questions already
        # taken from the bank are listed so it does not write those again.
        bank_asked: dict[str, list[str]] = {}
        for taken in mcqs:
            bank_asked.setdefault(taken.get("slo_code") or "", []).append(
                taken.get("question_text", "")
            )
        mcq_jobs = [
            (code, limited(generate_mcqs(
                llm, contexts[code], sum(mix.values()),
                language_code=language_code, level_mix=mix,
                avoid=bank_asked.get(code, []),
            )))
            for code, mix in mcq_orders
            if contexts.get(code)
        ]
        stimulus_jobs = [
            (code, limited(generate_stimulus_set(llm, contexts[code], language_code)))
            for code in stimulus_codes
            if code not in stimuli and contexts.get(code)
        ]
        srq_service = SrqService()
        # Both halves of a choice are written at the pair's level, so (a) and
        # (b) ask the same thing of the student in two ways
        srq_pairs = pairs[: plan["srq"]]
        erq_pairs = pairs[plan["srq"] : plan["srq"] + plan["erq"]]
        written_jobs = [
            limited(srq_service.generate(
                project_id, user_id, code, marks=plan["srq_marks"], parts=False, level=level,
            ))
            for first, second, level in srq_pairs
            for code in (first, second)
        ] + [
            limited(srq_service.generate(
                project_id, user_id, code, long=True, marks=plan["erq_marks"],
                parts=plan["erq_parts"][index], level=level,
            ))
            for index, (first, second, level) in enumerate(erq_pairs)
            for code in (first, second)
        ]
        srq_codes = [code for pair in srq_pairs for code in pair[:2]]
        results = await asyncio.gather(
            *(job for _, job in mcq_jobs), *(job for _, job in stimulus_jobs), *written_jobs,
            return_exceptions=True,
        )
        mcq_results = results[: len(mcq_jobs)]
        stimulus_results = results[len(mcq_jobs) : len(mcq_jobs) + len(stimulus_jobs)]
        written_results = results[len(mcq_jobs) + len(stimulus_jobs) :]

        for (code, _), result in zip(mcq_jobs, mcq_results):
            if isinstance(result, list):
                mcqs.extend({"bank_id": None, "slo_code": code, **payload} for payload in result)
        # Last line of defence on repeats: the SLOs are written in parallel and
        # a model told not to repeat itself still sometimes does. A paper one
        # question short is worth more than a paper that asks one twice.
        mcqs = blueprint.dedupe(mcqs)
        with self._get_db_session() as db:
            for (code, _), result in zip(stimulus_jobs, stimulus_results):
                if isinstance(result, dict):
                    stimuli[code] = result
                    # Keep new sets in the shared bank as drafts, so later papers are faster
                    db.add(ContentItem(
                        id=str(uuid4()), grade_subject_id=grade_subject_id, slo_code=code,
                        kind="stimulus", payload=result, review_status="draft", source="ai_generated",
                    ))
            db.commit()

        srqs = [r for r in written_results[: len(srq_codes)] if not isinstance(r, Exception)]
        erqs = [r for r in written_results[len(srq_codes) :] if not isinstance(r, Exception)]
        if len(srqs) < 2 * plan["srq"] or len(erqs) < 2 * plan["erq"]:
            failure = next((r for r in written_results if isinstance(r, Exception)), None)
            raise ValueError("Could not write all the written questions for the paper") from failure

        # Section A: straight MCQs, then the stimulus sets
        items = [self._mcq_item(f"m{i + 1}", m, plan["mcq_marks"]) for i, m in enumerate(mcqs[: plan["mcq"]])]
        number = len(items)
        for set_index, code in enumerate(stimulus_codes):
            stimulus = stimuli.get(code)
            if not stimulus:
                continue
            for question in stimulus["questions"][:STIMULUS_SIZE]:
                number += 1
                item = self._mcq_item(f"m{number}", {"slo_code": code, **question}, plan["mcq_marks"])
                item["stimulus"] = stimulus["scenario"]
                item["group"] = f"s{set_index + 1}"
                items.append(item)

        def written_items(questions, kind: str, section: str) -> list[dict]:
            out = []
            for index, question in enumerate(questions):
                out.append({
                    "id": question.id, "type": kind, "marks": question.marks,
                    "slo_code": question.slo_code, "cognitive_level": question.cognitive_level,
                    "choice_group": f"{section}{index // 2 + 1}", "choice": "ab"[index % 2],
                })
            return out

        sections = [
            {"id": "A", "title": "Section A: Multiple choice questions", "items": items},
            {"id": "B", "title": "Section B: Short questions (answer (a) OR (b) in each)",
             "items": written_items(srqs, "srq", "B")},
            {"id": "C", "title": "Section C: Long questions (answer (a) OR (b) in each)",
             "items": written_items(erqs, "erq", "C")},
        ]
        # Say so in the log when the finished paper drifted off the framework's
        # weighting. The levels were planned, so drift means the model labelled
        # questions differently from the level it was asked for - which is worth
        # knowing about and is invisible from the paper itself.
        drift = blueprint.off_target(
            [item.get("cognitive_level") for section in sections for item in section["items"]]
        )
        if drift:
            print(f"paper {paper_id} is off the cognitive target: {drift}")

        with self._get_db_session() as db:
            paper = db.get(PracticePaper, paper_id)
            paper.sections = sections
            paper.total_marks = float(self._max_marks(sections))
            paper.status = "ready"
            db.commit()

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
        """Mark the paper: MCQs instantly, written answers all at once.

        With an internal choice, only the answered question counts (the better one if
        the student answered both)."""
        with self._get_db_session() as db:
            paper = self._get_paper(db, paper_id, user_id)
            if paper.status == "submitted":
                return self._to_dto(db, paper)
            if paper.status != "ready":
                raise NotFoundError("This paper is not ready yet")
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
                choice_best: dict[str, float] = {}
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
                    group = item.get("choice_group")
                    if group:
                        choice_best[group] = max(choice_best.get(group, 0.0), awarded)
                    else:
                        score += awarded
                score += sum(choice_best.values())
                section_results.append(
                    PaperSectionResultDto(
                        id=section["id"], title=section["title"], score=score,
                        max_score=float(self._max_marks([section])),
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

    # ---------------------------------------------------------------- helpers

    def _scope(self, db, project_id: str, user_id: str, topic: str | None) -> dict:
        """The examined SLOs of the workspace in scope: a domain, a topic or everything."""
        from edu_ai.tools.syllabus import search_slos

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

        scope = "whole syllabus"
        wanted = (topic or "").strip().lower()
        candidates = [slo for slo, _ in rows]
        if wanted and wanted not in ("whole syllabus", "all", "everything"):
            domain = next(
                (d for _, d in rows if d.name.lower() in wanted or wanted in d.name.lower()), None
            )
            if domain is not None:
                candidates = [slo for slo, d in rows if d.id == domain.id]
                scope = domain.name
            else:
                codes = {m["code"] for m in search_slos(grade_subject.id, topic, limit=10)}
                matched = [slo for slo in candidates if slo.code in codes]
                if matched:
                    candidates = matched
                    scope = topic.strip()
        order = [slo.code for slo in candidates]
        random.shuffle(order)
        return {
            "grade_subject_id": grade_subject.id,
            "subject_code": grade_subject.subject.code,
            "subject_title": f"{grade_subject.subject.name} {GRADE_NAMES.get(grade_subject.grade, grade_subject.grade)}",
            "scope": scope,
            "slo_info": {
                slo.code: {"code": slo.code, "levels": list(slo.cognitive_levels or [])}
                for slo in candidates
            },
            "order": order,
            "domain_of": {slo.code: d.code for slo, d in rows},
        }

    @staticmethod
    def _bank_mcqs(db, grade_subject_id: str, order: list[str], wanted: int) -> list[dict]:
        """Bank MCQs (teacher-approved first), one per SLO, then a second and third pass."""
        mcqs: list[dict] = []
        used: set[str] = set()
        for code in order * 3:
            if len(mcqs) >= wanted:
                break
            item = next(
                (i for i in usable_items(db, grade_subject_id, code, "mcq") if i.id not in used),
                None,
            )
            if item is not None:
                used.add(item.id)
                mcqs.append({"bank_id": item.id, "slo_code": code, **item.payload})
        return mcqs

    @staticmethod
    def _mcq_item(item_id: str, m: dict, marks: float) -> dict:
        return {
            "id": item_id,
            "type": "mcq",
            "marks": marks,
            "slo_code": m.get("slo_code"),
            "cognitive_level": m.get("cognitive_level"),
            "question": m.get("question_text", ""),
            "options": {k: m.get(f"option_{k}", "") for k in ("a", "b", "c", "d")},
            "correct_option": (m.get("correct_option") or "").lower()[:1],
            "explanation": m.get("explanation"),
        }

    @staticmethod
    def _max_marks(sections: list[dict]) -> float:
        """Marks available: with an internal choice, one question per pair counts."""
        total = 0.0
        groups: dict[str, float] = {}
        for section in sections:
            for item in section["items"]:
                group = item.get("choice_group")
                if group:
                    groups[group] = max(groups.get(group, 0.0), float(item["marks"]))
                else:
                    total += float(item["marks"])
        return total + sum(groups.values())

    def _to_dto(self, db, paper: PracticePaper) -> PaperDto:
        submitted = paper.status == "submitted"
        written_ids = [
            item["id"] for s in paper.sections for item in s["items"] if item["type"] != "mcq"
        ]
        questions = {
            q.id: q.question
            for q in db.query(SrqQuestion).filter(SrqQuestion.id.in_(written_ids))
        } if written_ids else {}
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
                        stimulus=item.get("stimulus"),
                        group=item.get("group"),
                        choice_group=item.get("choice_group"),
                        choice=item.get("choice"),
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
