"""Practice the student does right inside the chat (shown as interactive cards).

The card is the answer, so these tools end the tutor's turn (return_direct): the
student sees the card without waiting for another model call. Chat history keeps
a short note of each card (ChatService._practice_note).

When a request leaves important choices open, the tutor first asks a few questions
(ask_practice_questions, shown as a card of tappable options); the student's
answers come back as their next message and go into the practice tools' settings.
"""

import json
from contextlib import suppress
from typing import Literal

from edu_ai.chatbot.context import ChatbotContext
from edu_ai.tools.syllabus import slo_choices
from edu_core.mastery import slo_mastery
from edu_core.services.quizzes import DEFAULT_QUESTIONS
from edu_core.services.flashcard_groups import FlashcardGroupService
from edu_core.services.mind_maps import MindMapService
from edu_core.services.papers import PaperService
from edu_core.services.quizzes import QuizService
from edu_db.models import CurriculumDomain, Slo
from edu_db.session import get_session_factory
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel, Field

KINDS = ("quiz", "flashcards", "mind_map", "paper")
# Used only if nothing else is left to ask, so the card is never shown empty.
FALLBACK_QUESTION = {
    "paper": {
        "question": "How long should the paper be?",
        "options": [
            "Full board paper (3 hours)",
            "Half paper (90 minutes)",
            "Standard (45 minutes)",
            "Mini (20 minutes)",
        ],
        "multiple": False,
        "recommended": ["Full board paper (3 hours)"],
    },
    "quiz": {
        "question": "How many questions?",
        "options": ["5", "10", "15"],
        "multiple": False,
        "recommended": ["10"],
    },
    "flashcards": {
        "question": "What should the cards focus on?",
        "options": ["Definitions", "Formulas and units", "Key facts", "A mix"],
        "multiple": False,
        "recommended": ["A mix"],
    },
    "mind_map": {
        "question": "How detailed?",
        "options": ["Quick revision", "Detailed"],
        "multiple": False,
        "recommended": ["Quick revision"],
    },
}
WEAK = 0.6  # SLO mastery below this is pre-selected as "needs practice"
WHOLE_SYLLABUS = "Whole syllabus"


class SetupQuestion(BaseModel):
    question: str = Field(..., description="A short question, e.g. 'What kind of questions?'")
    options: list[str] = Field(..., description="2 to 5 short answers the student can tap")
    multiple: bool = Field(False, description="True if the student may pick more than one")
    recommended: list[str] = Field(
        default_factory=list,
        description="Options to pre-select, from what the conversation already shows",
    )


