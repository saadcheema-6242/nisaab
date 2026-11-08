"""Check the weekly session rules without a database.

The three things that can go wrong here are a link pointing somewhere it
should not, a join button appearing at the wrong moment, and a session shown
on the wrong day because the clock was read in UTC. None of them need a
database to provoke, and all of them are awkward to provoke through one.

Run: python scripts/admin/check_weekly_session.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.weekly_session import (  # noqa: E402
    JOIN_OPENS_MINUTES,
    MEETING_HOSTS,
    SessionError,
    can_join,
    check_duration,
    check_link,
    check_title,
    groups_for,
    is_joinable,
    local_day,
    next_session,
    state,
    upcoming,
    when_in_words,
)

failures: list[str] = []


def check(label: str, ok: bool, note: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"  -- {note}" if note else ""))
    if not ok:
        failures.append(label)


def refuses(label: str, url: str) -> None:
    try:
        check_link(url)
    except SessionError:
        check(label, True)
        return
    check(label, False, "it was accepted")


UTC = timezone.utc


print("meeting links that must be accepted")
for good in (
    "https://meet.google.com/abc-defg-hij",
    "https://us02web.zoom.us/j/1234567890",
    "https://zoom.us/j/1234567890?pwd=xyz",
    "https://teams.microsoft.com/l/meetup-join/19%3ameeting",
    "https://acme.webex.com/meet/room",
):
    try:
        check(good[:52], check_link(good) == good)
    except SessionError as exc:
        check(good[:52], False, str(exc))

print()
print("and links that must not be")
refuses("http, not https", "http://meet.google.com/abc-defg-hij")
refuses("a host nobody is expecting", "https://bit.ly/free-physics")
# The one a person cannot see. The browser reads the host after the @.
refuses(
    "the credentials trick: meet.google.com@elsewhere",
    "https://meet.google.com@elsewhere.example/join",
)
# Looks like a subdomain, is not one.
refuses("a lookalike domain", "https://zoom.us.elsewhere.example/j/1")
refuses("a suffix that merely ends the same way", "https://notzoom.us/j/1")
refuses("nothing at all", "")
refuses("whitespace only", "   ")
refuses("not a link", "ask me on whatsapp")
refuses("javascript", "javascript:alert(1)")
refuses("a trailing dot evading the match", "https://zoom.us.evil.example./j/1")

print()
print("who a session is for: the subject decides, never the group")
check("Physics brings all three groups together",
      sorted(groups_for("PHY")) == ["ICS", "PRE_ENG", "PRE_MED"],
      str(sorted(groups_for("PHY"))))
check("Chemistry is Pre-Medical and Pre-Engineering",
      sorted(groups_for("CHEM")) == ["PRE_ENG", "PRE_MED"], str(sorted(groups_for("CHEM"))))
check("Maths is Pre-Engineering and ICS",
      sorted(groups_for("MATH")) == ["ICS", "PRE_ENG"], str(sorted(groups_for("MATH"))))
check("Biology is Pre-Medical alone", groups_for("BIO") == ["PRE_MED"], str(groups_for("BIO")))
check("Computer Science is ICS alone", groups_for("CS") == ["ICS"], str(groups_for("CS")))
check("a subject nobody studies has no audience", groups_for("URDU") == [])
check("the code is not case sensitive", groups_for("phy") == groups_for("PHY"))

check("an ICS student is invited to Physics", can_join("ICS", 11, "PHY", 11))
check("and to Maths", can_join("ICS", 11, "MATH", 11))
check("but not to Biology, which they do not study",
      not can_join("ICS", 11, "BIO", 11),
      "a student would see a class they cannot follow")
check("a Pre-Medical student is not invited to Computer Science",
      not can_join("PRE_MED", 11, "CS", 11))
check("a first year is not shown a second year class",
      not can_join("PRE_MED", 11, "PHY", 12),
      "grade has to match as well as subject")
check("a second year is shown their own",
      can_join("PRE_MED", 12, "PHY", 12))
check("an unknown group is invited to nothing",
      not can_join("", 11, "PHY", 11))

print()
print("the title and the length of a class")
check("a sensible duration is kept", check_duration(60) == 60)
for bad, why in ((0, "zero"), (5, "five minutes"), (600, "ten hours")):
    try:
        check_duration(bad)
        check(f"{why} is refused", False, "it was accepted")
    except SessionError:
        check(f"{why} is refused", True)
check("the shortest allowed is kept", check_duration(10) == 10)
check("the longest allowed is kept", check_duration(240) == 240)
check("a title is trimmed", check_title("  Waves revision  ") == "Waves revision")
try:
    check_title("   ")
    check("an empty title is refused", False, "it was accepted")
except SessionError:
    check("an empty title is refused", True)

print()
print("when the join button appears")
start = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)   # 5pm in Pakistan
DUR = 60
cases = [
    (start - timedelta(days=1), "upcoming", "a day before"),
    (start - timedelta(minutes=JOIN_OPENS_MINUTES + 1), "upcoming", "sixteen minutes before"),
    (start - timedelta(minutes=JOIN_OPENS_MINUTES), "open", "exactly the quarter hour before"),
    (start - timedelta(minutes=1), "open", "a minute before"),
    (start, "open", "on the hour"),
    (start + timedelta(minutes=59), "open", "a minute before the end"),
    (start + timedelta(minutes=60), "ended", "exactly at the end"),
    (start + timedelta(days=1), "ended", "the next day"),
]
for now, want, label in cases:
    got = state(start, DUR, now)
    check(f"{label}: {want}", got == want, got)

check("the link is handed over only while it is open",
      is_joinable(start, DUR, start) is True
      and is_joinable(start, DUR, start - timedelta(hours=2)) is False
      and is_joinable(start, DUR, start + timedelta(hours=2)) is False)

print()
print("the student's own day, not the server's")
# 9pm in Lahore on the 12th is 16:00 UTC on the 12th: same day either way.
check("an evening class is on the evening's date",
      local_day(datetime(2026, 11, 12, 16, 0, tzinfo=UTC)) == datetime(2026, 11, 12).date())
# 2am in Lahore on the 13th is 21:00 UTC on the 12th. UTC says the 12th and
# would put an early class on the wrong day in the timetable.
check("a very early class belongs to the day the student sees",
      local_day(datetime(2026, 11, 12, 21, 0, tzinfo=UTC)) == datetime(2026, 11, 13).date(),
      str(local_day(datetime(2026, 11, 12, 21, 0, tzinfo=UTC))))
check("a naive time is read as UTC rather than crashing",
      local_day(datetime(2026, 11, 12, 16, 0)) == datetime(2026, 11, 12).date())

print()
print("how it reads to a student")
now = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)      # 11am in Pakistan
check("today", when_in_words(start, now) == "Today at 5:00 pm",
      when_in_words(start, now))
check("tomorrow",
      when_in_words(start + timedelta(days=1), now) == "Tomorrow at 5:00 pm",
      when_in_words(start + timedelta(days=1), now))
check("further off says the date",
      "Nov" in when_in_words(start + timedelta(days=5), now),
      when_in_words(start + timedelta(days=5), now))
# 8:30pm local, the hour most revision actually happens.
evening = datetime(2026, 11, 12, 15, 30, tzinfo=UTC)
check("the evening reads as pm", when_in_words(evening, now) == "Today at 8:30 pm",
      when_in_words(evening, now))
# Midnight and noon are where a 12-hour clock usually breaks.
check("midnight is 12 am, not 0 am",
      when_in_words(datetime(2026, 11, 12, 19, 0, tzinfo=UTC), now).endswith("12:00 am"),
      when_in_words(datetime(2026, 11, 12, 19, 0, tzinfo=UTC), now))
check("noon is 12 pm, not 0 pm",
      when_in_words(datetime(2026, 11, 12, 7, 0, tzinfo=UTC), now) == "Today at 12:00 pm",
      when_in_words(datetime(2026, 11, 12, 7, 0, tzinfo=UTC), now))

print()
print("the timetable")
def made(day_offset, hours=0, title="X"):
    return {
        "title": title,
        "starts_at": start + timedelta(days=day_offset, hours=hours),
        "duration_minutes": DUR,
    }

sessions = [made(3, title="C"), made(-2, title="gone"), made(0, title="A"), made(1, title="B")]
seen = upcoming(sessions, now)
check("the one that already finished is dropped",
      all(s["title"] != "gone" for s in seen), str([s["title"] for s in seen]))
check("soonest first", [s["title"] for s in seen] == ["A", "B", "C"],
      str([s["title"] for s in seen]))
check("a limit is honoured", len(upcoming(sessions, now, limit=2)) == 2)
check("the next one is the soonest", next_session(sessions, now)["title"] == "A")
check("nothing scheduled, nothing next", next_session([], now) is None)
check("everything finished, nothing next",
      next_session([made(-5)], now) is None)
# A session running right now is still "next": a teacher opening the
# dashboard mid-class should see the class they are in, not the one after.
check("a session in progress is still the next one",
      next_session([made(0), made(1)], start + timedelta(minutes=10))["starts_at"] == start)

print()
print(f"{len(MEETING_HOSTS)} meeting hosts allowed")
if failures:
    print(f"\n{len(failures)} failed: {failures[0]}")
    sys.exit(1)
print("\nall checks passed")
