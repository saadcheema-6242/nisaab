"""What changes when a student changes group, and what must not.

A group decides which papers a student sits: Pre-Medical takes Biology,
Pre-Engineering and ICS take Mathematics, only ICS takes Computer Science. So
changing group adds subjects and drops others.

Onboarding only ever added. Run it twice with different groups and the student
kept every subject either group had ever included: an ICS student carrying
Chemistry and Biology they will never sit, counted in their mastery and
scheduled into their study plans.

Two rules make this safe, and they are easy to get the wrong way round:

- A dropped subject is hidden, never deleted. Somebody who spent a month on
  Chemistry notes before switching should not lose them to a dropdown, and
  switching back must bring the work with it.
- Only workspaces for the student's *current grade* are touched. Moving from
  XI to XII is not dropping anything, and a rule that archived by subject
  alone would quietly hide last year's work the first time somebody moved up.

Pure functions of the codes involved, so both rules can be checked without a
database.
"""

GROUP_SUBJECTS = {
    "PRE_MED": ["PHY", "CHEM", "BIO"],
    "PRE_ENG": ["PHY", "CHEM", "MATH"],
    # General Science / Computer Science group as offered by FBISE for FSc
    "ICS": ["PHY", "MATH", "CS"],
}

GROUP_NAMES = {
    "PRE_MED": "Pre-Medical",
    "PRE_ENG": "Pre-Engineering",
    "ICS": "ICS (Computer Science)",
}


def subjects_for(group_code: str) -> list[str]:
    """The subject codes this group studies, in the order they are shown."""
    return list(GROUP_SUBJECTS.get(group_code, []))


def is_group(group_code: str) -> bool:
    return group_code in GROUP_SUBJECTS


def plan_change(
    old_group: str | None, new_group: str
) -> tuple[list[str], list[str], list[str]]:
    """What a move from one group to another does: kept, added, dropped.

    ``dropped`` is what the student stops studying, and is only ever hidden.
    A move to the same group changes nothing at all, which matters: a student
    who opens the setting and picks what they already have must not have their
    subjects rebuilt underneath them.
    """
    if not is_group(new_group):
        raise ValueError(f"{new_group!r} is not an FSc group")

    before = subjects_for(old_group) if old_group else []
    after = subjects_for(new_group)

    kept = [code for code in after if code in before]
    added = [code for code in after if code not in before]
    dropped = [code for code in before if code not in after]
    return kept, added, dropped


def describe(old_group: str | None, new_group: str) -> str:
    """What to tell the student before they commit to it.

    Names the subjects rather than counting them. "2 subjects will be hidden"
    is not something a student can check; "Chemistry and Biology" is.
    """
    _, added, dropped = plan_change(old_group, new_group)
    parts = []
    if added:
        parts.append("adds " + ", ".join(added))
    if dropped:
        parts.append(
            "hides " + ", ".join(dropped) + " (your work in them is kept)"
        )
    if not parts:
        return f"You are already in {GROUP_NAMES.get(new_group, new_group)}."
    return (
        f"Moving to {GROUP_NAMES.get(new_group, new_group)} " + " and ".join(parts) + "."
    )
