"""End-to-end AI check: upload -> index -> search -> chat -> quiz/flashcards/note/mind map,
then the FBISE demo flow: onboarding -> syllabus map -> tutor in Roman Urdu -> SLO quiz -> mastery
-> SRQ marking -> predicted grade.

Runs below the HTTP/auth layer with the same services the API routes use, against
the database and storage configured in the environment (or the repository root
``.env``). The worker must be running. Exits with code 1 if any step fails.
On Google Cloud it runs as the ``edu-e2e`` Cloud Run job (deploy/gcp/deploy.sh e2e).

Usage (from the repository root):
    uv run --package edu-api python scripts/e2e_ai_check.py [--pdf FILE] [--keep]
    uv run --package edu-api python scripts/e2e_ai_check.py --cleanup
"""

import argparse
import asyncio
import io
import json
import sys
import time
from pathlib import Path

from docx import Document as DocxDocument
from edu_core.services import (
    AttemptService,
    ChatService,
    CurriculumService,
    DocumentUploadService,
    FlashcardGroupService,
    MindMapService,
    NoteService,
    PaperService,
    PracticeService,
    ProfileService,
    ProgressService,
    ProjectService,
    QuizService,
    SearchService,
    SrqService,
    UserService,
)
from edu_core import practice_options
from edu_core.storage import create_storage
from edu_db.models import (
    Document,
    Flashcard,
    MindMap,
    Note,
    PracticePaper,
    Project,
    QuizQuestion,
    User,
)
from edu_db.session import get_session_factory, init_db
from edu_queue.schemas import TaskType
from edu_queue.service import QueueService
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
TEST_USER = "e2e-test-user"
ICS_USER = "e2e-test-user-ics"
# A login deleted in Identity Platform, then the same email signing up again
OLD_LOGIN, NEW_LOGIN = "e2e-test-user-deleted", "e2e-test-user-resignup"
TOPIC = "projectile motion and circular motion"
QUESTION = "According to my course document, what must I be able to do for projectile motion? Keep it short."
STEP_TIMEOUT = 420

