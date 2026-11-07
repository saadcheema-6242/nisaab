"""Check who is let in and who is turned away, with no database and no clock.

Run with:
    python scripts/admin/check_moderation.py

Getting this wrong has two shapes and both are bad. Too loose, and a suspended
account keeps working, which makes the whole feature theatre. Too tight, and a
temporary ban never expires, so a student who was told "one week" is locked out
for good and nobody finds out until they complain.

The boundary is the dangerous part, so it is checked on both sides and at the
exact moment of expiry.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.moderation import (  # noqa: E402
    ACTIVE,
    UNVERIFIED_MESSAGE,
    PERMANENT,
    TEMPORARY,
    ban_message,
    ban_state,
    is_banned,
    is_verified,
    until_from_days,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

print("an account with no ban on it is simply let in")
check("never banned", not is_banned(None, None, NOW))
check("and reads as active", ban_state(None, None, NOW) == ACTIVE)
check("an end date with no ban is not a ban",
      not is_banned(None, NOW + DAY, NOW),
      "banned_until alone must never shut anyone out")

print()
print("a permanent ban holds")
check("banned with no end date", is_banned(NOW - DAY, None, NOW))
check("and reads as permanent", ban_state(NOW - DAY, None, NOW) == PERMANENT)
check("still banned a year later", is_banned(NOW - DAY, None, NOW + timedelta(days=365)))

print()
print("a temporary ban holds until it expires, and then stops")
until = NOW + timedelta(days=7)
check("during", is_banned(NOW, until, NOW))
check("reads as temporary", ban_state(NOW, until, NOW) == TEMPORARY)
check("an hour before it ends", is_banned(NOW, until, until - HOUR))
check("one second before it ends",
      is_banned(NOW, until, until - timedelta(seconds=1)))
check("NOT at the exact moment it ends", not is_banned(NOW, until, until))
check("NOT one second after", not is_banned(NOW, until, until + timedelta(seconds=1)))
check("NOT a week after", not is_banned(NOW, until, until + timedelta(days=7)))
check("an expired ban reads as active again",
      ban_state(NOW, until, until + DAY) == ACTIVE)

print()
print("the record of an expired ban is kept, but does not lock anyone out")
old = is_banned(NOW - timedelta(days=30), NOW - timedelta(days=23), NOW)
check("a ban from last month does not bite today", not old)

print()
print("a stored time with no timezone is read as UTC, not refused")
naive_at = datetime(2026, 11, 4, 10, 0)
naive_until = datetime(2026, 11, 11, 10, 0)
try:
    check("naive values compare without raising",
          is_banned(naive_at, naive_until, NOW))
    check("and expire correctly",
          not is_banned(naive_at, naive_until, NOW + timedelta(days=30)))
    check("naive with an aware now, and the other way round",
          is_banned(NOW - DAY, naive_until, naive_at))
except Exception as error:  # noqa: BLE001
    check("naive values compare without raising", False,
          f"{type(error).__name__}: {error}")

print()
print("a returned value is a yes or a no, never a date")
for name, args in (
    ("permanent", (NOW - DAY, None, NOW)),
    ("temporary", (NOW, NOW + DAY, NOW)),
    ("expired", (NOW, NOW - DAY, NOW)),
    ("none", (None, None, NOW)),
):
    got = is_banned(*args)
    check(f"{name} returns a bool", isinstance(got, bool), f"{type(got).__name__}: {got!r}")

print()
print("how long a suspension runs for")
check("seven days lands seven days out", until_from_days(7, NOW) == NOW + timedelta(days=7))
check("one day", until_from_days(1, NOW) == NOW + DAY)
for empty in (None, 0, -1, -30):
    check(f"{empty!r} means permanent, not already expired",
          until_from_days(empty, NOW) is None)
check("a permanent ban made this way really is permanent",
      is_banned(NOW, until_from_days(None, NOW), NOW + timedelta(days=3650)))

print()
print("the student is told something they can act on")
said = ban_message(NOW + timedelta(days=7), "Posting answers to a live paper")
check("it says when it ends", "11 November 2026" in said, said)
check("it gives the reason", "live paper" in said, said)
check("it says who to ask", "teacher" in said.lower(), said)

forever = ban_message(None, "Repeated abuse")
check("a permanent one does not invent an end date",
      "until" not in forever.split("Contact")[0].lower(), forever)
check("it still says why", "Repeated abuse" in forever, forever)

quiet = ban_message(None, None)
check("no reason given is still a sentence", quiet.strip().endswith("mistake."), quiet)
check("and does not print the word None", "None" not in quiet, quiet)
check("an empty reason is not shown as 'Reason: '",
      "Reason:" not in ban_message(None, "   "), ban_message(None, "   "))

print()
print("the ban is enforced where every request passes, not per router")
auth = (ROOT / "src/edu-api/auth.py").read_text(encoding="utf-8")
check("get_current_user checks it", "is_banned(" in auth)
check("and refuses with 403, so the client does not retry as if expired",
      "HTTP_403_FORBIDDEN" in auth.split("is_banned(")[1][:400], "")
check("the student is told why", "ban_message(" in auth)

print()
print("only an administrator reaches any of it")
router = (ROOT / "src/edu-api/routers/admin.py").read_text(encoding="utf-8")
for guarded in ("list_users", "get_user", "ban_user", "unban_user", "delete_user"):
    block = router.split(f"async def {guarded}(")[1].split(")")[0:6]
    check(f"{guarded} requires an administrator",
          "require_admin" in "".join(block), "")
check("admins come from settings, not from a database column",
      "get_settings().admins" in router)
check("an administrator cannot suspend themselves",
      "cannot suspend yourself" in router)
check("an administrator cannot delete themselves",
      "cannot delete yourself" in router)
check("deleting needs the email typed again", "confirm_email" in router)
check("a wrong email deletes nothing",
      "Nothing was deleted." in router)
check("the section is hidden rather than refused",
      'status_code=404, detail="Not found"' in router)

print()
print("a token proves a password was typed, not that the address exists")
check("Identity Platform says verified", is_verified({"email_verified": True}))
check("Identity Platform says not verified", not is_verified({"email_verified": False}))
check("a string true is still true", is_verified({"email_verified": "true"}))
check("a string false is not", not is_verified({"email_verified": "false"}))
check("Supabase inside user_metadata",
      is_verified({"user_metadata": {"email_verified": True}}))
check("Supabase records the moment instead of a flag",
      is_verified({"email_confirmed_at": "2026-11-07T07:00:00Z"}))
check("and sometimes nests that too",
      is_verified({"user_metadata": {"confirmed_at": "2026-11-07T07:00:00Z"}}))

print()
print("silence is never taken for confirmation")
for name, claims in (
    ("no claim at all", {"sub": "abc", "email": "x@y.com"}),
    ("empty token", {}),
    ("no token", None),
    ("metadata that is not an object", {"user_metadata": "nope"}),
    ("an empty confirmation time", {"email_confirmed_at": ""}),
    ("a whitespace confirmation time", {"email_confirmed_at": "   "}),
    ("verified is null", {"email_verified": None}),
    ("verified is zero", {"email_verified": 0}),
):
    check(f"{name}: treated as unverified", not is_verified(claims), str(claims))

print()
print("the student is told what to do about it")
check("it says to confirm the address", "confirm your email" in UNVERIFIED_MESSAGE.lower())
check("it says where the link is", "inbox" in UNVERIFIED_MESSAGE.lower())
check("it says what to do next", "sign in again" in UNVERIFIED_MESSAGE.lower())

print()
print("only new accounts are asked, so no class is locked out mid-week")
auth = (ROOT / "src/edu-api/auth.py").read_text(encoding="utf-8")
check("verification is checked at the one point every request passes",
      "is_verified(payload)" in auth)
check("an account that already exists is let through",
      "not user_service.exists(supabase_user_id)" in auth)
check("both conditions must hold before anyone is refused",
      "not is_verified(payload) and not user_service.exists(" in auth)
check("it refuses with 403, not 401",
      "HTTP_403_FORBIDDEN" in auth.split("is_verified(payload)")[1][:300])

users = (ROOT / "src/shared/core/src/edu_core/services/users.py").read_text(encoding="utf-8")
check("exists() only asks whether the row is there",
      "db.query(User.id).filter(User.id == user_id).first() is not None" in users)

print()
print("every column the admin service names really exists")
# A quiz, a note and a flashcard group belong to a project, not directly to a
# student. Assuming they all had user_id made the counting crash, and it took
# the whole delete with it - the account detail page, deleting one student and
# deleting every student, all 500. Reading the models rather than importing
# them, because edu_db needs pgvector and this has to run anywhere.
import ast  # noqa: E402

models_src = (ROOT / "src/shared/db/src/edu_db/models.py").read_text(encoding="utf-8")
columns: dict[str, set[str]] = {}
for node in ast.walk(ast.parse(models_src)):
    if isinstance(node, ast.ClassDef):
        columns[node.name] = {
            stmt.target.id
            for stmt in node.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
        }

admin_src = (ROOT / "src/shared/core/src/edu_core/services/admin.py").read_text(
    encoding="utf-8"
)
missing = []
for node in ast.walk(ast.parse(admin_src)):
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in columns
        and not node.attr.startswith("_")
    ):
        owner, field = node.value.id, node.attr
        known = columns[owner] | {"id", "metadata", "query", "in_", "isnot"}
        if field not in known:
            missing.append(f"{owner}.{field}")

check("no column is named that the model does not have",
      not missing, ", ".join(sorted(set(missing))))

for model, column in (
    ("FlashcardGroup", "user_id"), ("Quiz", "user_id"), ("Note", "user_id"),
):
    check(f"{model} really has no {column}, so it must go through the project",
          column not in columns.get(model, set()))
for model in ("Chat", "MindMap", "PracticePaper", "StudyPlan", "PracticeRecord",
              "SrqAttempt", "CommunityPost"):
    check(f"{model} does own its rows directly", "user_id" in columns.get(model, set()))

check("project-owned kinds are counted through the project",
      "by_project(Quiz)" in admin_src and "by_project(Note)" in admin_src)
check("flashcard groups too",
      "FlashcardGroup.project_id.in_(project_ids)" in admin_src)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
