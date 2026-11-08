"""Weekly class sessions: when one can be joined, and where it may point.

An administrator schedules a session for a subject and a cohort, names a
teacher, and pastes a meeting link. The teacher sees their upcoming sessions.
Students in that grade and group see theirs and join.

Three rules live here, away from the database, because each has edge cases
that are tedious to reach through a service and trivial to reach directly.

The link is checked against a list of meeting hosts. An administrator pasting
a URL that every student in a cohort will click is a phishing hole even when
the administrator is trustworthy: one mistyped domain, one copied link from
the wrong tab, and a hundred students are sent somewhere nobody intended.
The check also rejects the credential trick, where a link reading
"https://meet.google.com@elsewhere.example/" looks right to a person and
resolves to elsewhere.example for a browser.

The link is revealed only around the start time. Without that, the first
student to open the page on Monday gets the link for Thursday's class, and
either sits in an empty call or passes it on. Before the window they see when
it starts; during it they see the button.

Times are stored in UTC and shown in the student's own day. Pakistan is five
hours ahead, so a session at 17:00 local is 12:00 stored, and a list sorted
or grouped in the wrong one of those puts the evening class on the wrong day.
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# One definition, shared with the progress trend. Two copies of a timezone
# offset is how the graph and the heading came to disagree; the same mistake
# here would put a session on the wrong day for everyone.
from edu_core.group_change import GROUP_SUBJECTS
from edu_core.progress_trend import PAKISTAN_OFFSET_HOURS

# Hosts a meeting link may point at. Subdomains count, so us02web.zoom.us is
# accepted while zoom.us.evil.example is not.
MEETING_HOSTS = (
    "meet.google.com",
    "zoom.us",
    "teams.microsoft.com",
    "teams.live.com",
    "webex.com",
)

# How long before the start the join button appears.
JOIN_OPENS_MINUTES = 15

MIN_DURATION_MINUTES = 10
MAX_DURATION_MINUTES = 240
MAX_TITLE = 120


class SessionError(ValueError):
    """A session could not be scheduled as described."""


def check_link(url: str) -> str:
    """Return the link if it points at a real meeting host, else raise.

    Rejects anything that is not https, any host outside the list, and any
    link carrying credentials before the host.
    """
    url = (url or "").strip()
    if not url:
        raise SessionError("A meeting link is needed so students can join.")
    if len(url) > 500:
        raise SessionError("That meeting link is too long to be real.")

    try:
        parsed = urlparse(url)
    except ValueError as exc:  # pragma: no cover - urlparse is forgiving
        raise SessionError("That does not look like a link.") from exc

    if parsed.scheme != "https":
        raise SessionError("A meeting link must start with https://")
    # urlparse already resolves user@host correctly, but refusing it outright
    # keeps the rule obvious to whoever reads this next.
    if "@" in (parsed.netloc or ""):
        raise SessionError("That link is disguised and will not be accepted.")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise SessionError("That link has no address in it.")
    if not any(host == known or host.endswith("." + known) for known in MEETING_HOSTS):
        allowed = ", ".join(MEETING_HOSTS)
        raise SessionError(f"Use a link from one of: {allowed}")
    return url


def check_duration(minutes: int) -> int:
    """A session has to be long enough to be worth joining and short enough to end."""
    if minutes < MIN_DURATION_MINUTES:
        raise SessionError(f"A session must run at least {MIN_DURATION_MINUTES} minutes.")
    if minutes > MAX_DURATION_MINUTES:
        raise SessionError(f"A session cannot run longer than {MAX_DURATION_MINUTES // 60} hours.")
    return minutes


def check_title(title: str) -> str:
    title = (title or "").strip()
    if not title:
        raise SessionError("Give the session a title students will recognise.")
    if len(title) > MAX_TITLE:
        raise SessionError(f"Keep the title under {MAX_TITLE} characters.")
    return title


def groups_for(subject_code: str) -> list[str]:
    """Which groups study this subject, and may therefore join its session.

    A session is a grade and a subject, never a group. Physics is taught to
    all three groups, so one Physics XI session serves Pre-Medical,
    Pre-Engineering and ICS together; Biology serves only Pre-Medical.
    Putting a group on the session would have meant scheduling the same
    Physics class three times and splitting the students who should be in it
    together.

    Derived from the mapping the rest of the app already uses, so a change to
    what a group studies cannot leave the timetable behind.
    """
    code = (subject_code or "").upper()
    return [group for group, subjects in GROUP_SUBJECTS.items() if code in subjects]


def can_join(group_code: str, student_grade: int, subject_code: str, grade: int) -> bool:
    """Whether this student's timetable should contain this session."""
    return student_grade == grade and (subject_code or "").upper() in GROUP_SUBJECTS.get(
        (group_code or "").upper(), []
    )


