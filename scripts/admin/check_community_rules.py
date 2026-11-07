"""Check the rules of the class room: uploads, polls and the AI review.

Run with:
    python scripts/admin/check_community_rules.py

No database, no network, no model. Everything here is a plain function over
plain values, which is why the awkward cases can be stated directly:
the file that lies about what it is, the poll that rounds to 99 percent, the
model reply that arrives wrapped in markdown, the student who says they are
struggling and must not be sent a warning.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.community_media import (  # noqa: E402
    AUDIO,
    FILE,
    IMAGE,
    MAX_ATTACHMENTS,
    MAX_BYTES,
    MAX_VOICE_BYTES,
    check_attachment_count,
    check_upload,
    extension_of,
    kind_of,
    safe_name,
    sniffed_kind,
    stored_path,
)
from edu_core.community_poll import (  # noqa: E402
    MAX_OPTIONS,
    check_options,
    check_question,
    tally,
    winning,
)
from edu_core.community_review import (  # noqa: E402
    CHEATING,
    CLEAN,
    CONTACT,
    SELF_HARM,
    THREAT,
    message_for,
    read_review,
    review_prompt,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def refuses(name: str, call) -> None:
    try:
        call()
    except ValueError:
        check(name, True)
        return
    except Exception as error:  # noqa: BLE001
        check(name, False, f"raised {type(error).__name__}, wanted ValueError")
        return
    check(name, False, "was allowed")


JPEG = b"\xff\xd8\xff\xe0" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
PDF = b"%PDF-1.7" + b"0" * 20
EXE = b"MZ\x90\x00" + b"0" * 20

print("the kinds a student can attach")
check("a photo is an image", kind_of("image/jpeg") == IMAGE)
check("a png too", kind_of("image/png") == IMAGE)
check("a voice note is audio", kind_of("audio/webm") == AUDIO)
check("a pdf is a file", kind_of("application/pdf") == FILE)
check("a docx is a file", kind_of(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == FILE)
check("a charset suffix does not confuse it", kind_of("text/plain; charset=utf-8") == FILE)
check("upper case is fine", kind_of("IMAGE/PNG") == IMAGE)
check("an executable is nothing", kind_of("application/x-msdownload") is None)
check("a zip is nothing", kind_of("application/zip") is None)
check("empty is nothing", kind_of("") is None)

print()
print("size: 50MB for files, less for a voice note")
check("MAX_BYTES is 50MB", MAX_BYTES == 50 * 1024 * 1024, str(MAX_BYTES))
check("a 10MB pdf is fine",
      check_upload("notes.pdf", "application/pdf", 10 * 1024 * 1024, PDF)[0] == FILE)
check("exactly 50MB is fine",
      check_upload("big.pdf", "application/pdf", MAX_BYTES, PDF)[0] == FILE)
refuses("one byte over 50MB is not",
        lambda: check_upload("big.pdf", "application/pdf", MAX_BYTES + 1, PDF))
refuses("an empty file is not",
        lambda: check_upload("empty.pdf", "application/pdf", 0, b""))
refuses("a negative size is not",
        lambda: check_upload("odd.pdf", "application/pdf", -5, b""))
refuses("a voice note over its own limit is not",
        lambda: check_upload("v.webm", "audio/webm", MAX_VOICE_BYTES + 1))
check("a voice note under it is fine",
      check_upload("v.webm", "audio/webm", 1024)[0] == AUDIO)

print()
print("the size message tells the student the actual numbers")
try:
    check_upload("big.pdf", "application/pdf", 60 * 1024 * 1024, PDF)
    check("an oversize file is refused", False, "was allowed")
except ValueError as error:
    said = str(error)
    check("it says how big the file is", "60MB" in said, said)
    check("and what the limit is", "50MB" in said, said)

print()
print("a file that lies about what it is")
refuses("an exe declared as a png",
        lambda: check_upload("photo.png", "image/png", 999, EXE))
refuses("a pdf declared as an image",
        lambda: check_upload("x.png", "image/png", 999, PDF))
check("bytes that agree are accepted",
      check_upload("real.png", "image/png", 999, PNG)[0] == IMAGE)
check("no bytes to check means the claim stands",
      check_upload("real.png", "image/png", 999)[0] == IMAGE)
check("an unknown signature does not block a good file",
      check_upload("notes.txt", "text/plain", 99, b"hello there")[0] == FILE)
check("a jpeg is sniffed", sniffed_kind(JPEG) == IMAGE)
check("a pdf is sniffed", sniffed_kind(PDF) == FILE)
check("random bytes are not", sniffed_kind(b"zzzz") is None)

print()
print("names a browser might send")
check("a path is stripped", safe_name("../../etc/passwd") == "passwd")
check("a windows path too", safe_name("C:\\\\Users\\\\me\\\\notes.pdf") == "notes.pdf")
check("spaces survive", safe_name("my past paper.pdf") == "my past paper.pdf")
check("a hidden file is not", safe_name(".bashrc") == "bashrc")
check("nothing becomes something", safe_name("") == "attachment")
check("only dots becomes something", safe_name("...") == "attachment")
check("None is handled", safe_name(None) == "attachment")
check("a very long name is cut", len(safe_name("a" * 500)) <= 120)
check("a quote cannot break out", "'" not in safe_name("it's a file'; rm -rf.pdf"))
check("the extension is read", extension_of("Notes.PDF") == ".pdf")
check("no extension is empty", extension_of("notes") == "")

print()
print("the extensions that are never allowed, whatever the type says")
for name in ("virus.exe", "run.bat", "thing.jar", "page.html", "icon.svg", "bundle.zip"):
    refuses(f"{name} is refused", lambda n=name: check_upload(n, "text/plain", 99))

print()
print("how many files on one post")
check(f"{MAX_ATTACHMENTS} is fine", check_attachment_count(MAX_ATTACHMENTS) is None)
refuses("one more is not", lambda: check_attachment_count(MAX_ATTACHMENTS + 1))
check("none is fine", check_attachment_count(0) is None)

print()
print("where an attachment is stored")
path = stored_path(11, "PRE_MED", "abc-123", 0, ".png")
check("it is keyed by room and post", path == "community/11-PRE_MED/abc-123/0.png", path)

print()
print("polls: the shape of a sensible one")
check("two options is a poll", check_options(["Yes", "No"]) == ["Yes", "No"])
check("blank boxes are dropped, not refused",
      check_options(["A", "B", "", "  "]) == ["A", "B"])
refuses("one option is not a poll", lambda: check_options(["Only"]))
refuses("none is not a poll", lambda: check_options([]))
refuses("too many is not", lambda: check_options([str(i) for i in range(MAX_OPTIONS + 1)]))
refuses("the same option twice is refused", lambda: check_options(["Yes", "yes"]))
refuses("an enormous option is refused", lambda: check_options(["A" * 200, "B"]))
check("a question is kept", check_question("  Which chapter?  ") == "Which chapter?")
refuses("an empty question is not", lambda: check_question("   "))
refuses("None is not", lambda: check_question(None))

print()
print("poll percentages always total 100")
for counts in (
    [1, 1, 1], [2, 1], [1, 0], [0, 0, 0], [5, 3, 2], [1, 1, 1, 1, 1, 1],
    [7, 7, 7], [1, 2, 3, 4], [100, 1], [1] * 6, [0, 1, 0],
):
    got = tally(counts)
    total = sum(got)
    ok = total == 100 or sum(counts) == 0
    check(f"{counts} -> {got} totals {total}", ok)

check("thirds do not come to 99", sum(tally([1, 1, 1])) == 100, str(tally([1, 1, 1])))
check("nobody voted means all zero", tally([0, 0]) == [0, 0])
check("a single voter is 100", tally([1, 0]) == [100, 0], str(tally([1, 0])))

print()
print("who is winning")
check("the clear leader", winning([5, 2, 1]) == {0})
check("a tie has no single winner", winning([3, 3, 1]) == {0, 1})
check("before any votes, nobody", winning([0, 0, 0]) == set())
check("empty poll, nobody", winning([]) == set())

print()
print("the review prompt tells the model where it is")
prompt = review_prompt("is this right?", "Pre-Medical XI")
check("it names the room", "Pre-Medical XI" in prompt)
check("it includes the post", "is this right?" in prompt)
check("it says the students are Pakistani", "Pakistani" in prompt)
check("it warns against over-flagging", "wrongly flagged" in prompt)
check("it says Urdu is normal", "Urdu" in prompt)
check("it asks for JSON", "JSON" in prompt)

print()
print("reading what the model sends back")
check("plain json", read_review('{"finding":"bullying","confidence":0.9}').finding == "bullying")
check("wrapped in markdown",
      read_review('```json\n{"finding":"spam","confidence":0.8}\n```').finding == "spam")
check("with a sentence in front",
      read_review('Here is my answer: {"finding":"hate","confidence":0.95}').finding == "hate")
check("clean stays clean", read_review('{"finding":"clean","confidence":0.1}').finding == CLEAN)

print()
print("anything unreadable is treated as clean, never as a finding")
for text in ("", "   ", "not json at all", "{broken", "null", "[]", "{}"):
    check(f"{text!r} reads as clean", read_review(text).finding == CLEAN)
check("an invented label reads as clean",
      read_review('{"finding":"wizardry","confidence":0.99}').finding == CLEAN)
check("a non-numeric confidence does not raise",
      read_review('{"finding":"spam","confidence":"high"}').finding == CLEAN)

print()
print("a guess is not acted on")
check("low confidence bullying is dropped",
      read_review('{"finding":"bullying","confidence":0.3}').finding == CLEAN)
check("high confidence bullying is kept",
      read_review('{"finding":"bullying","confidence":0.8}').finding == "bullying")
check("but low confidence distress is NOT dropped",
      read_review('{"finding":"self_harm","confidence":0.2}').finding == SELF_HARM,
      "a possible cry for help is worth a false alarm")

print()
print("confidence is clamped, not trusted")
check("above one", read_review('{"finding":"spam","confidence":5}').confidence == 1.0)
check("below zero", read_review('{"finding":"spam","confidence":-3}').confidence == 0.0)

print()
print("how urgently an adult is needed")
check("distress outranks everything",
      read_review('{"finding":"self_harm","confidence":1}').severity
      > read_review('{"finding":"spam","confidence":1}').severity)
check("a threat is urgent", read_review('{"finding":"threat","confidence":1}').is_urgent)
check("spam is not", not read_review('{"finding":"spam","confidence":1}').is_urgent)
check("clean is not concerning",
      not read_review('{"finding":"clean","confidence":1}').is_concerning)

print()
print("what the author is told")
distress = read_review('{"finding":"self_harm","confidence":0.9}')
said = message_for(distress)
check("a struggling student is NOT warned", "reported" not in said.lower(), said)
check("they are told to talk to someone", "talk to someone" in said.lower(), said)
check("and that it is not about their studies", "studies can wait" in said.lower(), said)
check("distress is never a warning", not distress.should_warn)

warned = read_review('{"finding":"' + CHEATING + '","confidence":0.9}')
said = message_for(warned)
check("cheating gets a warning", "exam answers" in said, said)
check("that says what to do instead", "Ask how to solve it" in said, said)

contact = read_review('{"finding":"' + CONTACT + '","confidence":0.9}')
check("contact details get a warning", "contact details" in message_for(contact).lower())

check("a clean post is told nothing",
      message_for(read_review('{"finding":"clean","confidence":1}')) == "")

threat = read_review('{"finding":"' + THREAT + '","confidence":0.9}')
check("a threat is warned and urgent", threat.should_warn and threat.is_urgent)

print()
print("every finding has a label and a severity")
from edu_core.community_review import LABELS, SEVERITY  # noqa: E402
check("labels and severities cover the same set", set(LABELS) == set(SEVERITY),
      str(set(LABELS) ^ set(SEVERITY)))
for finding in SEVERITY:
    check(f"{finding} has a readable label", bool(LABELS.get(finding)))

print()
if failures:
    print(f"{len(failures)} failed:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
