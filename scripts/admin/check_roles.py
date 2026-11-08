"""Check who is allowed to be what, without a database.

The dangerous case is the one that looks harmless: an account that ticked
"teacher" at signup and has not been approved. If anything treats that as a
teacher, a stranger appears in the administrator's scheduling dropdown and
can be put in front of a class. Every question about a teacher is asked here
twice, once approved and once not.

Run: python scripts/admin/check_roles.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.roles import (  # noqa: E402
    STUDENT,
    TEACHER,
    RoleError,
    can_teach,
    check_grades,
    check_role,
    check_subjects,
    check_text,
    is_approved_teacher,
    is_pending_teacher,
    needs_onboarding,
    teaches,
)

failures: list[str] = []
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
SUBJECTS = ["PHY", "CHEM", "BIO", "MATH", "CS"]


def check(label: str, ok: bool, note: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"  -- {note}" if note else ""))
    if not ok:
        failures.append(label)


def refuses(label, fn, *args):
    try:
        fn(*args)
    except RoleError:
        check(label, True)
        return
    check(label, False, "it was accepted")


print("an unapproved teacher is not a teacher")
check("pending is pending", is_pending_teacher(TEACHER, None))
check("and is not approved", not is_approved_teacher(TEACHER, None))
# The one that matters. Reading the role alone offers them a class.
check("they CANNOT be put in front of a class",
      not can_teach(TEACHER, None),
      "a stranger who ticked a box would be assignable to real students")
check("once approved, they can", can_teach(TEACHER, NOW))
check("a student never can", not can_teach(STUDENT, None))
# A student row with a stray approval date is nonsense, and must not pass.
check("a student with an approval date still cannot",
      not can_teach(STUDENT, NOW),
      "the role and the date must agree, not either one alone")

print()
print("the administrator")
check("an admin can take a class without being approved",
      can_teach(STUDENT, None, is_admin=True),
      "they are who does the approving; self-approval would be a loop")
check("and is not sent to a waiting page",
      needs_onboarding(STUDENT, True, True, None) is None)
check("but does pick a cohort once",
      needs_onboarding(STUDENT, True, False, None) == "/onboarding",
      "without a profile the subject pages have nothing to read")

print()
print("where each account is sent")
check("a new student onboards",
      needs_onboarding(STUDENT, False, False, None) == "/onboarding")
check("an onboarded student carries on",
      needs_onboarding(STUDENT, False, True, None) is None)
check("a pending teacher waits",
      needs_onboarding(TEACHER, False, False, None) == "/awaiting-approval")
check("even one who somehow has a profile",
      needs_onboarding(TEACHER, False, True, None) == "/awaiting-approval",
      "approval is the gate, not setup")
check("an approved teacher carries on",
      needs_onboarding(TEACHER, False, False, NOW) is None,
      "a teacher has no year or group to pick")

print()
print("what a teacher says they teach")
check("subjects come back in the order given",
      check_subjects(["BIO", "PHY"], SUBJECTS) == ["BIO", "PHY"])
check("duplicates are dropped once",
      check_subjects(["PHY", "phy", " PHY "], SUBJECTS) == ["PHY"])
check("lower case is accepted", check_subjects(["phy"], SUBJECTS) == ["PHY"])
check("blanks are ignored", check_subjects(["", "PHY"], SUBJECTS) == ["PHY"])
refuses("a subject that is not on the FSc list", check_subjects, ["URDU"], SUBJECTS)
refuses("no subjects at all", check_subjects, [], SUBJECTS)
refuses("only blanks", check_subjects, ["", "  "], SUBJECTS)

check("years are sorted and deduplicated", check_grades([12, 11, 12]) == [11, 12])
refuses("no years", check_grades, [])
refuses("a year FSc does not have", check_grades, [9])
refuses("a year above FSc", check_grades, [13])

check("a school name is trimmed",
      check_text("  IMCB G-10/4  ", 120, "the school") == "IMCB G-10/4")
check("an empty one becomes nothing", check_text("   ", 120, "x") is None)
refuses("an absurdly long one", check_text, "x" * 200, 120, "the school")

print()
print("approval to teach Physics is not approval to teach everything")
check("their own subject and year", teaches("PHY", 11, ["PHY"], [11]))
check("not a subject they did not claim",
      not teaches("BIO", 11, ["PHY"], [11]),
      "a Physics teacher could schedule Biology")
check("not a year they did not claim",
      not teaches("PHY", 12, ["PHY"], [11]))
check("case does not matter", teaches("phy", 11, ["PHY"], [11]))
check("an administrator schedules anything",
      teaches("BIO", 12, [], [], is_admin=True))
check("nothing claimed means nothing allowed",
      not teaches("PHY", 11, [], []))

print()
print("the role itself")
check("student is a role", check_role(STUDENT) == STUDENT)
check("teacher is a role", check_role(TEACHER) == TEACHER)
refuses("admin is not a role on the account", check_role, "admin")
refuses("nothing is not a role", check_role, "")

if failures:
    print(f"\n{len(failures)} failed: {failures[0]}")
    sys.exit(1)
print("\nall checks passed")