def ends_at(starts_at: datetime, duration_minutes: int) -> datetime:
    return starts_at + timedelta(minutes=duration_minutes)


def opens_at(starts_at: datetime) -> datetime:
    return starts_at - timedelta(minutes=JOIN_OPENS_MINUTES)


def state(starts_at: datetime, duration_minutes: int, now: datetime) -> str:
    """One of 'upcoming', 'open', 'ended'.

    'open' covers the quarter hour before the start as well as the session
    itself, so a student who arrives early is let in rather than told to come
    back. 'ended' is the only state in which the session leaves the list.
    """
    if now >= ends_at(starts_at, duration_minutes):
        return "ended"
    if now >= opens_at(starts_at):
        return "open"
    return "upcoming"


def is_joinable(starts_at: datetime, duration_minutes: int, now: datetime) -> bool:
    """Whether the link may be handed to a student right now."""
    return state(starts_at, duration_minutes, now) == "open"


def local_day(moment: datetime, offset_hours: int = PAKISTAN_OFFSET_HOURS):
    """The calendar day a moment falls on where the students are."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (moment.astimezone(timezone.utc) + timedelta(hours=offset_hours)).date()


def when_in_words(
    starts_at: datetime,
    now: datetime,
    offset_hours: int = PAKISTAN_OFFSET_HOURS,
) -> str:
    """How a student would say it: 'Today at 5:00 pm', 'Thu 13 Nov, 5:00 pm'.

    Worked out in the student's own day rather than UTC. A class at 17:00 in
    Lahore is stored at 12:00, and a naive comparison would call an evening
    session tomorrow's for anyone looking at it after 7pm.
    """
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    shifted = starts_at.astimezone(timezone.utc) + timedelta(hours=offset_hours)
    hour = shifted.hour % 12 or 12
    suffix = "am" if shifted.hour < 12 else "pm"
    clock = f"{hour}:{shifted.minute:02d} {suffix}"

    days = (local_day(starts_at, offset_hours) - local_day(now, offset_hours)).days
    if days == 0:
        return f"Today at {clock}"
    if days == 1:
        return f"Tomorrow at {clock}"
    if days == -1:
        return f"Yesterday at {clock}"
    return f"{shifted.strftime('%a %-d %b') if _supports_dash() else shifted.strftime('%a %d %b')}, {clock}"


def _supports_dash() -> bool:
    """%-d strips the leading zero on Linux and raises on Windows."""
    try:
        datetime(2026, 11, 3).strftime("%-d")
    except ValueError:
        return False
    return True


def upcoming(sessions: list[dict], now: datetime, limit: int | None = None) -> list[dict]:
    """The sessions still worth showing, soonest first.

    Each session is a dict carrying at least starts_at and duration_minutes.
    Ended ones are dropped: a timetable of classes that already happened is
    not a timetable.
    """
    live = [
        s
        for s in sessions
        if state(s["starts_at"], s["duration_minutes"], now) != "ended"
    ]
    live.sort(key=lambda s: s["starts_at"])
    return live[:limit] if limit else live


def next_session(sessions: list[dict], now: datetime) -> dict | None:
    """The one to put at the top of a teacher's dashboard."""
    soon = upcoming(sessions, now, limit=1)
    return soon[0] if soon else None
