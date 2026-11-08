"""Who an account is, and what that lets them do.

Three kinds of account, and one of them is all three at once.

A student picks a year and a group at onboarding and sees that cohort.

A teacher says so at signup and then waits. Anybody can claim to be a
teacher, so the claim grants nothing at all until an administrator approves
it: not a dashboard, not a student's name, and above all not a place in the
list of people who can be put in front of a class. That last one is the
mistake this module exists to prevent. Filtering "who can teach" on the role
alone looks right and quietly offers every stranger who ticked the box.

An administrator is on the email list, and is also a student of every cohort
and a teacher. Not a fourth kind of account with its own rules: the same
student and teacher paths, with the cohort unpinned so they can study as
Grade 11 ICS one minute and Grade 12 Pre-Medical the next.

Approval is a date, not a flag, matching how a ban is already recorded on the
same table: "the dates are the whole state". A boolean beside a timestamp
drifts the first time one is written without the other.
"""

from datetime import datetime

STUDENT = "student"
TEACHER = "teacher"
ROLES = (STUDENT, TEACHER)

# What a teacher is asked at signup. Kept here so the page and the server
# cannot disagree about what a valid application looks like.
MAX_SCHOOL = 120
MAX_HEADLINE = 120
MIN_SUBJECTS = 1
MAX_SUBJECTS = 5


class RoleError(ValueError):
    """An account cannot be what it is being asked to be."""


def check_role(role: str) -> str:
    if role not in ROLES:
        raise RoleError("An account is either a student or a teacher.")
    return role


def is_approved_teacher(role: str, approved_at: datetime | None) -> bool:
    """The only question worth asking before trusting a teacher claim.

    Both halves matter. The role says what they asked to be; the date says an
    administrator agreed. Anything that reads one without the other is a hole.
    """
    return role == TEACHER and approved_at is not None


def is_pending_teacher(role: str, approved_at: datetime | None) -> bool:
    return role == TEACHER and approved_at is None


def can_teach(role: str, approved_at: datetime | None, is_admin: bool = False) -> bool:
    """Whether this account may be scheduled to take a class.

    An administrator can, without being approved by anyone: they are the
    person who does the approving, and requiring them to approve themselves
    would be a loop with no way in on a fresh system.
    """
    return is_admin or is_approved_teacher(role, approved_at)


def needs_onboarding(
    role: str,
    is_admin: bool,
    has_profile: bool,
    approved_at: datetime | None,
) -> str | None:
    """Where this account has to go before it can use the app.

    Returns a route, or None when they are free to carry on.

    An administrator is sent to onboarding exactly once, to pick a cohort to
    start in, and never blocked by approval. Without a profile the subject
    pages have nothing to read and fail the way they did on 7 November, with
    "Failed to load your subjects" and no clue why.
    """
    if is_admin:
        return None if has_profile else "/onboarding"
    if role == TEACHER:
        # A pending teacher is held before onboarding, not after. There is
        # nothing to set up until somebody says they are a teacher, and
        # walking them through a setup that may be refused is a small cruelty.
        return None if approved_at is not None else "/awaiting-approval"
    return None if has_profile else "/onboarding"


def check_subjects(codes: list[str], known: list[str]) -> list[str]:
    """The subjects a teacher says they teach.

    Deduplicated and ordered as given, so the list reads back the way it was
    entered rather than in whatever order a set happens to produce.
    """
    seen: list[str] = []
    for raw in codes or []:
        code = (raw or "").strip().upper()
        if not code:
            continue
        if code not in known:
            raise RoleError(f"{code} is not an FSc subject.")
        if code not in seen:
            seen.append(code)
    if len(seen) < MIN_SUBJECTS:
        raise RoleError("Choose at least one subject you teach.")
    if len(seen) > MAX_SUBJECTS:
        raise RoleError(f"That is more than the {MAX_SUBJECTS} FSc subjects.")
    return seen


def check_grades(grades: list[int]) -> list[int]:
    wanted = sorted({int(g) for g in (grades or [])})
    if not wanted:
        raise RoleError("Choose at least one year you teach.")
    if any(g not in (11, 12) for g in wanted):
        raise RoleError("FSc is years 11 and 12.")
    return wanted


def check_text(value: str | None, limit: int, what: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) > limit:
        raise RoleError(f"Keep {what} under {limit} characters.")
    return text


def teaches(
    subject_code: str,
    grade: int,
    subjects: list[str],
    grades: list[int],
    is_admin: bool = False,
) -> bool:
    """Whether a teacher may schedule this particular class.

    Checked when a teacher schedules their own, so that approval to teach
    Physics does not become approval to teach everything. An administrator
    schedules whatever they like.
    """
    if is_admin:
        return True
    return (subject_code or "").upper() in (subjects or []) and grade in (grades or [])