SAMPLE_PARAGRAPHS = [
    ("Physics Grade XI: Mechanics (FBISE SLOs)", "Title"),
    ("Projectile motion", "Heading 1"),
    (
        "[SLO: P-11-B-05] Evaluate and analyze projectile motion in the absence of air resistance. "
        "The horizontal component of velocity is constant; acceleration is vertical and equal to g. "
        "Students determine how high it goes, how far it goes along level land, where it is after a "
        "given time and how long it remains in flight. The range is R = v^2 sin(2θ)/g, maximum at θ = 45°.",
        None,
    ),
    (
        "[SLO: P-11-B-06] Predict qualitatively how air resistance affects projectile motion, "
        "reducing both the horizontal and vertical components of velocity and hence the range.",
        None,
    ),
    ("Circular motion", "Heading 1"),
    (
        "[SLO: P-11-B-08] Define and calculate angular displacement, angular velocity and angular "
        "acceleration using S = rθ, v = rω, ω = 2π/T and a = rω² = v²/r.",
        None,
    ),
    (
        "[SLO: P-11-B-14] Define and calculate centripetal force using F = mrω² and F = mv²/r. "
        "[SLO: P-11-B-16] Explain why objects in orbiting satellites appear to be weightless.",
        None,
    ),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str
    storage_backend: str = "supabase"
    storage_bucket: str = "documents"
    supabase_url: str = ""
    supabase_service_role_key: str = ""


settings = Settings()
init_db(settings.database_url)
Session = get_session_factory()
storage = create_storage(
    settings.storage_backend,
    settings.storage_bucket,
    settings.supabase_url,
    settings.supabase_service_role_key,
)
failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{': ' + detail if detail else ''}")
    if not ok:
        failures.append(label)
    return ok


def db_get(fn):
    with Session() as db:
        return fn(db)


def wait_for(fn, timeout: int = STEP_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        if result := fn():
            return result, time.time() - start
        time.sleep(5)
    return None, time.time() - start


def sample_docx() -> bytes:
    doc = DocxDocument()
    for text_, style in SAMPLE_PARAGRAPHS:
        doc.add_paragraph(text_, style=style) if style else doc.add_paragraph(text_)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def cleanup() -> None:
    with Session() as db:
        users = [TEST_USER, ICS_USER, OLD_LOGIN, NEW_LOGIN]
        project_ids = [p.id for p in db.query(Project).filter(Project.owner_id.in_(users))]
        for pid in project_ids:
            storage.delete(storage.list_paths(pid))
            db.execute(text("DELETE FROM jobs WHERE payload->>'project_id' = :pid"), {"pid": pid})
        db.query(User).filter(User.id.in_(users)).delete()
        db.commit()
    print(f"Cleaned up the test user, {len(project_ids)} project(s), their files and jobs")


async def run(pdf: Path | None) -> None:
    storage.ensure_bucket()
    queue = QueueService()
    user = UserService().get_or_create_user_from_token(
        user_id=TEST_USER, email="e2e-test@local.test", name="E2E Test"
    )
    project = ProjectService().create_project(
        owner_id=user.id, name="E2E Physics XI check", language_code="en"
    )
    print(f"Project {project.id}")

    # 1. Upload and index
    content, filename = (
        (pdf.read_bytes(), pdf.name) if pdf else (sample_docx(), "physics_xi_slos.docx")
    )
    doc_id = DocumentUploadService(settings.database_url, storage).upload_document(
        file_content=content, filename=filename, project_id=project.id, owner_id=user.id
    )
    queue.send_message(
        {
            "type": TaskType.DOCUMENT_PROCESSING,
            "data": {"document_id": doc_id, "project_id": project.id, "user_id": user.id},
        }
    )
    print("1. Document processing")
    status, secs = wait_for(
        lambda: db_get(
            lambda db: (d := db.get(Document, doc_id)) and d.status in ("indexed", "failed") and d.status
        )
    )
    doc = db_get(lambda db: db.get(Document, doc_id))
    segments = db_get(lambda db: len(db.get(Document, doc_id).segments))
    if not check("indexed", status == "indexed", f"{status} in {secs:.0f}s, {segments} chunks"):
        return
    check("summary written", bool(doc.summary), (doc.summary or "")[:120])

    # 2. Search
    search = SearchService(
        database_url=settings.database_url,
        azure_openai_embedding_deployment="",
        azure_openai_endpoint="",
        azure_openai_api_version="",
    )
    results = await search.search_documents(
        query="range of a projectile", project_id=project.id, top_k=3
    )
    print("2. Search")
    check("search finds the document", bool(results), f"{len(results)} result(s)")

    # 3. Chat (tool call + streaming)
    print("3. Chat")
    chat_svc = ChatService(search_service=search, queue_service=queue)
    chat = chat_svc.create_chat(project_id=project.id, user_id=user.id, title="E2E chat")
    async for _ in chat_svc.stream_chat_events(
        chat.id, user.id, [{"type": "text", "text": QUESTION}]
    ):
        pass
    detail = chat_svc.get_chat(chat_id=chat.id, user_id=user.id, include_messages=True)
    replies = [m for m in detail.messages if m.role == "assistant"]
    answer = "".join(
        getattr(p, "text_content", "") or "" for m in replies for p in m.parts
    )
    has_source = any(
        p.__class__.__name__ == "SourceDocumentPartDto" for m in replies for p in m.parts
    )
    check("chat answered", bool(answer) and not answer.startswith("Error"), answer[:160].replace("\n", " "))
    check("chat cited the document", has_source)

    # 4. Generation jobs
    print("4. Generation (worker)")
    quizzes = QuizService(queue_service=queue)
    quiz = quizzes.create_quiz(project_id=project.id, name="Generated Quiz")
    quizzes.queue_generation(quiz_id=quiz.id, project_id=project.id, topic=TOPIC, count=5, user_id=user.id)
    groups = FlashcardGroupService(queue_service=queue)
    group = groups.create_flashcard_group(project_id=project.id, name="Generated Flashcards")
    groups.queue_generation(group_id=group.id, project_id=project.id, topic=TOPIC, count=5, user_id=user.id)
    notes = NoteService(queue_service=queue)
    note = notes.create_note(project_id=project.id, title="Generated Note", content="")
    notes.queue_generation(note_id=note.id, project_id=project.id, topic=TOPIC, user_id=user.id)
    maps = MindMapService(queue_service=queue)
    mind_map = maps.create_mind_map(user_id=user.id, project_id=project.id, title="Generated Mind Map")
    maps.queue_generation(user_id=user.id, project_id=project.id, mind_map_id=mind_map.id, topic=TOPIC)

    qs, secs = wait_for(lambda: db_get(lambda db: db.query(QuizQuestion).filter_by(quiz_id=quiz.id).all()))
    check("quiz", bool(qs), f"{len(qs or [])} questions in {secs:.0f}s")
    cards, secs = wait_for(lambda: db_get(lambda db: db.query(Flashcard).filter_by(group_id=group.id).all()))
    check("flashcards", bool(cards), f"{len(cards or [])} cards in {secs:.0f}s")
    saved_note, secs = wait_for(lambda: db_get(lambda db: (n := db.get(Note, note.id)) and n.content and n))
    check("note", bool(saved_note), f"{len(saved_note.content) if saved_note else 0} chars in {secs:.0f}s")
    saved_map, secs = wait_for(
        lambda: db_get(lambda db: (m := db.get(MindMap, mind_map.id)) and m.map_data.get("nodes") and m)
    )
    check("mind map", bool(saved_map), f"{len(saved_map.map_data['nodes']) if saved_map else 0} nodes in {secs:.0f}s")


async def run_fbise() -> None:
    """The judging-demo flow for Physics XI."""
    queue = QueueService()
    search = SearchService(
        database_url=settings.database_url,
        azure_openai_embedding_deployment="",
        azure_openai_endpoint="",
        azure_openai_api_version="",
    )
    UserService().get_or_create_user_from_token(
        user_id=TEST_USER, email="e2e-test@local.test", name="E2E Test"
    )

    print("5. FBISE onboarding")
    result = ProfileService().complete_onboarding(
        user_id=TEST_USER, grade=11, group_code="PRE_MED", explanation_language="ur-Latn"
    )
    names = [p.name for p in result.projects]
    check("subject workspaces", names == ["Physics XI", "Chemistry XI", "Biology XI"], ", ".join(names))
    physics = result.projects[0]

    UserService().get_or_create_user_from_token(user_id=OLD_LOGIN, email="e2e-resignup@local.test")
    try:
        again = UserService().get_or_create_user_from_token(user_id=NEW_LOGIN, email="e2e-resignup@local.test")
        old_email = db_get(lambda db: db.get(User, OLD_LOGIN).email)
        check(
            "same email signs up again after its login was deleted",
            again.id == NEW_LOGIN and again.email == "e2e-resignup@local.test" and old_email is None,
            f"new account {again.id}, old account email now {old_email}",
        )
    except Exception as e:
        check("same email signs up again after its login was deleted", False, f"{type(e).__name__}: {e}"[:200])

    print("6. Syllabus map")
    tree = CurriculumService().get_tree(physics.grade_subject_id, TEST_USER)
    slo_count = sum(d.slo_count for d in tree.domains)
    check("Physics XI SLOs", slo_count >= 190 and len(tree.domains) == 7, f"{slo_count} SLOs, {len(tree.domains)} domains")

    print("6b. FSc Part 1: every group and subject")
    UserService().get_or_create_user_from_token(user_id=ICS_USER, email="e2e-ics@local.test", name="E2E ICS")
    ics = ProfileService().complete_onboarding(
        user_id=ICS_USER, grade=11, group_code="ICS", explanation_language="en"
    )
    ics_names = [p.name for p in ics.projects]
    check("ICS workspaces", ics_names == ["Physics XI", "Mathematics XI", "Computer Science XI"], ", ".join(ics_names))
    expected = {"Chemistry XI": (329, 7), "Biology XI": (246, 9), "Mathematics XI": (79, 3), "Computer Science XI": (22, 8)}
    for project in [*result.projects, *ics.projects]:
        if project.name not in expected:
            continue
        want_slos, want_domains = expected.pop(project.name)
        subject_tree = CurriculumService().get_tree(project.grade_subject_id, TEST_USER)
        count = sum(d.slo_count for d in subject_tree.domains)
        check(f"{project.name} syllabus map", count == want_slos and len(subject_tree.domains) == want_domains, f"{count} SLOs, {len(subject_tree.domains)} domains")

    print("7. FBISE tutor (Roman Urdu)")
    chat_svc = ChatService(search_service=search, queue_service=queue)
    chat = chat_svc.create_chat(project_id=physics.id, user_id=TEST_USER, title="E2E tutor")
    async for _ in chat_svc.stream_chat_events(
        chat.id, TEST_USER, [{"type": "text", "text": "projectile ki range kaise nikalte hain?"}]
    ):
        pass
    detail = chat_svc.get_chat(chat_id=chat.id, user_id=TEST_USER, include_messages=True)
    answer = "".join(
        getattr(p, "text_content", "") or ""
        for m in detail.messages
        if m.role == "assistant"
        for p in m.parts
    )
    check("tutor answered", bool(answer) and not answer.startswith("Error"), answer[:160].replace("\n", " "))
    check("tutor cited SLO P-11-B-05", "P-11-B-05" in answer)
    check("tutor wrote a formula", "$" in answer)

    # Web search must never stand in for the syllabus: a syllabus question is
    # answered from the SLOs and the bank, not from whatever the web says.
    from edu_ai.tools.web import api_key as tavily_key

    searched = [
        part
        for m in detail.messages
        for part in (m.parts or [])
        if getattr(part, "tool_name", None) == "search_web"
    ]
    check(
        "web search stays out of syllabus answers",
        not searched,
        f"web search configured: {bool(tavily_key())}; called {len(searched)} time(s)",
    )

    # ... and it does step in for a board question the syllabus cannot answer
    if tavily_key():
        web_chat = chat_svc.create_chat(
            project_id=physics.id, user_id=TEST_USER, title="E2E web search"
        )
        start = time.time()
        async for _ in chat_svc.stream_chat_events(
            web_chat.id,
            TEST_USER,
            [{"type": "text", "text": "FBISE ka HSSC-I date sheet kab aata hai? website par dekho"}],
        ):
            pass
        web_detail = chat_svc.get_chat(
            chat_id=web_chat.id, user_id=TEST_USER, include_messages=True
        )
        calls = [
            part
            for m in web_detail.messages
            for part in (m.parts or [])
            if getattr(part, "tool_name", None) == "search_web"
        ]
        web_answer = "".join(
            getattr(part, "text_content", "") or ""
            for m in web_detail.messages
            if m.role == "assistant"
            for part in (m.parts or [])
        )
        check(
            "web search used for a board question, and the source named",
            len(calls) == 1 and "fbise.edu.pk" in web_answer.lower(),
            f"{len(calls)} call(s) in {time.time() - start:.0f}s: "
            + " ".join(web_answer[:150].split()),
        )

    cs_project = next(p for p in ics.projects if p.name == "Computer Science XI")
    cs_chat = chat_svc.create_chat(project_id=cs_project.id, user_id=ICS_USER, title="E2E CS tutor")
    async for _ in chat_svc.stream_chat_events(
        cs_chat.id, ICS_USER, [{"type": "text", "text": "How do I find the sum of all numbers in a list in Python? Show a short program."}]
    ):
        pass
    cs_detail = chat_svc.get_chat(chat_id=cs_chat.id, user_id=ICS_USER, include_messages=True)
    cs_answer = "".join(
        getattr(p, "text_content", "") or "" for m in cs_detail.messages if m.role == "assistant" for p in m.parts
    )
    check("Computer Science tutor cites a CS SLO", "CS-11-" in cs_answer, cs_answer[:120].replace("\n", " "))
    check("Computer Science tutor shows code in a code block", "```" in cs_answer)

    print("8. SLO practice and mastery")
    quizzes = QuizService(queue_service=queue)
    quiz = quizzes.create_quiz(project_id=physics.id, name="SLO quiz")
    quizzes.queue_generation(
        quiz_id=quiz.id, project_id=physics.id, count=5, user_id=TEST_USER, slo_code="P-11-B-05"
    )
    qs, secs = wait_for(lambda: db_get(lambda db: db.query(QuizQuestion).filter_by(quiz_id=quiz.id).all()))
    tagged = [q for q in qs or [] if q.slo_code == "P-11-B-05"]
    check("SLO quiz", bool(qs) and len(tagged) == len(qs), f"{len(qs or [])} questions, {len(tagged)} tagged, in {secs:.0f}s")
    if qs:
        PracticeService().create_practice_records_batch(
            TEST_USER,
            physics.id,
            [
                {
                    "item_type": "quiz",
                    "item_id": q.id,
                    "topic": q.question_text[:100],
                    "user_answer": q.correct_option,
                    "correct_answer": q.correct_option,
                    "was_correct": True,
                }
                for q in qs
            ],
        )
        slo = CurriculumService().get_slo("P-11-B-05", TEST_USER, physics.grade_subject_id)
        check("mastery updated", slo.mastery is not None and slo.attempts == len(qs), f"{slo.attempts} answers, mastery {slo.mastery}")

    print("8b. Quiz inside the chat")
    chat2 = chat_svc.create_chat(project_id=physics.id, user_id=TEST_USER, title="E2E chat quiz")
    start = time.time()
    tool_part_ids: dict[str, set] = {}
    async for event in chat_svc.stream_chat_events(
        chat2.id, TEST_USER, [{"type": "text", "text": "vector product ke 5 MCQs do, main attempt karna chahta hoon"}]
    ):
        part = event.part if isinstance(event.part, dict) else (event.part.model_dump() if event.part else None)
        if part and part.get("type") == "tool_call":
            tool_part_ids.setdefault(part["tool_call_id"], set()).add(part.get("id"))
    detail = chat_svc.get_chat(chat_id=chat2.id, user_id=TEST_USER, include_messages=True)
    check(
        "each tool card streamed under one ID (no duplicate cards)",
        bool(tool_part_ids) and all(len(ids) == 1 and None not in ids for ids in tool_part_ids.values()),
        f"{len(tool_part_ids)} tool calls",
    )
    last_parts = detail.messages[-1].parts if detail.messages else []
    check(
        "turn ended on the quiz card (no extra model call)",
        bool(last_parts) and getattr(last_parts[-1], "tool_name", None) == "practice_quiz",
        ", ".join(getattr(p, "tool_name", None) or p.type for p in last_parts),
    )
    quiz_ids = [
        json.loads(p.tool_output).get("quiz_id") if isinstance(p.tool_output, str) else (p.tool_output or {}).get("quiz_id")
        for m in detail.messages
        for p in m.parts
        if getattr(p, "tool_name", None) == "practice_quiz" and p.tool_output
    ]
    chat_quiz = next((q for q in quiz_ids if q), None)
    check("tutor started a quiz card", bool(chat_quiz), f"in {time.time() - start:.0f}s")
    if chat_quiz:
        qs = db_get(lambda db: db.query(QuizQuestion).filter_by(quiz_id=chat_quiz).all())
        attempt = AttemptService().submit_quiz(
            TEST_USER, physics.id, chat_quiz, {q.id: q.correct_option for q in qs}
        )
        check("chat quiz answered and saved", attempt.max_score > 0 and attempt.score == attempt.max_score, f"{attempt.score}/{attempt.max_score}, SLO {qs[0].slo_code if qs else None}")
        retry = AttemptService().submit_quiz(TEST_USER, physics.id, chat_quiz, {qs[0].id: "a"} if qs else {})
        latest, history = AttemptService().latest_quiz_attempt(TEST_USER, physics.id, chat_quiz)
        check(
            "retry saved as attempt 2, first kept",
            attempt.number == 1 and retry.number == 2 and latest is not None and latest.id == retry.id
            and [h.number for h in history] == [1, 2] and history[0].score == attempt.score,
            " · ".join(f"#{h.number} {h.score:g}/{h.max_score:g}" for h in history),
        )
        listed = [h for h in AttemptService().history(TEST_USER, physics.id) if h.ref_id == chat_quiz]
        check("practice history lists both attempts", [h.number for h in listed] == [2, 1], ", ".join(f"{h.title} - Attempt {h.number}" for h in listed))

        start = time.time()
        async for _ in chat_svc.stream_chat_events(
            chat2.id, TEST_USER, [{"type": "text", "text": "maine quiz kar liya, ab vector product ka ek real life example do"}]
        ):
            pass
        detail = chat_svc.get_chat(chat_id=chat2.id, user_id=TEST_USER, include_messages=True)
        last = detail.messages[-1]
        reply = "".join(getattr(p, "text_content", "") or "" for p in last.parts) if last.role == "assistant" else ""
        check("follow-up after a card answered", bool(reply) and not reply.startswith("Error"), f"in {time.time() - start:.0f}s: " + reply[:100].replace("\n", " "))

        start = time.time()
        async for _ in chat_svc.stream_chat_events(
            chat2.id, TEST_USER, [{"type": "text", "text": "ek aur quiz do, 3 MCQs dot product par"}]
        ):
            pass
        detail = chat_svc.get_chat(chat_id=chat2.id, user_id=TEST_USER, include_messages=True)
        last = detail.messages[-1]
        again = [p for p in last.parts if last.role == "assistant" and getattr(p, "tool_name", None) == "practice_quiz"]
        check("second quiz in the same chat is a new card", bool(again) and again[0].tool_state == "output-available", f"in {time.time() - start:.0f}s")

    print("8c. Flashcards inside the chat")
    start = time.time()
    group, cards = await FlashcardGroupService(queue_service=queue).create_practice_flashcards(
        project_id=physics.id, topic="dot product", count=4, search_service=search
    )
    check("instant flashcards", cards > 0 and bool(group.slo_code), f"{cards} cards for {group.slo_code} in {time.time() - start:.0f}s")
    card_ids = db_get(lambda db: [c.id for c in db.query(Flashcard).filter_by(group_id=group.id)])
    fc_attempt = AttemptService().submit_flashcards(TEST_USER, physics.id, group.id, {cid: True for cid in card_ids})
    check("flashcards studied and saved", fc_attempt.total == len(card_ids) > 0, f"{fc_attempt.known}/{fc_attempt.total} known")

    print("8d. Mind maps from the syllabus")
    maps = MindMapService(queue_service=queue)
    domain_mm = await maps.create_practice_mind_map(TEST_USER, physics.id, "Mechanics", search)
    domain_codes = {n["data"].get("slo_code") for n in domain_mm.map_data["nodes"]} - {None}
    check("domain mind map", len(domain_codes) >= 40, f"{len(domain_mm.map_data['nodes'])} nodes, {len(domain_codes)} SLOs")
    start = time.time()
    topic_mm = await maps.create_practice_mind_map(TEST_USER, physics.id, "vector product", search)
    topic_codes = {n["data"].get("slo_code") for n in topic_mm.map_data["nodes"]} - {None}
    check("topic mind map", "P-11-B-02" in topic_codes, f"'{topic_mm.title}', {len(topic_mm.map_data['nodes'])} nodes in {time.time() - start:.0f}s")
    maps.delete_mind_map(topic_mm.id, physics.id, TEST_USER)
    check("mind map deleted", all(m.id != topic_mm.id for m in maps.list_mind_maps(physics.id, TEST_USER)))

    print("8e. Questions before practice (asked only when needed)")

    async def say(chat_id: str, text: str):
        """Send a chat message; return the tutor's last message parts and the seconds taken."""
        start = time.time()
        async for _ in chat_svc.stream_chat_events(chat_id, TEST_USER, [{"type": "text", "text": text}]):
            pass
        messages = chat_svc.get_chat(chat_id=chat_id, user_id=TEST_USER, include_messages=True).messages
        last = messages[-1]
        return (last.parts if last.role == "assistant" else []), time.time() - start

    def tool_part(parts, name: str):
        return next((p for p in parts if getattr(p, "tool_name", None) == name and p.tool_output), None)

    def output(part) -> dict:
        return json.loads(part.tool_output) if isinstance(part.tool_output, str) else (part.tool_output or {})

    def answer_card(setup: dict, wants: dict) -> str:
        """Answer the card like the web app does, picking options that contain a wanted word."""
        lines = []
        for question in setup["questions"]:
            pick = next(
                (o for o in question["options"] for word in wants.values() if word.lower() in o.lower()),
                (question["recommended"] or question["options"][:1])[0],
            )
            lines.append(f"- {question['question']} {pick}")
        name = {"quiz": "Quiz", "mind_map": "Mind map", "flashcards": "Flashcards", "paper": "Paper"}[setup["kind"]]
        return f"{name} setup ({setup['topic']}):\n" + "\n".join(lines) + "\nPlease make it now."

    chat3 = chat_svc.create_chat(project_id=physics.id, user_id=TEST_USER, title="E2E ask first")
    parts, secs = await say(chat3.id, "mujhe vectors par quiz chahiye")
    ask = tool_part(parts, "ask_practice_questions")
    setup = output(ask) if ask else {}
    questions = setup.get("questions", [])
    first_options = questions[0]["options"] if questions else []
    check(
        "vague request: tutor asked 3-5 questions first",
        3 <= len(questions) <= 5 and not tool_part(parts, "practice_quiz"),
        f"in {secs:.0f}s: " + " | ".join(q["question"] for q in questions),
    )
    check(
        "the syllabus question lists real SLOs",
        any(o.startswith("P-11-B-") for o in first_options),
        ", ".join(o.split(":")[0] for o in first_options),
    )
    if questions:
        reply = answer_card(setup, {"slo": "P-11-B-02", "style": "Numerical"})
        parts, secs = await say(chat3.id, reply)
        made = tool_part(parts, "practice_quiz")
        quiz_id = output(made).get("quiz_id") if made else None
        qs = db_get(lambda db: db.query(QuizQuestion).filter_by(quiz_id=quiz_id).all()) if quiz_id else []
        numerical = sum(practice_options.is_numerical(q.question_text) for q in qs)
        check(
            "answers turned into a matching quiz",
            bool(qs) and (made.tool_input or {}).get("style", "").startswith("numer") and numerical >= len(qs) // 2 + 1,
            f"in {secs:.0f}s, settings {made.tool_input if made else None}, {numerical}/{len(qs)} numerical",
        )

    chat4 = chat_svc.create_chat(project_id=physics.id, user_id=TEST_USER, title="E2E specific")
    parts, secs = await say(chat4.id, "cross product ke 5 numericals do, board level")
    made = tool_part(parts, "practice_quiz")
    check(
        "specific request: quiz made without asking",
        bool(made) and not tool_part(parts, "ask_practice_questions"),
        f"in {secs:.0f}s, settings {made.tool_input if made else None}",
    )

    chat5 = chat_svc.create_chat(project_id=physics.id, user_id=TEST_USER, title="E2E mind map ask")
    parts, secs = await say(chat5.id, "vectors ka mind map banao")
    ask = tool_part(parts, "ask_practice_questions")
    setup = output(ask) if ask else {}
    check(
        "vague mind map: tutor asked first",
        setup.get("kind") == "mind_map" and 3 <= len(setup.get("questions", [])) <= 5,
        f"in {secs:.0f}s: " + " | ".join(q["question"] for q in setup.get("questions", [])),
    )
    if setup:
        reply = answer_card(setup, {"slo": "P-11-B-02", "detail": "Detail", "include": "Formula"})
        parts, secs = await say(chat5.id, reply)
        made = tool_part(parts, "practice_mind_map")
        check(
            "answers turned into a mind map",
            bool(made) and bool(output(made).get("mind_map_id")),
            f"in {secs:.0f}s, settings {made.tool_input if made else None}",
        )

    print("9. Written answer (SRQ) marking")
    srq = SrqService()
    start = time.time()
    question = await srq.generate(physics.id, TEST_USER, "P-11-B-05")
    check("SRQ generated", question.marks >= 2, f"{question.marks} marks in {time.time() - start:.0f}s: {question.question[:100]}")
    start = time.time()
    attempt = await srq.mark(
        physics.id,
        question.id,
        TEST_USER,
        "Range R = v^2 sin 2θ / g. Horizontal velocity stays constant and acceleration is g downwards.",
    )
    check(
        "SRQ marked",
        bool(attempt.points) and 0 <= attempt.awarded_marks <= attempt.max_marks,
        f"{attempt.awarded_marks}/{attempt.max_marks} in {time.time() - start:.0f}s",
    )

    print("9b. Practice paper")
    papers = PaperService()
    start = time.time()
    paper = await papers.create(physics.id, TEST_USER, length="mini", topic="Mechanics")
    items = [item for section in paper.sections for item in section.items]
    check("paper made", len(items) == 10 and paper.total_marks > 8, f"{len(items)} questions, {paper.total_marks:g} marks in {time.time() - start:.0f}s")
    stored = db_get(lambda db: db.get(PracticePaper, paper.id).sections)
    answers = {i["id"]: i["correct_option"] for s in stored for i in s["items"] if i["type"] == "mcq"}
    first_written = next(i for i in items if i.type != "mcq")
    answers[first_written.id] = "Using the formula for this case with the given values, the answer follows with SI units."
    start = time.time()
    marked = await papers.submit(paper.id, TEST_USER, answers)
    result = marked.result
    check(
        "paper marked",
        result is not None and result.sections[0].score == result.sections[0].max_score,
        f"{result.score:g}/{result.max_score:g} ({result.grade}) in {time.time() - start:.0f}s" if result else "no result",
    )

    # FBISE's new pattern at half length, built here (no queue) as the worker builds it
    start = time.time()
    half = await papers.create(physics.id, TEST_USER, length="half")
    by_section = {s.id: list(s.items) for s in half.sections}
    a, b, c = by_section.get("A", []), by_section.get("B", []), by_section.get("C", [])
    sets = {i.group for i in a if i.group}
    pairs_b = {i.choice_group for i in b}
    check(
        "half board paper set (stimulus sets, (a) OR (b) choices)",
        half.status == "ready" and len(a) == 40 and len(sets) == 3
        and all(i.stimulus for i in a if i.group) and len(b) == 8 and len(pairs_b) == 4
        and len(c) == 2 and 38 <= half.total_marks <= 42,
        f"{half.status}: A {len(a)} MCQs ({len(sets)} stimulus sets), B {len(b)} in {len(pairs_b)} pairs, "
        f"C {len(c)}, {half.total_marks:g} marks in {time.time() - start:.0f}s",
    )
    if half.status == "ready" and b:
        stored = db_get(lambda db: db.get(PracticePaper, half.id).sections)
        answers = {i["id"]: i["correct_option"] for s in stored for i in s["items"] if i["type"] == "mcq"}
        # Both questions of pair B1 answered: only one may count
        first_pair = [i for i in b if i.choice_group == b[0].choice_group]
        for item in first_pair:
            answers[item.id] = "Using the relevant formula with the given values: substitution and the answer with SI units."
        start = time.time()
        marked = await papers.submit(half.id, TEST_USER, answers)
        result = marked.result
        section_b = next((s for s in result.sections if s.id == "B"), None) if result else None
        check(
            "half paper marked, a choice pair counted once",
            result is not None and result.sections[0].score == result.sections[0].max_score
            and section_b is not None and section_b.score <= max(i.marks for i in first_pair)
            and result.max_score == half.total_marks,
            f"{result.score:g}/{result.max_score:g}, Section B {section_b.score:g}/{section_b.max_score:g} in "
            f"{time.time() - start:.0f}s" if result and section_b else "no result",
        )

    print("10. Progress and predicted grade")
    progress = ProgressService().get_progress(TEST_USER)
    physics_progress = next((s for s in progress.subjects if s.project_id == physics.id), None)
    predicted = physics_progress.predicted if physics_progress else None
    check(
        "predicted grade",
        predicted is not None,
        f"{predicted.grade} ({predicted.percent}%, {predicted.confidence} confidence)" if predicted else "none",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf", type=Path, help="Test with this PDF instead of the sample document")
    parser.add_argument("--keep", action="store_true", help="Keep the test data afterwards")
    parser.add_argument("--cleanup", action="store_true", help="Only delete leftover test data")
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
        return

    try:
        asyncio.run(run(args.pdf))
        asyncio.run(run_fbise())
    finally:
        if not args.keep:
            cleanup()

    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
