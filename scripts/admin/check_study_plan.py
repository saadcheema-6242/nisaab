"""Check how a study plan divides a student's time, with no database or model.

Run with:
    python scripts/admin/check_study_plan.py

The two ways in are checked separately, because they answer different
questions: a plan on a custom topic stays inside that topic even when the
student has never practised it, and a plan with no topic covers everything they
are weak at across the syllabus.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.study_plan_blueprint import (  # noqa: E402
    ACTIONS,
    MAX_DAYS,
    MAX_HOURS,
    build,
    clamp_period,
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
print("the worst comes first")
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
print("no topic: the whole syllabus, weak outcomes only")
whole = build(SYLLABUS, RECORDS, days=5, hours_per_day=1, weak_only=True)
planned = {item.slo_code for item in whole.items}
check("only weak outcomes are planned", planned <= {"P-11-B-05", "P-11-B-06"}, str(planned))
check("the solid outcome is left alone", "P-11-C-09" not in planned)
check("unpractised outcomes are not called weak", "P-11-D-12" not in planned)
check("the weak ones are reported", set(whole.weak_codes) == {"P-11-B-05", "P-11-B-06"},
      str(whole.weak_codes))

print()
print("a custom topic: stays inside it, even with no practice history")
topic = [s for s in SYLLABUS if s["domain"] == "Waves"]
fresh = build(topic, [], days=3, hours_per_day=1, scope="Waves")
check("a never-practised topic still produces a plan", len(fresh.items) > 0, str(len(fresh.items)))
check("and only covers that topic", {i.slo_code for i in fresh.items} == {"P-11-D-12"},
      str({i.slo_code for i in fresh.items}))
check("it starts by reading, not by testing them",
      fresh.items[0].action == "read", fresh.items[0].action)

dyn = [s for s in SYLLABUS if s["domain"] == "Dynamics"]
mixed = build(dyn, RECORDS, days=5, hours_per_day=1, scope="Dynamics")
check("inside a topic the weakest outcome comes first",
      mixed.items[0].slo_code == "P-11-B-05", mixed.items[0].slo_code)
check("and an unpractised outcome in that topic is still included",
      "P-11-B-07" in {i.slo_code for i in mixed.items}, str({i.slo_code for i in mixed.items}))

print()
print("the work fits the time, and the ladder makes sense")
small = build(SYLLABUS, RECORDS, days=1, hours_per_day=0.5, weak_only=True)
check("a half-hour plan does not overrun", small.total_minutes <= 30, str(small.total_minutes))
check("it covers fewer outcomes properly rather than all of them badly",
      len({i.slo_code for i in small.items}) <= 2, str({i.slo_code for i in small.items}))

big = build(SYLLABUS, RECORDS, days=10, hours_per_day=2, weak_only=True)
check("a long plan never exceeds its budget", big.total_minutes <= 10 * 120, str(big.total_minutes))
check("no day is over its allowance",
      all(
          sum(i.minutes for i in big.items if i.day == d) <= big.minutes_per_day
          for d in {i.day for i in big.items}
      ))
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
check("it gives the real numbers", "1/8" in told, told.splitlines()[2] if len(told.splitlines()) > 2 else told)
check("it does not ask the model to decide who is weak", "decide" not in told.lower())

print()
print("nothing to plan is handled honestly")
empty = build([], [], days=5, hours_per_day=2)
check("an empty syllabus gives an empty plan", empty.items == [] and empty.days == 5)
none_weak = build(SYLLABUS, attempts("P-11-C-09", 10, 0), days=5, hours_per_day=2, weak_only=True)
check("a student with no weaknesses gets no busywork", none_weak.items == [],
      str(len(none_weak.items)))

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
