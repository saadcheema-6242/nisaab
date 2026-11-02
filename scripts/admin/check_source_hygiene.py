"""Check the three faults that made the tutor answer about the wrong document.

Run with:
    python scripts/admin/check_source_hygiene.py

A student attached one PDF and asked an unrelated question. The reply cited
"study-plan (1).pdf" twice, cited a third file nothing had asked about, and
opened with "I have successfully read and analyzed your study plan". Three
separate causes, one symptom, so all three are pinned here.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def source_of(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


print("one document is cited once, however many times it was searched")
chats = source_of("src/shared/core/src/edu_core/services/chats.py")
check(
    "sources are keyed on the document, not the segment that matched",
    'source_id = source.get("document_id") or source.get("id", "")' in chats,
)
check(
    "the old segment-first key is gone",
    'source.get("id") or source.get("document_id", "")' not in chats,
)

print()
print("an attachment note states a fact, it does not give an order")
router = source_of("src/edu-api/routers/chats.py")
check(
    "the note is just the filename",
    'note = f"(attached: {\', \'.join(documents)})"' in router,
    "note text changed",
)
# Only code counts: the comment above the note quotes the old wording on
# purpose, to say why it was wrong.
code = "\n".join(
    line for line in router.splitlines() if not line.lstrip().startswith("#")
)
for order in ("search the project documents to look inside", "now being read and indexed"):
    check(f"no longer sent: {order!r}", order not in code)

print()
print("conversations that already carry the old order are cleaned on read")
from edu_core.chat_attachments import without_stale_orders  # noqa: E402

old = (
    "see this study plan of python\n\n(attached: study-plan (1).pdf - now "
    "being read and indexed; search the project documents to look inside, and "
    "say it is still being read if nothing is found yet)"
)
cleaned = without_stale_orders(old)
check("the standing order is removed", "search the project documents" not in cleaned, cleaned)
check("the student's own question survives", "see this study plan of python" in cleaned)
check("the filename survives, so the tutor knows what was sent",
      "study-plan (1).pdf" in cleaned, cleaned)
check("an ordinary message is untouched",
      without_stale_orders("what is a logic gate?") == "what is a logic gate?")
check("empty text does not break it", without_stale_orders("") == "")
check("text with no note is unchanged",
      without_stale_orders("(attached: a.pdf)") == "(attached: a.pdf)")

print()
print("a weak or trailing search result is dropped")
rag = source_of("src/shared/ai/src/edu_ai/tools/rag.py")
floor = float(re.search(r'DOCUMENT_SEARCH_MIN_SCORE", "([0-9.]+)"', rag).group(1))
check("there is an absolute floor", 0.3 < floor < 0.9, str(floor))
check("there is a relative cut as well", "best * 0.75" in rag)

# The shape of the real failure: one decent match, one unrelated file alongside
scored = [{"score": 0.62, "title": "notes.pdf"}, {"score": 0.33, "title": "study-plan.pdf"}]
best = max(s["score"] for s in scored)
kept = [s for s in scored if s["score"] >= floor and s["score"] >= best * 0.75]
check("the unrelated file is dropped", [s["title"] for s in kept] == ["notes.pdf"], str(kept))

weak = [{"score": 0.31, "title": "study-plan.pdf"}]
best_weak = max(s["score"] for s in weak)
kept_weak = [s for s in weak if s["score"] >= floor and s["score"] >= best_weak * 0.75]
check("a search with nothing good returns nothing", kept_weak == [], str(kept_weak))

good = [{"score": 0.80, "title": "a.pdf"}, {"score": 0.72, "title": "b.pdf"}]
best_good = max(s["score"] for s in good)
kept_good = [s for s in good if s["score"] >= floor and s["score"] >= best_good * 0.75]
check("two genuinely close matches both survive", len(kept_good) == 2, str(kept_good))

print()
print("results are offered to the tutor, not asserted as the answer")
check("they are called search results", "not an answer and not necessarily" in rag)
check("the tutor is told not to announce what it read",
      "Do not open your reply by announcing what you have read" in rag)
check("the old assertion is gone",
      "Here is relevant information from the course documents" not in rag)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
