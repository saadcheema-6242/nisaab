"""Check the progress graphs: the trend, the cognitive levels and streaks.

Run with:
    python scripts/admin/check_progress_trend.py

Three things here are easy to get wrong in ways nobody notices:

A trend computed differently from the headline mastery produces a graph whose
last point disagrees with the number printed above it. So the final point is
checked against the estimator itself, not against a hand-written expectation.

A streak counted in UTC breaks for anyone revising in the evening, because
Pakistan is five hours ahead. So the boundary is tested at 9pm and at 2am
local, which are the two times a student actually practises.

A cognitive split that drops an SLO carrying two levels quietly understates
both. So that case is stated directly.

No database, no network.
"""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.mastery import estimate  # noqa: E402
from edu_core.progress_trend import (  # noqa: E402
    PAPER_WEIGHTS,
    TREND_WEEKS,
    active_days,
    answers_this_week,
    cognitive_split,
    local_day,
    streaks,
    trend,
    weakest_level,
    week_start,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


UTC = timezone.utc


def at(y, m, d, hh=12, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


print("which day an answer belongs to, where the student is")
# 21:00 in Lahore is 16:00 UTC: same day either way.
check("an evening answer is today", local_day(at(2026, 11, 8, 16, 0)) == date(2026, 11, 8))
# 02:00 in Lahore is 21:00 UTC the day before. The student lived through
# the 9th; UTC thinks it is still the 8th.
check("a late night answer is the student's day, not UTC's",
      local_day(at(2026, 11, 8, 21, 0)) == date(2026, 11, 9),
      str(local_day(at(2026, 11, 8, 21, 0))))
check("just before midnight local", local_day(at(2026, 11, 8, 18, 59)) == date(2026, 11, 8))
check("just after midnight local", local_day(at(2026, 11, 8, 19, 1)) == date(2026, 11, 9))
check("a naive time is read as UTC, not refused",
      local_day(datetime(2026, 11, 8, 16, 0)) == date(2026, 11, 8))

print()
print("weeks start on Monday")
check("Monday is its own week start", week_start(date(2026, 11, 9)) == date(2026, 11, 9))
check("Sunday belongs to the week before", week_start(date(2026, 11, 8)) == date(2026, 11, 2))
check("Wednesday", week_start(date(2026, 11, 11)) == date(2026, 11, 9))
check("across a month boundary",
      week_start(date(2026, 12, 1)) == date(2026, 11, 30),
      str(week_start(date(2026, 12, 1))))

print()
print("the trend")
check("no answers, no graph", trend([]) == [])

answers = [
    (at(2026, 9, 7), 0.0, 1.0),
    (at(2026, 9, 9), 1.0, 1.0),
    (at(2026, 9, 21), 1.0, 1.0),
    (at(2026, 10, 5), 1.0, 1.0),
    (at(2026, 11, 2), 1.0, 1.0),
]
points = trend(answers, today=date(2026, 11, 9))
check(f"it returns {TREND_WEEKS} weeks", len(points) == TREND_WEEKS, str(len(points)))
check("ending on the current week",
      points[-1]["week_start"] == "2026-11-09", points[-1]["week_start"])
check("every point has a week and a mastery",
      all("week_start" in p and "mastery" in p for p in points))
check("weeks are in order",
      [p["week_start"] for p in points] == sorted(p["week_start"] for p in points))

# The whole point: the last point must equal what the rest of the page says.
_, headline = estimate([(s, w) for _, s, w in answers])
check("the last point equals the headline mastery",
      points[-1]["mastery"] == headline,
      f"graph {points[-1]['mastery']} vs page {headline}")

print()
print("a quiet week holds its value rather than vanishing")
sparse = [(at(2026, 10, 5), 1.0, 1.0)]
held = trend(sparse, today=date(2026, 11, 9))
after = [p for p in held if p["week_start"] >= "2026-10-05"]
check("every week after the last answer is present", len(after) >= 5, str(len(after)))
check("and they all hold the same value",
      len({p["mastery"] for p in after}) == 1,
      str({p["mastery"] for p in after}))

print()
print("practice from before the window still counts")
old = [(at(2026, 1, 5), 1.0, 1.0), (at(2026, 11, 2), 1.0, 1.0)]
early = trend(old, today=date(2026, 11, 9))
check("the first point is not empty, because the student already knew it",
      early[0]["mastery"] is not None, str(early[0]))
check("attempts carry over too", early[0]["attempts"] >= 1, str(early[0]))

print()
print("improvement actually shows as improvement")
first = datetime(2026, 9, 7, 12, tzinfo=UTC)
climbing = [
    (first + timedelta(weeks=n), 0.0 if n < 3 else 1.0, 1.0) for n in range(9)
]
rising = trend(climbing, today=date(2026, 11, 9))
scored = [p["mastery"] for p in rising if p["mastery"] is not None]
check("it starts low and ends high", scored[0] < scored[-1], f"{scored[0]} -> {scored[-1]}")

print()
print("streaks")
check("nothing practised", streaks([]) == {
    "current": 0, "longest": 0, "days_practised": 0, "last_day": None})

run = [at(2026, 11, d) for d in (4, 5, 6, 7, 8)]
got = streaks(run, today=date(2026, 11, 8))
check("five days in a row", got["current"] == 5, str(got))
check("longest is five too", got["longest"] == 5, str(got))
check("days practised is five", got["days_practised"] == 5, str(got))

print()
print("today being empty does not break a streak")
# Practised up to yesterday, opened the app this morning.
got = streaks([at(2026, 11, d) for d in (5, 6, 7)], today=date(2026, 11, 8))
check("yesterday still counts as a live streak", got["current"] == 3, str(got))
# A whole day missed does break it.
got = streaks([at(2026, 11, d) for d in (5, 6, 7)], today=date(2026, 11, 9))
check("a missed day ends it", got["current"] == 0, str(got))

print()
print("a broken run keeps its record")
broken = [at(2026, 10, d) for d in (1, 2, 3, 4, 5)] + [at(2026, 11, d) for d in (7, 8)]
got = streaks(broken, today=date(2026, 11, 8))
check("current is the recent run", got["current"] == 2, str(got))
check("longest remembers the older one", got["longest"] == 5, str(got))

print()
print("twice in one day is one day")
got = streaks([at(2026, 11, 8, 6), at(2026, 11, 8, 10), at(2026, 11, 8, 15)],
              today=date(2026, 11, 8))
check("three answers, one day", got["current"] == 1 and got["days_practised"] == 1, str(got))

print()
print("a streak across a month boundary")
over = [at(2026, 10, 30), at(2026, 10, 31), at(2026, 11, 1), at(2026, 11, 2)]
got = streaks(over, today=date(2026, 11, 2))
check("October into November is unbroken", got["current"] == 4, str(got))

print()
print("the activity calendar shows the gaps, not only the good days")
cal = active_days([at(2026, 11, 8), at(2026, 11, 8), at(2026, 11, 5)],
                  today=date(2026, 11, 8))
check("it is a continuous run of days", len(cal) == 120, str(len(cal)))
check("it ends today", cal[-1]["day"] == "2026-11-08", cal[-1]["day"])
check("two answers on one day are counted together",
      cal[-1]["answers"] == 2, str(cal[-1]))
check("an empty day is present with zero",
      cal[-2]["answers"] == 0, str(cal[-2]))
check("no answers at all means no calendar", active_days([]) == [])

print()
print("this week's answers")
check("counts only this week",
      answers_this_week([at(2026, 11, 9), at(2026, 11, 10), at(2026, 11, 2)],
                        today=date(2026, 11, 9)) == 2)
check("none is zero", answers_this_week([]) == 0)

print()
print("the FBISE cognitive levels")
split = cognitive_split([
    (["K"], 0.9, 1),
    (["U"], 0.5, 1),
    (["A"], 0.2, 1),
])
by = {row["level"]: row for row in split}
check("all three levels are returned", set(by) == set(PAPER_WEIGHTS), str(set(by)))
check("Knowledge is weighted 30", by["K"]["paper_weight"] == 30)
check("Understanding 50", by["U"]["paper_weight"] == 50)
check("Application 20", by["A"]["paper_weight"] == 20)
check("the weights are the paper's, and total 100",
      sum(r["paper_weight"] for r in split) == 100)
check("mastery comes through", by["K"]["mastery"] == 0.9 and by["A"]["mastery"] == 0.2)
check("they are named for a student", by["A"]["name"] == "Application")

print()
print("an SLO that tests two levels counts towards both")
both = cognitive_split([(["K", "U"], 0.8, 1)])
by2 = {r["level"]: r for r in both}
check("Knowledge sees it", by2["K"]["mastery"] == 0.8, str(by2["K"]))
check("Understanding sees it too", by2["U"]["mastery"] == 0.8, str(by2["U"]))
check("Application does not", by2["A"]["mastery"] is None, str(by2["A"]))
check("and it is counted in both examined totals",
      by2["K"]["examined_count"] == 1 and by2["U"]["examined_count"] == 1)

print()
print("unpractised and unknown levels")
none = cognitive_split([(["K"], None, 3)])
byn = {r["level"]: r for r in none}
check("an unpractised SLO has no mastery", byn["K"]["mastery"] is None)
check("but is still counted as examined", byn["K"]["examined_count"] == 3)
check("and not as practised", byn["K"]["practised_count"] == 0)
check("an empty level list is skipped", cognitive_split([([], 0.5, 1)])[0]["mastery"] is None)
check("an unknown level is ignored",
      all(r["mastery"] is None for r in cognitive_split([(["Z"], 0.5, 1)])))
check("lower case still matches",
      {r["level"]: r for r in cognitive_split([(["u"], 0.6, 1)])}["U"]["mastery"] == 0.6)
check("nothing at all is still three rows", len(cognitive_split([])) == 3)

print()
print("which level is costing the most marks")
# Weak on Application (20% of the paper) but weaker still, in marks, on
# Understanding - because Understanding is half the paper.
worst = weakest_level(cognitive_split([
    (["K"], 0.95, 1),
    (["U"], 0.70, 1),   # 0.30 x 50 = 15 marks
    (["A"], 0.40, 1),   # 0.60 x 20 = 12 marks
]))
check("it is the one worth the most marks, not the lowest score",
      worst and worst["level"] == "U", str(worst))
check("and it says how many marks", worst and worst["marks_at_stake"] == 15, str(worst))

close = weakest_level(cognitive_split([(["K"], 0.99, 1), (["U"], 0.99, 1)]))
check("a student who is nearly there is not sent to revise", close is None, str(close))
check("nothing practised, nothing to say", weakest_level(cognitive_split([])) is None)

print()
if failures:
    print(f"{len(failures)} failed:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
