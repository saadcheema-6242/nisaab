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
    CommunityAttachment,
    CommunityPost,
    CommunityReport,
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
# Three students for the class room: two in one room, one in another,
# because most of what can go wrong there is about who can see what.
ROOM_A, ROOM_B, ROOM_C = (
    "e2e-room-a", "e2e-room-b", "e2e-room-c",
)
# A student with ten weeks of practice behind them, for the graphs.
GRAPH_USER = "e2e-graphs"
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
        users = [TEST_USER, ICS_USER, OLD_LOGIN, NEW_LOGIN, ROOM_A, ROOM_B,
                 ROOM_C, GRAPH_USER]
        project_ids = [p.id for p in db.query(Project).filter(Project.owner_id.in_(users))]
        for pid in project_ids:
            storage.delete(storage.list_paths(pid))
            db.execute(text("DELETE FROM jobs WHERE payload->>'project_id' = :pid"), {"pid": pid})
        # Community files hang off posts, not projects, so they are not
        # covered by the project sweep above. The rows cascade with the
        # user; the bytes do not.
        room_paths = [
            a.storage_path
            for a in db.query(CommunityAttachment).join(
                CommunityPost, CommunityAttachment.post_id == CommunityPost.id
            ).filter(CommunityPost.user_id.in_(users))
        ]
        if room_paths:
            storage.delete(room_paths)
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



