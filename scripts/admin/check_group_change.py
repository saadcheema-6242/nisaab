"""Check what changing FSc group does to a student's subjects.

Run with:
    python scripts/admin/check_group_change.py

An ICS student was found carrying Chemistry and Biology: subjects they will
never sit, counted in their mastery and scheduled into their study plans.
Onboarding only ever added workspaces, so running it twice with different
groups left the union of both.

Two rules fix it and they are easy to get the wrong way round. A dropped
subject is hidden, never deleted, because a student who spent a month on
Chemistry notes before switching should not lose them to a dropdown. And only
the current grade is touched, because moving from XI to XII drops nothing.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.group_change import (  # noqa: E402
    GROUP_SUBJECTS,
    describe,
    is_group,
    plan_change,
    subjects_for,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("each group studies what FBISE says it studies")
check("Pre-Medical", subjects_for("PRE_MED") == ["PHY", "CHEM", "BIO"])
check("Pre-Engineering", subjects_for("PRE_ENG") == ["PHY", "CHEM", "MATH"])
check("ICS", subjects_for("ICS") == ["PHY", "MATH", "CS"])
check("every group has exactly three subjects",
      all(len(v) == 3 for v in GROUP_SUBJECTS.values()))
check("Physics is in all three", all("PHY" in v for v in GROUP_SUBJECTS.values()))
check("only ICS takes Computer Science",
      [g for g, v in GROUP_SUBJECTS.items() if "CS" in v] == ["ICS"])
check("only Pre-Medical takes Biology",
      [g for g, v in GROUP_SUBJECTS.items() if "BIO" in v] == ["PRE_MED"])

print()
print("the move a student actually made: Pre-Medical to ICS")
kept, added, dropped = plan_change("PRE_MED", "ICS")
check("Physics is kept", kept == ["PHY"], str(kept))
check("Maths and CS are added", added == ["MATH", "CS"], str(added))
check("Chemistry and Biology are dropped", dropped == ["CHEM", "BIO"], str(dropped))
check("the result is exactly three subjects",
      len(kept) + len(added) == 3, f"{kept} + {added}")
check("not five, which is the bug this fixes",
      len(set(kept + added + dropped)) == 5 and len(kept + added) == 3)

print()
print("every move between groups adds and drops correctly")
for old in GROUP_SUBJECTS:
    for new in GROUP_SUBJECTS:
        kept, added, dropped = plan_change(old, new)
        check(f"{old} to {new}: lands on the new group's subjects",
              sorted(kept + added) == sorted(subjects_for(new)),
              f"{kept}+{added} vs {subjects_for(new)}")
        check(f"{old} to {new}: drops only what the new group lacks",
              all(code not in subjects_for(new) for code in dropped), str(dropped))
        check(f"{old} to {new}: nothing is both kept and dropped",
              not set(kept) & set(dropped))

print()
print("choosing the group you are already in changes nothing")
for group in GROUP_SUBJECTS:
    kept, added, dropped = plan_change(group, group)
    check(f"{group}: nothing added", added == [], str(added))
    check(f"{group}: nothing dropped", dropped == [], str(dropped))
    check(f"{group}: everything kept", sorted(kept) == sorted(subjects_for(group)))
    check(f"{group}: says so plainly", "already in" in describe(group, group))

print()
print("a student with no group yet gets all three, drops nothing")
for group in GROUP_SUBJECTS:
    kept, added, dropped = plan_change(None, group)
    check(f"new student into {group}: all three added",
          sorted(added) == sorted(subjects_for(group)), str(added))
    check(f"new student into {group}: nothing dropped", dropped == [])

print()
print("an unknown group is refused before anything is written")
for bad in ("", "ARTS", "pre_med", "COMMERCE", None):
    try:
        plan_change("PRE_MED", bad)  # type: ignore[arg-type]
        check(f"{bad!r} refused", False, "it was accepted")
    except ValueError:
        check(f"{bad!r} refused", True)
    except TypeError:
        check(f"{bad!r} refused", True)
check("is_group agrees", not any(is_group(b) for b in ("", "ARTS", "pre_med")))

print()
print("the student is told which subjects, not how many")
said = describe("PRE_MED", "ICS")
for code in ("MATH", "CS", "CHEM", "BIO"):
    check(f"{code} is named", code in said, said)
check("it says the work is kept", "work in them is kept" in said, said)
check("it does not just count them", " 2 subjects" not in said, said)

print()
print("hidden, not deleted, and only for this grade")
service = (ROOT / "src/shared/core/src/edu_core/services/profiles.py").read_text(
    encoding="utf-8"
)
check("dropped subjects are archived", "archived_at = project.archived_at or now" in service)
check("returning to a group restores them", "project.archived_at = None" in service)
check("nothing is deleted", "db.delete(" not in service)
check("only the student's current grade is touched",
      "GradeSubject.grade == grade" in service)
check("onboarding itself archives, so the existing button is fixed",
      "_archive_dropped(db, user_id, grade, group_code)" in service)

projects = (ROOT / "src/shared/core/src/edu_core/services/projects.py").read_text(
    encoding="utf-8"
)
check("an archived subject is not listed", "Project.archived_at.is_(None)" in projects)

print()
print("wiping every account is guarded against doing it by accident")
router = (ROOT / "src/edu-api/routers/admin.py").read_text(encoding="utf-8")
check("a phrase must be typed, not a box ticked",
      'WIPE_PHRASE = "DELETE ALL USERS"' in router)
check("a wrong phrase deletes nothing", "Nothing was deleted." in router)
check("the count must match what the administrator was looking at",
      "expected_count" in router)
check("a mismatch is refused rather than guessed at", "status_code=409" in router)
check("only an administrator can reach it",
      "require_admin" in router.split("async def delete_all_users(")[1][:600])

admin = (ROOT / "src/shared/core/src/edu_core/services/admin.py").read_text(
    encoding="utf-8"
)
check("the administrator running it is kept",
      "User.id != keep_user_id" in admin)
check("it is one statement, so it cannot half-finish",
      "synchronize_session=False" in admin)
check("it reports what it removed", "totals" in admin)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