def _short(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


# Ways a model has been seen to ask "which part of the syllabus?" without using
# the word chapter.
SCOPE_WORDS = ("chapter", "topic", "focus", "cover", "syllabus", "area", "which part")


def _asks_about_scope(question: str) -> bool:
    """Whether a question the model wrote is really asking which part to cover."""
    text = question.lower()
    return any(word in text for word in SCOPE_WORDS)


def _part_question(ctx: ChatbotContext, kind: str, topic: str) -> dict | None:
    """"Which part?" built from the real syllabus, with weak SLOs pre-selected."""
    grade_subject_id = ctx.fbise.grade_subject_id if ctx.fbise else None
    if not grade_subject_id:
        return None
    with get_session_factory()() as db:
        if kind == "paper":
            domains = (
                db.query(CurriculumDomain.name)
                .join(Slo, Slo.domain_id == CurriculumDomain.id)
                .filter(
                    CurriculumDomain.grade_subject_id == grade_subject_id,
                    Slo.assessment_form == "summative",
                )
                .group_by(CurriculumDomain.name, CurriculumDomain.sort_order)
                .order_by(CurriculumDomain.sort_order)
                .all()
            )
            names = [name for (name,) in domains]
            if not names:
                return None
            wanted = topic.strip().lower()
            match = next((n for n in names if wanted and (wanted in n.lower() or n.lower() in wanted)), None)
            # The student has already said what they want, so asking again just
            # makes them repeat themselves. They rarely name a chapter the way
            # the syllabus does: "complex numbers" sits inside "Numbers and
            # Algebra". So when the chapter name does not match, fall back to the
            # same syllabus search the paper itself uses to pick its questions —
            # if that finds the topic, there is nothing left to ask.
            named = wanted not in ("", WHOLE_SYLLABUS.lower(), "all", "everything")
            if match or (named and slo_choices(grade_subject_id, topic, limit=3)):
                return None
            return {
                "question": "Which chapters should the paper cover?",
                "options": [WHOLE_SYLLABUS, *names][:6],
                "multiple": False,
                "recommended": [WHOLE_SYLLABUS],
            }
        slos = slo_choices(grade_subject_id, topic, limit=5)
        if not slos:
            return None
        mastery = slo_mastery(db, ctx.user_id, [s["code"] for s in slos])
    options = [f"{s['code']}: {_short(s['description'])}" for s in slos]
    weak = [
        option
        for option, slo in zip(options, slos)
        if (m := mastery.get(slo["code"])) and m[1] is not None and m[1] < WEAK
    ]
    if kind == "mind_map":
        options.append(f"Whole chapter: {slos[0]['domain']}")
    return {
        "question": "Which part of the syllabus?",
        "options": options,
        "multiple": True,
        "recommended": weak or options[:1],
    }


@tool(
    "ask_practice_questions",
    return_direct=True,
    description=(
        "Before making a quiz, flashcards, mind map or practice paper whose important choices "
        "are still open, show the student a card of 2-4 short questions with tappable answers. "
        "Ask ONLY about what the student has not already said. If their message already covers "
        "what to make, what it is about and how long or how many, do not use this tool at all: "
        "make the thing straight away. Never ask a question the student has already answered. "
        "Write questions that fit this topic and conversation, e.g. for Physics 'What kind of "
        "questions?' (Theory and concepts / Numericals / Derivations / Mixed like the board "
        "paper), 'How hard?' (Easy / Board level / Challenging), 'How many?' (5 / 10 / 15), "
        "'Why are you practising?' (First time learning / Test revision / Final exam); for "
        "flashcards what to focus on (Definitions / Formulas and units / Key facts); for a mind "
        "map how detailed (Quick revision / Detailed) and what to include (Formulas / "
        "Derivations / Examples / Exam tips); for a paper how long it should be (Mini 20 min / "
        "Standard 45 min / Half paper 90 min / Full board paper 3 hours), pre-selecting the full "
        "board paper whenever the student mentioned the board or its pattern. Never ask which "
        "part of the syllabus to use - not chapters, not topics, not what to focus on, not "
        "which areas to cover: the card adds that question itself from the real syllabus, and "
        "leaves it out when the student has already named the part. Pre-select in "
        "'recommended' what the conversation already shows. kind: quiz, flashcards, mind_map "
        "or paper. topic: English keywords."
    ),
)
async def ask_practice_questions(
    kind: Literal["quiz", "flashcards", "mind_map", "paper"],
    topic: str,
    questions: list[SetupQuestion],
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    ctx = runtime.context
    kind = kind if kind in KINDS else "quiz"
    cleaned = []
    for item in questions:
        options = [_short(o, 80) for o in item.options if o and o.strip()][:5]
        if not item.question.strip() or len(options) < 2:
            continue
        recommended = [r for r in (_short(r, 80) for r in item.recommended) if r in options]
        cleaned.append(
            {
                "question": _short(item.question, 100),
                "options": options,
                "multiple": item.multiple,
                "recommended": recommended[: len(options) if item.multiple else 1],
            }
        )
    with suppress(Exception):
        if part := _part_question(ctx, kind, topic):
            # This card already asks which part of the syllabus to cover, built
            # from the real chapter list. Anything the model wrote that asks the
            # same thing in other words has to go: the two are written
            # independently, so they can offer choices that contradict each
            # other (chapters from one chapter, sub-topics from another).
            cleaned = [q for q in cleaned if not _asks_about_scope(q["question"])]
            cleaned = [part, *cleaned[:4]]
    # The card is the whole turn, so it must never come back blank: if nothing
    # survived, ask the one thing that always changes the outcome.
    if not cleaned:
        cleaned = [dict(FALLBACK_QUESTION[kind])]
    cleaned = cleaned[:5]
    for number, item in enumerate(cleaned, start=1):
        item["id"] = f"q{number}"
    return json.dumps(
        {
            "kind": kind,
            "topic": topic,
            "questions": cleaned,
            "message": (
                "The student now sees these questions as a card of tappable answers and answers "
                "them there; their choices come back as their next message. Do not repeat the "
                "questions in text."
            ),
        },
        ensure_ascii=False,
    )


@tool(
    "practice_quiz",
    return_direct=True,
    description=(
        "Start an interactive MCQ quiz that the student answers right here in the chat "
        "(tap an option, instant feedback, score at the end; answers update their SLO mastery). "
        "Use this whenever the student wants to take, attempt or practise a quiz or MCQs. "
        "topic: the topic in English keywords, e.g. 'vector product'. count: 1-100, default 10. "
        "slo_codes: the SLO codes the student chose or named, e.g. ['P-11-B-02']. "
        "style: theory, numerical, derivation or mixed (default). "
        "level: easy, board (default) or challenging. "
        "notes: anything else they asked for, e.g. 'final exam revision'."
    ),
)
async def practice_quiz(
    topic: str,
    runtime: ToolRuntime[ChatbotContext],
    count: int = DEFAULT_QUESTIONS,
    slo_codes: list[str] | None = None,
    style: str = "mixed",
    level: str = "board",
    notes: str | None = None,
) -> str:
    ctx = runtime.context
    quiz, questions, source = await QuizService(queue_service=ctx.queue).create_practice_quiz(
        project_id=ctx.project_id,
        topic=topic,
        count=count,
        slo_codes=slo_codes,
        search_service=ctx.search,
        style=style,
        level=level,
        notes=notes,
    )
    if source != "bank" and ctx.usage:
        with suppress(Exception):
            ctx.usage.check_and_increment(ctx.user_id, "quiz_generation")
    return json.dumps(
        {
            "quiz_id": quiz.id,
            "slo_code": quiz.slo_code,
            "questions": questions,
            "message": (
                f"The student now sees an interactive quiz card with {questions} questions in the chat "
                "and answers it there. Reply with one short, encouraging sentence. Do not write out "
                "the questions or answers, and never mention any ID. After they finish, they may ask "
                "you about their mistakes."
            ),
        },
        ensure_ascii=False,
    )


@tool(
    "practice_flashcards",
    return_direct=True,
    description=(
        "Start interactive flashcards that the student flips and studies right here in the chat "
        "(tap to flip, 'Knew it' / 'Still learning'; results update their SLO mastery). "
        "Use this whenever the student wants flashcards to study or revise. "
        "topic: the topic in English keywords, e.g. 'dot product'. count: 1-100, default 10. "
        "slo_codes: the SLO codes the student chose or named. focus: what the cards should "
        "cover, e.g. 'formulas and units'. level: easy, board (default) or challenging. "
        "notes: anything else they asked for."
    ),
)
async def practice_flashcards(
    topic: str,
    runtime: ToolRuntime[ChatbotContext],
    count: int = DEFAULT_QUESTIONS,
    slo_codes: list[str] | None = None,
    focus: str | None = None,
    level: str = "board",
    notes: str | None = None,
) -> str:
    ctx = runtime.context
    group, cards = await FlashcardGroupService(
        queue_service=ctx.queue
    ).create_practice_flashcards(
        project_id=ctx.project_id,
        topic=topic,
        count=count,
        slo_codes=slo_codes,
        search_service=ctx.search,
        focus=focus,
        level=level,
        notes=notes,
    )
    if ctx.usage:
        with suppress(Exception):
            ctx.usage.check_and_increment(ctx.user_id, "flashcard_generation")
    return json.dumps(
        {
            "group_id": group.id,
            "slo_code": group.slo_code,
            "cards": cards,
            "message": (
                f"The student now sees {cards} interactive flashcards in the chat and studies them "
                "there. Reply with one short, encouraging sentence. Do not write out the cards, and "
                "never mention any ID."
            ),
        },
        ensure_ascii=False,
    )


@tool(
    "practice_mind_map",
    return_direct=True,
    description=(
        "Show a visual, zoomable mind map right here in the chat. In a syllabus subject its "
        "structure follows the FBISE SLOs: pass a domain name (e.g. 'Mechanics') for the whole "
        "domain, or a topic (e.g. 'vector product') for its SLOs with key points. Use this "
        "whenever the student asks for a mind map. topic: English keywords. slo_codes: the SLO "
        "codes the student chose. detail: quick, standard (default) or detailed. include: what "
        "the points should include, e.g. ['formulas', 'exam tips']. notes: anything else."
    ),
)
async def practice_mind_map(
    topic: str,
    runtime: ToolRuntime[ChatbotContext],
    slo_codes: list[str] | None = None,
    detail: str = "standard",
    include: list[str] | None = None,
    notes: str | None = None,
) -> str:
    ctx = runtime.context
    detail = detail.strip().lower()
    mind_map = await MindMapService(queue_service=ctx.queue).create_practice_mind_map(
        user_id=ctx.user_id,
        project_id=ctx.project_id,
        topic=topic,
        search_service=ctx.search,
        slo_codes=slo_codes,
        detail="quick" if detail.startswith("quick") else "detailed" if detail.startswith("detail") else "standard",
        include=include,
        notes=notes,
    )
    if ctx.usage:
        with suppress(Exception):
            ctx.usage.check_and_increment(ctx.user_id, "mindmap_generation")
    return json.dumps(
        {
            "mind_map_id": mind_map.id,
            "title": mind_map.title,
            "message": (
                "The student now sees the visual mind map in the chat (they can zoom, open branches "
                "and tap a node for details). Reply with one short sentence. Do not draw or write out "
                "the mind map in text, and never mention any ID."
            ),
        },
        ensure_ascii=False,
    )


@tool(
    "practice_paper",
    return_direct=True,
    description=(
        "Make an FBISE-style practice paper the student attempts on an exam page: Section A MCQs, "
        "Section B short questions answered by typing, Section C long questions, all marked like "
        "an examiner. Use this when the student asks for a paper, test or mock exam. topic: a "
        "domain (e.g. 'Mechanics') or topic, or empty for the whole syllabus. "
        "length is how LONG the paper is, never how hard it is: 'mini' (about 20 minutes), "
        "'standard' (about 45 minutes), 'half' (FBISE's new pattern at half length, 90 minutes) "
        "or 'board' (the full FBISE new-pattern paper, 3 hours, 80 marks, 100 for Mathematics: "
        "stimulus MCQs and questions with an internal choice). "
        "Use 'board' whenever the student mentions the board, the board pattern, 'board level', "
        "a full paper, a real paper, a proper paper, a mock exam, or 'our pattern': all of those "
        "ask for the full paper, not for a short one made harder. Only use 'mini' when they want "
        "something quick and say nothing about the board. Board and half papers take a minute or "
        "two to prepare."
    ),
)
async def practice_paper(
    runtime: ToolRuntime[ChatbotContext],
    topic: str | None = None,
    length: str = "mini",
) -> str:
    ctx = runtime.context
    if topic and topic.strip().lower() in (WHOLE_SYLLABUS.lower(), "all", "everything"):
        topic = None
    paper = await PaperService(queue_service=ctx.queue).create(
        project_id=ctx.project_id,
        user_id=ctx.user_id,
        length=length if length in ("mini", "standard", "board", "half") else "mini",
        topic=topic,
    )
    if ctx.usage:
        with suppress(Exception):
            ctx.usage.check_and_increment(ctx.user_id, "quiz_generation")
    questions = sum(len(s.items) for s in paper.sections)
    return json.dumps(
        {
            "paper_id": paper.id,
            "title": paper.title,
            "questions": questions,
            "total_marks": paper.total_marks,
            "minutes": paper.time_limit_minutes,
            "status": paper.status,
            "message": (
                f"The student now sees a card for the paper ({paper.total_marks:g} marks, "
                f"{paper.time_limit_minutes} minutes)"
                + (", which is being prepared and opens in a minute or two" if paper.status == "preparing" else f" with {questions} questions")
                + ". Reply with one short, encouraging sentence with a tip for the exam. Do not "
                "write out the questions, and never mention any ID."
            ),
        },
        ensure_ascii=False,
    )


tools = [ask_practice_questions, practice_quiz, practice_flashcards, practice_mind_map, practice_paper]