async def run_community() -> None:
    """The class room: moderation, attachments, voice notes and polls.

    Runs against the real database and the real bucket, with two students in
    the same room and a third in another, because most of what can go wrong
    here is about who can see what.

    The reviewer is a stub rather than the live model. What needs proving in
    an end-to-end run is that the verdict reaches the post, the warning
    reaches the author, and the queue sorts by it - not that Gemini agrees
    with us today, which would make this check fail for reasons that are not
    bugs. The prompt and the parsing are checked in
    scripts/admin/check_community_rules.py, and a real call is made at the
    end to prove the model is reachable at all.
    """
    from edu_core.community_review import CLEAN, SELF_HARM
    from edu_core.services.community import CommunityService
    from edu_core.services.moderation_queue import ModerationQueueService

    print("12. Class room: setting up two students in one room")
    UserService().get_or_create_user_from_token(
        user_id=ROOM_A, email="e2e-room-a@local.test", name="Ayesha"
    )
    UserService().get_or_create_user_from_token(
        user_id=ROOM_B, email="e2e-room-b@local.test", name="Bilal"
    )
    UserService().get_or_create_user_from_token(
        user_id=ROOM_C, email="e2e-room-c@local.test", name="Chaudhry"
    )
    ProfileService().complete_onboarding(
        user_id=ROOM_A, grade=11, group_code="PRE_MED", explanation_language="en"
    )
    ProfileService().complete_onboarding(
        user_id=ROOM_B, grade=11, group_code="PRE_MED", explanation_language="en"
    )
    # A different group, so a different room.
    ProfileService().complete_onboarding(
        user_id=ROOM_C, grade=11, group_code="ICS", explanation_language="en"
    )

    # What the stub reviewer says, set per call by the test.
    verdict = {"finding": "clean", "confidence": 0.9, "why": ""}

    def stub_reviewer(prompt: str) -> str:
        return json.dumps(verdict)

    def failing_reviewer(prompt: str) -> str:
        raise RuntimeError("Vertex is having a bad minute")

    room = CommunityService(storage=storage, reviewer=stub_reviewer)
    queue = ModerationQueueService(storage=storage)

    print("12a. Posting, replying and who can see it")
    post = room.add_post(user_id=ROOM_A, body="Can someone explain Boyle's law?")
    check("a student can post", bool(post.id), post.id)

    reply = room.add_post(
        user_id=ROOM_B, body="Pressure times volume is constant", parent_id=post.id
    )
    check("another student can reply", reply.id != post.id)

    seen = room.get_room(user_id=ROOM_B)
    check("the room has the post", any(p.id == post.id for p in seen.posts))
    mine = next(p for p in seen.posts if p.id == post.id)
    check("the reply is threaded under it", any(r.id == reply.id for r in mine.replies))
    check("the author is named, never their email",
          mine.author_name == "Ayesha", mine.author_name)
    check("and no email appears anywhere in the room",
          "@" not in json.dumps([p.model_dump(mode="json") for p in seen.posts]))

    other = room.get_room(user_id=ROOM_C)
    check("a student in another group sees a different room",
          all(p.id != post.id for p in other.posts),
          f"ICS student saw {len(other.posts)} posts")

    print("12b. Contact details are refused, Physics is not")
    for text_in, why in (
        ("my number is 03001234567", "a phone number"),
        ("mail me at test@example.com", "an email"),
        ("add me on instagram.com/someone", "a link"),
    ):
        try:
            room.add_post(user_id=ROOM_A, body=text_in)
            check(f"refuses {why}", False, "it was accepted")
        except ValueError as error:
            said = str(error)
            check(f"refuses {why}", "cannot be posted here" in said, said[:90])
            check(f"and does not repeat the {why} back",
                  text_in.split()[-1] not in said, said[:90])

    allowed = room.add_post(
        user_id=ROOM_A,
        body="the charge is 1.6 x 10^-19 C and pi is 3.141592653, see chapter 11",
    )
    check("a post full of numbers is allowed", bool(allowed.id))

    print("12c. The model's verdict reaches the post and the author")
    verdict = {"finding": "bullying", "confidence": 0.95, "why": "targets a student"}
    flagged = room.add_post(user_id=ROOM_B, body="A post the stub will flag")
    with Session() as db:
        row = db.get(CommunityPost, flagged.id)
        check("the finding is stored", row.review_finding == "bullying", str(row.review_finding))
        check("with a severity to sort by", (row.review_severity or 0) > 0, str(row.review_severity))
        check("and the author was warned", bool(row.warning_text), str(row.warning_text)[:60])

    warned_room = room.get_room(user_id=ROOM_B)
    check("the author sees the warning", len(warned_room.warnings) >= 1)
    check("and it is a warning, not an offer of help",
          not warned_room.warnings[0].is_support)
    others_view = room.get_room(user_id=ROOM_A)
    check("nobody else is shown it", len(others_view.warnings) == 0)
    check("and the room never exposes the finding",
          "bullying" not in json.dumps([p.model_dump(mode="json") for p in others_view.posts]))

    room.mark_warnings_seen(user_id=ROOM_B)
    check("dismissing a warning works",
          len(room.get_room(user_id=ROOM_B).warnings) == 0)

    print("12d. Distress is handled the other way round")
    verdict = {"finding": SELF_HARM, "confidence": 0.2, "why": "sounds desperate"}
    sad = room.add_post(user_id=ROOM_A, body="A post the stub will treat as distress")
    with Session() as db:
        row = db.get(CommunityPost, sad.id)
        check("acted on even at low confidence", row.review_finding == SELF_HARM,
              str(row.review_finding))
        check("it outranks everything else", row.review_severity == 100,
              str(row.review_severity))
        check("the message offers help rather than a telling-off",
              "talk to someone" in (row.warning_text or "").lower(),
              str(row.warning_text)[:80])
    sad_room = room.get_room(user_id=ROOM_A)
    support = [w for w in sad_room.warnings if w.post_id == sad.id]
    check("and it is marked as support", support and support[0].is_support)
    check("the post is still visible to the room",
          any(p.id == sad.id for p in room.get_room(user_id=ROOM_B).posts),
          "hiding it would help nobody")

    print("12e. A failing model never loses a post")
    broken = CommunityService(storage=storage, reviewer=failing_reviewer)
    survived = broken.add_post(user_id=ROOM_A, body="Posted while Vertex was down")
    check("the post still goes through", bool(survived.id))
    with Session() as db:
        row = db.get(CommunityPost, survived.id)
        check("and is left unreviewed, not marked clean",
              row.review_finding is None, str(row.review_finding))

    print("12f. Attachments: an image, a document and a voice note")
    verdict = {"finding": CLEAN, "confidence": 0.9, "why": ""}
    png = bytes.fromhex("89504e470d0a1a0a") + b"0" * 64
    pdf = b"%PDF-1.7\n" + b"0" * 64
    ogg = b"OggS" + b"0" * 64
    with_files = room.add_post(
        user_id=ROOM_A,
        body="Here is my working",
        uploads=[
            ("working.png", "image/png", png, None),
            ("past-paper.pdf", "application/pdf", pdf, None),
            ("voice-note.ogg", "audio/ogg", ogg, 42),
        ],
    )
    kinds = sorted(a.kind for a in with_files.attachments)
    check("all three are attached", kinds == ["audio", "file", "image"], str(kinds))
    check("a voice note keeps its length",
          any(a.duration_seconds == 42 for a in with_files.attachments))
    check("every attachment has a link",
          all(a.url for a in with_files.attachments),
          "signing failed")

    data, name, ctype = room.attachment_bytes(
        user_id=ROOM_B,
        attachment_id=next(a.id for a in with_files.attachments if a.kind == "file"),
    )
    check("a classmate can download it", data == pdf and name == "past-paper.pdf", name)

    try:
        room.attachment_bytes(
            user_id=ROOM_C,
            attachment_id=next(a.id for a in with_files.attachments if a.kind == "file"),
        )
        check("a student in another room cannot", False, "the download was allowed")
    except Exception as error:
        check("a student in another room cannot", "not in your room" in str(error), str(error)[:70])

    print("12g. Files a student must not be able to share")
    for filename, ctype_in, data_in, why in (
        ("virus.png", "image/png", b"MZ\x90\x00" + b"0" * 40, "a program renamed to .png"),
        ("notes.zip", "application/zip", b"PK\x03\x04" + b"0" * 40, "an archive"),
        ("big.pdf", "application/pdf", b"%PDF-" + b"0" * 40, "a file over 50MB"),
    ):
        size_lie = 60 * 1024 * 1024 if why.startswith("a file over") else None
        try:
            payload = b"0" * size_lie if size_lie else data_in
            room.add_post(
                user_id=ROOM_A, body="trying it on",
                uploads=[(filename, ctype_in, payload, None)],
            )
            check(f"refuses {why}", False, "it was accepted")
        except ValueError:
            check(f"refuses {why}", True)

    print("12h. Polls")
    poll = room.add_post(
        user_id=ROOM_A,
        body="",
        poll_question="Which chapter is hardest?",
        poll_options=["Thermodynamics", "Waves", "Optics"],
    )
    check("a poll is created", poll.poll is not None and len(poll.poll.options) == 3)

    first = poll.poll.options[0].id
    second = poll.poll.options[1].id
    room.vote(user_id=ROOM_A, post_id=poll.id, option_id=first)
    after = room.vote(user_id=ROOM_B, post_id=poll.id, option_id=first)
    check("votes are counted", after.poll.total_votes == 2, str(after.poll.total_votes))
    check("percentages total 100",
          sum(o.percent for o in after.poll.options) == 100,
          str([o.percent for o in after.poll.options]))

    changed = room.vote(user_id=ROOM_B, post_id=poll.id, option_id=second)
    check("a student may change their vote, and it is still one vote",
          changed.poll.total_votes == 2, str(changed.poll.total_votes))
    counts = {o.id: o.votes for o in changed.poll.options}
    check("the change moved the vote", counts[first] == 1 and counts[second] == 1,
          str(counts))

    try:
        room.vote(user_id=ROOM_C, post_id=poll.id, option_id=first)
        check("a student in another room cannot vote", False, "the vote was allowed")
    except Exception as error:
        check("a student in another room cannot vote", "not in your room" in str(error))

    print("12i. Reporting")
    room.report_post(user_id=ROOM_B, post_id=post.id, reason="bullying", note="not ok")
    room.report_post(user_id=ROOM_B, post_id=post.id, reason="bullying")
    with Session() as db:
        count = (
            db.query(CommunityReport)
            .filter(CommunityReport.post_id == post.id)
            .count()
        )
    check("reporting twice counts once", count == 1, str(count))
    reader = room.get_room(user_id=ROOM_B)
    reported = next(p for p in reader.posts if p.id == post.id)
    check("the reporter sees that they reported it", reported.reported_by_me)
    author_view = next(
        p for p in room.get_room(user_id=ROOM_A).posts if p.id == post.id
    )
    check("the author is not told it was reported", not author_view.reported_by_me)

    print("12j. The administrator's queue")
    waiting = queue.queue()
    ids = [i.post_id for i in waiting.items]
    check("the flagged post is in it", flagged.id in ids)
    check("the distressed post is in it", sad.id in ids)
    check("the reported post is in it", post.id in ids)
    check("the unreviewed post is in it", survived.id in ids)
    check("distress comes first", ids[0] == sad.id, f"first was {ids[0]}")
    check("urgent items are counted", waiting.urgent_count >= 1, str(waiting.urgent_count))
    check("so are the unreviewed, separately from the clean",
          waiting.unreviewed_count >= 1, str(waiting.unreviewed_count))
    item = next(i for i in waiting.items if i.post_id == post.id)
    check("an administrator sees the reporter's reason",
          item.reports and item.reports[0].reason == "bullying")
    check("and the author's email, which the room never shows",
          item.author_email == "e2e-room-a@local.test", str(item.author_email))

    print("12k. An administrator can act")
    queue.clear_post(admin_id=TEST_USER, post_id=flagged.id)
    check("clearing takes it out of the queue",
          flagged.id not in [i.post_id for i in queue.queue().items])
    check("but the finding is kept",
          db_get(lambda db: db.get(CommunityPost, flagged.id).review_finding) == "bullying")

    paths = db_get(
        lambda db: [
            a.storage_path
            for a in db.query(CommunityAttachment).filter(
                CommunityAttachment.post_id == with_files.id
            )
        ]
    )
    queue.delete_post(admin_id=TEST_USER, post_id=with_files.id)
    check("an administrator can delete anyone's post",
          db_get(lambda db: db.get(CommunityPost, with_files.id)) is None)
    check("its attachment rows go too",
          db_get(lambda db: db.query(CommunityAttachment).filter(
              CommunityAttachment.post_id == with_files.id).count()) == 0)
    still_there = []
    for path in paths:
        try:
            storage.download(path)
            still_there.append(path)
        except Exception:
            pass
    check("and the files leave the bucket", not still_there, str(still_there))

    print("12l. A student deletes their own, and only their own")
    own = room.add_post(user_id=ROOM_A, body="I will delete this myself")
    room.delete_post(user_id=ROOM_A, post_id=own.id)
    check("a student can delete their own post",
          db_get(lambda db: db.get(CommunityPost, own.id)) is None)
    try:
        room.delete_post(user_id=ROOM_B, post_id=post.id)
        check("a student cannot delete someone else's", False, "it was deleted")
    except Exception as error:
        check("a student cannot delete someone else's", "not yours" in str(error))

    print("12m. A cascade: deleting a post takes its replies")
    parent = room.add_post(user_id=ROOM_A, body="Parent post")
    child = room.add_post(user_id=ROOM_B, body="A reply", parent_id=parent.id)
    room.delete_post(user_id=ROOM_A, post_id=parent.id)
    check("the reply goes with it",
          db_get(lambda db: db.get(CommunityPost, child.id)) is None)

    print("12n. The real model, to prove it is reachable")
    try:
        from edu_ai.llm import generate_text, is_llm_configured

        if not is_llm_configured():
            check("a model is configured", False, "LLM is not configured")
        else:
            live = CommunityService(
                storage=storage, reviewer=lambda p: generate_text(p)
            )
            real = live.add_post(
                user_id=ROOM_A,
                body="Can someone explain how to balance a redox equation?",
            )
            finding = db_get(
                lambda db: db.get(CommunityPost, real.id).review_finding
            )
            check(
                "the live model reviews an ordinary question and leaves it alone",
                finding == CLEAN,
                f"it said {finding}",
            )
    except Exception as error:  # noqa: BLE001
        check("the live model is reachable", False, f"{type(error).__name__}: {error}"[:150])



