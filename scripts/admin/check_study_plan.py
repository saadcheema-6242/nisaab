"""Check how a study plan divides a student's time, with no database or model.

Run with:
    python scripts/admin/check_study_plan.py

The two ways in are checked separately, because they answer different
questions. A plan on a topic teaches that topic from the syllabus and never
looks at the student's practice record. A plan on their weak topics is nothing
but that record.

Two faults are pinned here that a student actually hit. A plan asked for over
thirty days at five hours a day came back as one day and three steps, because
the schedule's size came from how many outcomes the topic held and ignored the
period entirely. And a plan asked for on a topic opened by reporting that the
student had no practice records on that topic - true, and not an answer to what
they asked.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.study_plan_blueprint import (  # noqa: E402
    ACTIONS,
    MAX_DAYS,
    MAX_HOURS,
    MAX_PASSES,
    TOPIC,
    WEAK,
    build,
    clamp_period,
    order_for,
    outcomes_from,
    rank,
    summarise,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


SYLLABUS = [
    {"code": "P-11-A-01", "domain": "Measurements", "description": "Estimate quantities"},
    {"code": "P-11-B-05", "domain": "Dynamics", "description": "Apply Newton's laws"},
    {"code": "P-11-B-06", "domain": "Dynamics", "description": "Describe air resistance"},
    {"code": "P-11-B-07", "domain": "Dynamics", "description": "Projectile motion"},
    {"code": "P-11-C-09", "domain": "Work and Energy", "description": "Work done"},
    {"code": "P-11-D-12", "domain": "Waves", "description": "Wave speed"},
]


def attempts(code: str, right: int, wrong: int) -> list[dict]:
    return [{"slo_code": code, "was_correct": True}] * right + [
        {"slo_code": code, "was_correct": False}
    ] * wrong


# B-05 is badly wrong, B-06 is shaky, C-09 is fine, the rest never attempted.
RECORDS = (
    attempts("P-11-B-05", 1, 7)
    + attempts("P-11-B-06", 3, 3)
    + attempts("P-11-C-09", 9, 1)
)


def day_minutes(plan) -> dict[int, int]:
    out: dict[int, int] = {}
    for item in plan.items:
        out[item.day] = out.get(item.day, 0) + item.minutes
    return out


print("time asked for becomes a budget that can be kept")
check("a week at 2 hours is 7 days x 120 min", clamp_period(7, 2) == (7, 120), str(clamp_period(7, 2)))
check("nothing given falls back to a sensible default", clamp_period(None, None) == (7, 120),
      str(clamp_period(None, None)))
check("half an hour a day is allowed", clamp_period(3, 0.5) == (3, 30), str(clamp_period(3, 0.5)))
check("a year at 20 hours a day is capped, not refused",
      clamp_period(900, 20) == (MAX_DAYS, int(MAX_HOURS * 60)), str(clamp_period(900, 20)))
check("zero days is not a plan", clamp_period(0, 2)[0] >= 1, str(clamp_period(0, 2)))

print()
print("weakness is measured from practice, not guessed")
outcomes = {o.code: o for o in outcomes_from(SYLLABUS, RECORDS)}
check("every outcome in scope is present", len(outcomes) == len(SYLLABUS), str(len(outcomes)))
check("B-05 is counted correctly", (outcomes["P-11-B-05"].correct, outcomes["P-11-B-05"].attempts) == (1, 8),
      f"{outcomes['P-11-B-05'].correct}/{outcomes['P-11-B-05'].attempts}")
check("B-05 is struggling", outcomes["P-11-B-05"].standing == "struggling", outcomes["P-11-B-05"].standing)
check("B-06 is weak, not struggling", outcomes["P-11-B-06"].standing == "weak", outcomes["P-11-B-06"].standing)
check("C-09 is solid", outcomes["P-11-C-09"].standing == "solid", outcomes["P-11-C-09"].standing)
check("an unattempted outcome is unknown, not weak",
      outcomes["P-11-D-12"].standing == "unknown" and not outcomes["P-11-D-12"].is_weak)
check("an unattempted outcome has no accuracy, rather than 0%",
      outcomes["P-11-D-12"].accuracy is None, str(outcomes["P-11-D-12"].accuracy))

stray = outcomes_from(SYLLABUS, [{"slo_code": "C-12-Z-99", "was_correct": False}])
check("practice on an outcome outside the scope is ignored",
      all(o.attempts == 0 for o in stray))

print()
print("in weak-topics mode, the worst comes first")
order = [o.code for o in rank(list(outcomes.values()))]
check("the struggling outcome leads", order[0] == "P-11-B-05", order[0])
check("the weak one is next", order[1] == "P-11-B-06", order[1])
check("the solid one comes last", order[-1] == "P-11-C-09", order[-1])
check("unattempted outcomes sit between them",
      order.index("P-11-D-12") > 1 and order.index("P-11-D-12") < order.index("P-11-C-09"),
      str(order))

# One unlucky attempt should not outrank a measured failure.
thin = outcomes_from(SYLLABUS, attempts("P-11-A-01", 0, 1) + attempts("P-11-B-05", 1, 7))
thin_order = [o.code for o in rank(thin)]
check("a single bad attempt does not outrank eight",
      thin_order.index("P-11-B-05") < thin_order.index("P-11-A-01"), str(thin_order[:3]))

print()
print("weak-topics mode: every weak outcome, across the whole syllabus")
whole = build(SYLLABUS, RECORDS, days=5, hours_per_day=1, mode=WEAK)
planned = {item.slo_code for item in whole.items}
check("only weak outcomes are planned", planned <= {"P-11-B-05", "P-11-B-06"}, str(planned))
check("every weak outcome is covered, not just the worst",
      planned == {"P-11-B-05", "P-11-B-06"}, str(planned))
check("the solid outcome is left alone", "P-11-C-09" not in planned)
check("unpractised outcomes are not called weak", "P-11-D-12" not in planned)
check("the weak ones are reported", set(whole.weak_codes) == {"P-11-B-05", "P-11-B-06"},
      str(whole.weak_codes))
check("a weak plan says why each step is there",
      all(i.standing in ("struggling", "weak") for i in whole.items),
      str({i.standing for i in whole.items}))
check("a named topic is ignored in weak mode",
      order_for(list(outcomes.values()), WEAK) == rank(list(outcomes.values()), weak_only=True))

print()
print("topic mode: teaches the topic, and says nothing about their record")
dyn = [s for s in SYLLABUS if s["domain"] == "Dynamics"]
topic_plan = build(dyn, RECORDS, days=6, hours_per_day=1, mode=TOPIC, scope="Dynamics")
check("a topic plan covers the whole topic",
      {i.slo_code for i in topic_plan.items} == {"P-11-B-05", "P-11-B-06", "P-11-B-07"},
      str({i.slo_code for i in topic_plan.items}))
check("it follows syllabus order, not the order of their mistakes",
      topic_plan.items[0].slo_code == "P-11-B-05"
      and [i.slo_code for i in topic_plan.items if i.pass_index == 0][:4].count("P-11-B-05") > 0,
      topic_plan.items[0].slo_code)
check("no step claims anything about their practice",
      all(i.standing == "" for i in topic_plan.items),
      str({i.standing for i in topic_plan.items}))
check("every outcome in the topic starts by being read",
      all(
          next(i.action for i in topic_plan.items if i.slo_code == code) == "read"
          for code in ("P-11-B-05", "P-11-B-06", "P-11-B-07")
      ))

told_topic = summarise(topic_plan)
for leak in ("Practice so far", "correct", "struggling", "Never practised", "%"):
    check(f"a topic plan is never told about {leak!r}", leak not in told_topic,
          told_topic)
check("it is told what the topic covers", "Outcomes covered:" in told_topic, told_topic)

# The topic a student has never touched: the case that produced the bad plan.
waves = [s for s in SYLLABUS if s["domain"] == "Waves"]
fresh = build(waves, [], days=3, hours_per_day=1, mode=TOPIC, scope="Waves")
check("a never-practised topic still produces a plan", len(fresh.items) > 0, str(len(fresh.items)))
check("and only covers that topic", {i.slo_code for i in fresh.items} == {"P-11-D-12"},
      str({i.slo_code for i in fresh.items}))
check("it starts by reading, not by testing them",
      fresh.items[0].action == "read", fresh.items[0].action)

print()
print("the period asked for is the period delivered")
# The student's own words: thirty days, five hours a day, on one narrow topic.
long_plan = build(waves, [], days=30, hours_per_day=5, mode=TOPIC, scope="data science")
check("a thirty-day plan is not one day", long_plan.days > 1, str(long_plan.days))
check("what was asked for is remembered", long_plan.asked_days == 30, str(long_plan.asked_days))
check("the days it reports are the days it actually fills",
      long_plan.days == max(i.day for i in long_plan.items), str(long_plan.days))
check("and its work is spread over many days, not dumped on day one",
      len({i.day for i in long_plan.items}) > 1,
      str(sorted({i.day for i in long_plan.items})))
check("no day is skipped",
      {i.day for i in long_plan.items} == set(range(1, long_plan.days + 1)),
      str(sorted({i.day for i in long_plan.items})))
check("asking for longer gives more work, not the same work",
      len(long_plan.items) > len(fresh.items),
      f"{len(long_plan.items)} vs {len(fresh.items)}")
check("the extra work is revision of the same topic, not invented content",
      {i.slo_code for i in long_plan.items} == {"P-11-D-12"},
      str({i.slo_code for i in long_plan.items}))
check("it goes over the topic more than once", long_plan.passes > 1, str(long_plan.passes))
check("but not without limit", long_plan.passes <= MAX_PASSES, str(long_plan.passes))
check("a plan smaller than the time offered knows it", long_plan.is_light)
check("and the model is told to say so, with what was asked for",
      "30 days" in summarise(long_plan) and "padded" in summarise(long_plan),
      summarise(long_plan))
check("a plan that uses its time is not called light",
      not build(SYLLABUS, [], days=2, hours_per_day=1, mode=TOPIC).is_light)

# Same scope, two periods: the bug was that these came out identical.
short_same = build(waves, [], days=1, hours_per_day=1, mode=TOPIC, scope="Waves")
check("a one-day plan and a thirty-day plan differ",
      len(short_same.items) != len(long_plan.items)
      or short_same.days != long_plan.days,
      f"{len(short_same.items)}/{short_same.days} vs {len(long_plan.items)}/{long_plan.days}")

wide = build(SYLLABUS, [], days=20, hours_per_day=3, mode=TOPIC, scope="whole syllabus")
check("a wide scope over three weeks fills most of the days",
      len({i.day for i in wide.items}) >= 15, str(len({i.day for i in wide.items})))
check("and never puts more on a day than the student offered",
      all(m <= wide.asked_minutes_per_day for m in day_minutes(wide).values()),
      str(day_minutes(wide)))

# The case that broke it: enough work to use the budget exactly. Packing a day
# always wastes a little of it, so the leftover used to land on the last day.
for period, hours in ((7, 2), (5, 1), (14, 3), (3, 0.5), (21, 4)):
    packed = build(SYLLABUS, [], days=period, hours_per_day=hours, mode=TOPIC)
    worst = max(day_minutes(packed).values(), default=0)
    check(
        f"{period} days at {hours}h: no day runs over the limit",
        worst <= packed.asked_minutes_per_day
        or len([i for i in packed.items if i.day == max(day_minutes(packed))]) == 1,
        f"{worst} min vs {packed.asked_minutes_per_day}: {day_minutes(packed)}",
    )

print()
print("a revisit is not the same sitting again")
revisits = [i for i in long_plan.items if i.pass_index > 0]
check("there are revisits", len(revisits) > 0, str(len(revisits)))
check("the first sweep comes before any revisit",
      max((i.day for i in long_plan.items if i.pass_index == 0), default=0)
      <= min(i.day for i in revisits))
check("a revisit lands on a later day than the first sweep of that outcome",
      all(
          i.day > min(j.day for j in long_plan.items if j.slo_code == i.slo_code)
          for i in revisits
      ))
check("revisits are numbered in order",
      [i.pass_index for i in long_plan.items] == sorted(i.pass_index for i in long_plan.items),
      str([i.pass_index for i in long_plan.items]))

print()
print("the work fits the time, and the ladder makes sense")
small = build(SYLLABUS, RECORDS, days=1, hours_per_day=0.5, mode=WEAK)
check("a half-hour plan does not overrun", small.total_minutes <= 30, str(small.total_minutes))
check("it covers fewer outcomes properly rather than all of them badly",
      len({i.slo_code for i in small.items}) <= 2, str({i.slo_code for i in small.items}))

big = build(SYLLABUS, RECORDS, days=10, hours_per_day=2, mode=WEAK)
check("a long plan never exceeds its budget", big.total_minutes <= 10 * 120, str(big.total_minutes))
check("no day holds more than the plan says a day holds",
      all(m <= big.minutes_per_day for m in day_minutes(big).values()),
      str(day_minutes(big)))
check("no day holds more than the student offered",
      all(m <= big.asked_minutes_per_day for m in day_minutes(big).values()),
      str(day_minutes(big)))
check("days start at 1 and do not exceed the period",
      all(1 <= i.day <= big.days for i in big.items))

struggling = [i for i in big.items if i.slo_code == "P-11-B-05"]
check("a struggling outcome is sent back to the explanation first",
      struggling[0].action == "read", struggling[0].action)
weak_items = [i for i in big.items if i.slo_code == "P-11-B-06"]
check("a merely weak one goes straight to practice",
      weak_items[0].action != "read", weak_items[0].action)
check("every item carries the outcome it assesses",
      all(i.slo_code for i in big.items))
check("quizzes carry a target the student can check against",
      all(i.target == ACTIONS["quiz"]["target"] for i in big.items if i.action == "quiz"))
check("reading carries no score target", all(i.target is None for i in big.items if i.action == "read"))

print()
print("what the model is told is fact, not inference")
told = summarise(big)
check("it names the scope and the budget", "Scope:" in told and "Time:" in told)
check("it gives the real numbers", "1/8" in told, told)
check("it does not ask the model to decide who is weak", "decide" not in told.lower())

print()
print("nothing to plan is handled honestly")
empty = build([], [], days=5, hours_per_day=2)
check("an empty syllabus gives an empty plan", empty.items == [] and empty.days == 5)
none_weak = build(SYLLABUS, attempts("P-11-C-09", 10, 0), days=5, hours_per_day=2, mode=WEAK)
check("a student with no weaknesses gets no busywork", none_weak.items == [],
      str(len(none_weak.items)))
check("an empty plan is not called light", not empty.is_light)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
