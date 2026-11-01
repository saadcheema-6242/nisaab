"""Check how attached pictures are carried through a conversation.

Run with:
    python scripts/admin/check_chat_attachments.py

The bug this guards against: a student attached a picture, the picture was
thrown away before the tutor saw it, the tutor was told to search the project
documents instead, and the search returned an unrelated mind map - which the
tutor then described as though it were the student's picture.

So two rules are checked here, both without a database or a model:
  - the most recent pictures travel with every message, so the tutor still
    knows a picture several questions after it was attached;
  - a weak search result is dropped rather than offered as an answer.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The service module pulls in the database and AI packages, so the whole
# workspace has to be importable even though nothing here touches either.
for package in ("core", "db", "ai", "queue"):
    sys.path.insert(0, str(ROOT / f"src/shared/{package}/src"))

from edu_core.schemas.chats import FilePartDto, TextPartDto  # noqa: E402
from edu_core.storage import chat_upload_path  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


class FakeMessage:
    def __init__(self, role: str, parts: list) -> None:
        self.role = role
        self.parts = parts
        self.chat_id = "c1"


def picture(name: str, kind: str = "image/png") -> FilePartDto:
    return FilePartDto(
        id=name, file_name=name, file_type=kind,
        file_url=f"https://signed/{name}", file_path=f"p1/chat/{name}", order=0,
    )


def words(text: str) -> TextPartDto:
    return TextPartDto(id=text[:8], text_content=text, order=0)


print("the most recent pictures are the ones carried")
from edu_core.chat_attachments import (  # noqa: E402
    MAX_CARRIED_PICTURES,
    pictures_to_carry as carry,
)

one = [FakeMessage("user", [words("what is this?"), picture("a.png")])]
check("a single picture is carried", len(carry(one)) == 1, str(len(carry(one))))

# The conversation moves on. The picture must still be there, or the tutor
# forgets it the moment the student asks a follow-up.
later = one + [
    FakeMessage("assistant", [words("It is a free-body diagram.")]),
    FakeMessage("user", [words("so what is the net force?")]),
]
check(
    "it is still carried several messages later",
    len(carry(later)) == 1,
    str(len(carry(later))),
)

many = [
    FakeMessage("user", [words(f"and this one? {i}"), picture(f"{i}.png")])
    for i in range(MAX_CARRIED_PICTURES + 3)
]
kept = carry(many)
check(
    f"a long conversation carries at most {MAX_CARRIED_PICTURES}",
    len(kept) == MAX_CARRIED_PICTURES,
    str(len(kept)),
)
newest = {id(p) for m in many[-MAX_CARRIED_PICTURES:] for p in m.parts if isinstance(p, FilePartDto)}
check("and they are the newest ones, not the oldest", kept == newest)

mixed = [
    FakeMessage("user", [picture("notes.pdf", "application/pdf"), picture("b.png")]),
]
check(
    "a PDF is not carried as a picture",
    len(carry(mixed)) == 1,
    str(len(carry(mixed))),
)
check("a conversation with no pictures carries none",
      carry([FakeMessage("user", [words("hello")])]) == set())

print()
print("a picture is stored with its conversation, not among the documents")
path = chat_upload_path("proj-1", "abc", "png")
check("the path is under the project's chat folder", path == "proj-1/chat/abc.png", path)
check("a file with no extension still gets a path",
      chat_upload_path("proj-1", "abc", "") == "proj-1/chat/abc",
      chat_upload_path("proj-1", "abc", ""))
check("it cannot collide with a document's path",
      chat_upload_path("p", "x", "png") != "p/x.png")

print()
print("a weak search result is not offered as an answer")
# Read the floor out of the source rather than importing it: rag.py pulls
# in the whole AI package, and this check needs none of it.
import ast  # noqa: E402

rag = ast.parse((ROOT / 'src/shared/ai/src/edu_ai/tools/rag.py').read_text(encoding='utf-8'))
MIN_SCORE = next(
    float(node.value.args[0].args[1].value)  # float(os.getenv(name, default))
    for node in ast.walk(rag)
    if isinstance(node, ast.Assign)
    and getattr(node.targets[0], 'id', '') == 'MIN_SCORE'
)

check("there is a floor at all", 0.0 < MIN_SCORE < 1.0, str(MIN_SCORE))
# The real case: "what's this?" against a project holding one unrelated file.
weak = [{"score": 0.08, "title": "mind-map.png"}]
check("an unrelated file scores below the floor",
      all(s["score"] < MIN_SCORE for s in weak))
strong = [{"score": 0.72, "title": "chapter-3.pdf"}]
check("a genuine match scores above it",
      all(s["score"] >= MIN_SCORE for s in strong))

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