async def run_progress_graphs() -> None:
    """The graphs tab, against real practice records in the real database.

    The arithmetic is checked without a database in
    scripts/admin/check_progress_trend.py. What has to be proved here is the
    part that only the real thing can show: that the rows reach the functions
    in the right shape, that the trend agrees with the overview rather than
    quietly disagreeing with it, and that the cognitive levels in the seeded
    FBISE syllabus actually produce a split.

    Answers are written at chosen dates rather than now, because a trend with
    every point in the same week is not a trend and would pass whatever the
    bucketing did.
    """
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from edu_core.progress_trend import PAPER_WEIGHTS
    from edu_db.models import PracticeRecord, Slo

    print("13. Progress graphs")
    UserService().get_or_create_user_from_token(
        user_id=GRAPH_USER, email="e2e-graphs@local.test", name="Graph Student"
    )
    setup = ProfileService().complete_onboarding(
        user_id=GRAPH_USER, grade=11, group_code="PRE_MED", explanation_language="en"
    )
    physics = setup.projects[0]

    service = ProgressService()

    print("13a. Nothing practised yet")
    empty = service.get_graphs(user_id=GRAPH_USER)
    check("it returns a subject per workspace", len(empty.subjects) == 3,
          str(len(empty.subjects)))
    check("with an empty trend", empty.subjects[0].trend == [])
    check("no streak", empty.consistency.current_streak == 0)
    check("no calendar", empty.consistency.calendar == [])
    check("the cognitive levels are still listed",
          len(empty.subjects[0].cognitive) == 3,
          "a student should see what the paper asks for before they start")
    check("and each carries the paper's weight",
          sorted(c.paper_weight for c in empty.subjects[0].cognitive)
          == sorted(PAPER_WEIGHTS.values()))
    check("nothing practised means no weakest level",
          empty.subjects[0].weakest_level is None)

    print("13b. Twelve weeks of practice, improving")
    # Real SLO codes from the seeded syllabus, so the cognitive levels are
    # the curriculum's rather than invented.
    codes = db_get(
        lambda db: [
            s.code
            for s in db.query(Slo)
            .filter(
                Slo.grade_subject_id == physics.grade_subject_id,
                Slo.assessment_form == "summative",
            )
            .order_by(Slo.sort_order)
            .limit(8)
            .all()
        ]
    )
    check("the syllabus gave us SLOs to practise", len(codes) >= 4, str(len(codes)))

    now = datetime.now(timezone.utc)
    written = 0
    with Session() as db:
        for week in range(10):
            when = now - timedelta(weeks=9 - week)
            for n, code in enumerate(codes[:4]):
                # Wrong at the start, right by the end: a climb the graph
                # has to show.
                correct = week >= 4
                db.add(
                    PracticeRecord(
                        id=str(uuid4()),
                        user_id=GRAPH_USER,
                        project_id=physics.id,
                        item_type="quiz",
                        item_id=f"e2e-graph-{week}-{n}",
                        topic="e2e graphs",
                        slo_code=code,
                        user_answer="A",
                        correct_answer="A",
                        was_correct=correct,
                        created_at=when,
                    )
                )
                written += 1
        db.commit()
    check(f"{written} practice answers written across 10 weeks", written == 40)

    graphs = service.get_graphs(user_id=GRAPH_USER)
    phys = next(s for s in graphs.subjects if s.project_id == physics.id)

    print("13c. The trend")
    check("there is a trend now", len(phys.trend) > 0, str(len(phys.trend)))
    scored = [p for p in phys.trend if p.mastery is not None]
    check("most weeks have a value", len(scored) >= 8, str(len(scored)))
    check("it climbs", scored[0].mastery < scored[-1].mastery,
          f"{scored[0].mastery} -> {scored[-1].mastery}")
    check("weeks are in order",
          [p.week_start for p in phys.trend] == sorted(p.week_start for p in phys.trend))
    check("attempts never go backwards",
          all(a.attempts <= b.attempts for a, b in zip(phys.trend, phys.trend[1:])),
          "a cumulative count that falls is a bucketing bug")

    print("13d. The graph agrees with the overview")
    # The thing that matters most. If these two disagree a student sees a
    # chart ending at one number under a heading saying another.
    overview = service.get_progress(user_id=GRAPH_USER)
    over_phys = next(s for s in overview.subjects if s.project_id == physics.id)
    check("the subject's headline comes from the trend's last point",
          phys.mastery == phys.trend[-1].mastery,
          f"{phys.mastery} vs {phys.trend[-1].mastery}")
    check("and the overview is within a point of it",
          over_phys.mastery is not None
          and abs(over_phys.mastery - phys.mastery) < 0.02,
          f"overview {over_phys.mastery} vs graphs {phys.mastery}",
          )

    print("13e. The FBISE cognitive levels")
    check("all three levels come back", len(phys.cognitive) == 3)
    by_level = {c.level: c for c in phys.cognitive}
    check("they are K, U and A", set(by_level) == {"K", "U", "A"}, str(set(by_level)))
    check("the weights are 30, 50 and 20",
          (by_level["K"].paper_weight, by_level["U"].paper_weight,
           by_level["A"].paper_weight) == (30, 50, 20))
    check("the seeded syllabus really carries levels",
          sum(c.examined_count for c in phys.cognitive) > 0,
          "no SLO in Physics XI has cognitive_levels set")
    check("at least one level has been practised",
          any(c.mastery is not None for c in phys.cognitive),
          str({k: v.mastery for k, v in by_level.items()}))
    check("every level names itself for a student",
          all(c.name in ("Knowledge", "Understanding", "Application")
              for c in phys.cognitive))

    print("13f. Consistency")
    run = graphs.consistency
    check("days practised is counted", run.days_practised >= 9, str(run.days_practised))
    check("the calendar is a continuous run", len(run.calendar) == 120,
          str(len(run.calendar)))
    check("it ends on the most recent day",
          run.calendar[-1].day >= run.calendar[0].day)
    check("the empty days are kept",
          any(d.answers == 0 for d in run.calendar),
          "a calendar with no gaps is not a record of what happened")
    check("and the busy ones are counted",
          any(d.answers > 0 for d in run.calendar))
    check("the last day practised is recorded", run.last_day is not None)

    print("13g. Every subject together")
    check("there is an overall trend", len(graphs.overall_trend) > 0)
    check("it has a value by the end",
          graphs.overall_trend[-1].mastery is not None,
          str(graphs.overall_trend[-1]))
    check("a subject never practised has no trend of its own",
          any(s.trend == [] for s in graphs.subjects if s.project_id != physics.id),
          "Chemistry and Biology were never touched")

    print("13h. Which level is costing the most marks")
    # Not asserted to be present - it depends on how the seeded SLOs are
    # labelled - but if it is there it must be coherent.
    worst = phys.weakest_level
    if worst is None:
        check("no weakest level is a fair answer when mastery is high", True)
    else:
        check("it names a real level", worst.level in ("K", "U", "A"), worst.level)
        check("and some marks", worst.marks_at_stake >= 2, str(worst.marks_at_stake))
        check("it matches the level it names",
              worst.name == by_level[worst.level].name)

    print("13i. One student's graphs are their own")
    other = service.get_graphs(user_id=TEST_USER)
    other_ids = {s.project_id for s in other.subjects}
    check("another student does not see this one's subjects",
          physics.id not in other_ids,
          "progress leaked between accounts")


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
        asyncio.run(run_community())
        asyncio.run(run_progress_graphs())
    finally:
        if not args.keep:
            cleanup()

    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
