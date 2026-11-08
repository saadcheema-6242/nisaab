"""Check who shares a room and what they are called in it, with no database.

Run with:
    python scripts/admin/check_community.py

One rule here is worth more than the rest. A student's email is not theirs to
hand to a room full of classmates, and getting it wrong would not raise an
error or look broken - it would quietly publish a few hundred teenagers'
addresses. There is no test a student can run for that, so it is run here.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.community_rules import (  # noqa: E402
    MAX_BODY,
    SOMEONE,
    check_body,
    display_name,
    room_name,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("an email address never reaches the room")
for name, email, expected in (
    ("Ayesha Khan", "ayesha@example.com", "Ayesha Khan"),
    (None, "ayesha@example.com", "ayesha"),
    ("", "ayesha.khan+fsc@gmail.com", "ayesha.khan+fsc"),
    ("   ", "a.b.c@school.edu.pk", "a.b.c"),
    (None, None, SOMEONE),
    (None, "", SOMEONE),
    (None, "@nothing.com", SOMEONE),
    ("  Bilal  ", "bilal@x.com", "Bilal"),
):
    got = display_name(name, email)
    check(f"{name!r}/{email!r} -> {got!r}", got == expected, f"wanted {expected!r}")

for email in ("ayesha@example.com", "a.b.c@school.edu.pk", "ayesha.khan+fsc@gmail.com"):
    for name in (None, "", "Ayesha Khan"):
        shown = display_name(name, email)
        check(
            f"no @ in what is shown for {email!r} (name={name!r})",
            "@" not in shown,
            shown,
        )
        check(
            f"the domain of {email!r} never appears",
            email.split("@")[1] not in shown,
            shown,
        )

print()
print("a room is a grade and a group together, never one or the other")
for grade, group, expected in (
    (11, "PRE_MED", "Pre-Medical XI"),
    (12, "PRE_MED", "Pre-Medical XII"),
    (11, "PRE_ENG", "Pre-Engineering XI"),
    (12, "ICS", "ICS XII"),
):
    got = room_name(grade, group)
    check(f"{grade}/{group} -> {got!r}", got == expected, f"wanted {expected!r}")

check("Pre-Medical XI and Pre-Engineering XI are different rooms",
      room_name(11, "PRE_MED") != room_name(11, "PRE_ENG"))
check("XI and XII are different rooms",
      room_name(11, "PRE_MED") != room_name(12, "PRE_MED"))
check("an unknown group still reads as something",
      room_name(11, "NEW_GROUP") == "NEW_GROUP XI", room_name(11, "NEW_GROUP"))
check("an unknown grade still reads as something",
      room_name(9, "ICS") == "ICS 9", room_name(9, "ICS"))

print()
print("what may be posted")
check("an ordinary post is kept as written",
      check_body("  How do you do part (b)?  ") == "How do you do part (b)?")
check("a post at the limit is allowed", len(check_body("a" * MAX_BODY)) == MAX_BODY)

for bad, why in ((None, "nothing"), ("", "empty"), ("   \n  ", "only spaces")):
    try:
        check_body(bad)
        check(f"{why} is refused", False, "it was accepted")
    except ValueError:
        check(f"{why} is refused", True)

try:
    check_body("a" * (MAX_BODY + 1))
    check("one character over the limit is refused", False, "it was accepted")
except ValueError as error:
    check("one character over the limit is refused", True)
    check("and the message says what the limit is", str(MAX_BODY) in str(error), str(error))

print()
print("the room is never taken from the request")
service = (ROOT / "src/shared/core/src/edu_core/services/community.py").read_text(
    encoding="utf-8"
)
router = (ROOT / "src/edu-api/routers/community.py").read_text(encoding="utf-8")
check("the service works the room out from the student's own profile",
      "_room_of(db, user_id)" in service)
check("and reads it from the profile table", "StudentProfile" in service)
# The fields only. The docstring beside them explains why grade and group are
# absent, and a check that read the prose would fail on the explanation.
import ast  # noqa: E402

post_create = next(
    node
    for node in ast.walk(ast.parse(router))
    if isinstance(node, ast.ClassDef) and node.name == "PostCreate"
)
fields = {
    node.target.id
    for node in post_create.body
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
}
check("the request body carries no grade", "grade" not in fields, str(fields))
check("the request body carries no group", "group_code" not in fields, str(fields))
# Everything a student types into the composer, and nothing else. The point
# is not the exact list, it is that the client cannot smuggle in a grade, a
# group or a user id and be believed - those are read from the profile. The
# poll fields joined this list when polls were added; the check was not
# updated with them, so it has been failing since.
check("it carries only what a student actually types",
      fields == {"body", "parent_id", "poll_question", "poll_options"}, str(fields))
check("and never anything the server should decide",
      not ({"grade", "group_code", "user_id", "room", "flagged"} & fields), str(fields))
check("a reply must be in the reader's own room",
      "That post is not in your room" in service)
check("only your own post can be deleted",
      "CommunityPost.user_id == user_id" in service)

print()
print("a post is shown as text, never rendered")
page = (ROOT / "src/edu-web/src/features/community/community-page.tsx").read_text(
    encoding="utf-8"
)
check("no dangerouslySetInnerHTML anywhere near it",
      "dangerouslySetInnerHTML" not in page)
check("whitespace is preserved rather than markup interpreted",
      "whitespace-pre-wrap" in page)
check("a long word cannot break the layout", "break-words" in page)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
