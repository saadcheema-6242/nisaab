"""Plan a board paper against the real syllabus and measure it, with no model calls.

Run with:
    python scripts/admin/check_paper_plan.py [physics-xi]

Reads the seed data a subject is loaded from, plans a paper exactly as the
worker now does, and reports what the paper would assess: how many SLOs it draws
on, how the cognitive levels fall, whether a stimulus scenario repeats, and
whether each internal choice offers comparable alternatives.

The old planner is run beside it on the same syllabus, so the numbers can be
compared with the ones a Gemini review measured on a real generated paper:
K 0%, U 45.8%, A 54.2%, two scenarios printed three times each, and the whole
paper drawn from a couple of outcomes.
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.paper_blueprint import (  # noqa: E402
    COGNITIVE_SHARE,
    assign_levels,
    mcq_pool,
    choice_pairs,
    group_by_slo,
    measure,
    off_target,
    spread,
)

SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "physics-xi"
# The full paper for a science subject: 56 straight MCQs, 6 stimulus sets of 4,
# 7 short questions and 2 long ones.
PLAN = {"mcq": 56, "stimulus": 6, "srq": 7, "erq": 2}


def load() -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    """The examined SLOs of the subject: codes, levels and which domain each is in."""
    path = ROOT / "scripts/seed/data" / f"{SUBJECT}.json"
    if not path.exists():
        available = sorted(p.stem for p in (ROOT / "scripts/seed/data").glob("*.json"))
        sys.exit(f"No seed data for {SUBJECT}. Try one of: {', '.join(available)}")
    data = json.loads(path.read_text(encoding="utf-8"))

    codes: list[str] = []
    levels: dict[str, list[str]] = {}
    domains: dict[str, str] = {}
    for slo in data.get("slos", []):
        # Only examined outcomes go in a paper; formative ones are taught and
        # checked in class, which is what the service filters on too
        if slo.get("assessment_form") != "summative":
            continue
        code = slo["code"]
        codes.append(code)
        levels[code] = list(slo.get("cognitive_levels") or [])
        domains[code] = slo.get("domain") or "?"
    return codes, levels, domains


def old_planner(codes, levels, domains):
    """What the planner did before: four SLOs for MCQs, U/A only for the rest."""
    deep = [c for c in codes if {"U", "A"} & set(levels[c])] or codes

    def old_spread(items, count):
        by_domain: dict[str, list[str]] = {}
        for code in items:
            by_domain.setdefault(domains.get(code, ""), []).append(code)
        picked: list[str] = []
        while len(picked) < count and any(by_domain.values()):
            for domain in list(by_domain):
                if by_domain[domain] and len(picked) < count:
                    picked.append(by_domain[domain].pop(0))
        while picked and len(picked) < count:  # the repeating tail
            picked.append(picked[len(picked) % len(items)] if items else picked[0])
        return picked

    stimulus = old_spread(deep, PLAN["stimulus"])
    written = old_spread([c for c in deep if c not in stimulus] or deep,
                         2 * (PLAN["srq"] + PLAN["erq"]))
    return {
        "mcq_slos": codes[:4],
        "stimulus": stimulus,
        "written_pairs": [(written[i], written[i + 1]) for i in range(0, len(written) - 1, 2)],
    }


def report(title: str, slo_count: int, total_slos: int, levels_seen, stimulus, pairs, domains):
    print(f"\n{title}")
    print(f"  SLOs the MCQs draw on      : {slo_count} of {total_slos}")
    share = measure(levels_seen)
    for level in ("K", "U", "A"):
        target = COGNITIVE_SHARE[level]
        flag = "" if abs(share[level] - target) <= 0.05 else "   <-- off target"
        print(f"  {level} ({target:.0%} wanted)            : {share[level]:5.1%}{flag}")
    repeats = len(stimulus) - len(set(stimulus))
    print(f"  stimulus sets              : {len(stimulus)}"
          f"{f', {repeats} of them REPEAT a scenario' if repeats else ', all distinct'}")
    if pairs:
        same = sum(1 for a, b, *_ in pairs if domains.get(a) == domains.get(b))
        identical = sum(1 for a, b, *_ in pairs if a == b)
        print(f"  choices with both halves in one domain: {same} of {len(pairs)}")
        if identical:
            print(f"  choices offering the same SLO twice   : {identical}")


def main() -> int:
    codes, levels, domains = load()
    if not codes:
        sys.exit(f"{SUBJECT} has no examined SLOs in the seed data")
    print(f"{SUBJECT}: {len(codes)} examined SLOs across "
          f"{len(set(domains.values()))} domains")
    random.seed(7)  # the real planner shuffles; fix it so the run is comparable
    random.shuffle(codes)

    old = old_planner(codes, levels, domains)
    # Every MCQ comes from one of four SLOs, at whatever level the model chose.
    # The levels below are the ones those SLOs are listed under, which is the
    # most generous reading of what the old planner could have produced.
    old_levels = [lvl for c in old["mcq_slos"] for lvl in (levels[c] or ["U"])] * 14
    report(
        "BEFORE", len(set(old["mcq_slos"])), len(codes), old_levels[: PLAN["mcq"]],
        old["stimulus"], [(a, b, "") for a, b in old["written_pairs"]], domains,
    )

    # The planner as it now is
    assignments = assign_levels(
        mcq_pool(codes, domains, PLAN["mcq"]), levels, PLAN["mcq"], domains
    )
    orders = group_by_slo(assignments)
    stimulus = spread(
        [c for c in codes if {"U", "A"} & set(levels[c])] or codes, domains, PLAN["stimulus"]
    )
    pairs = choice_pairs(
        [c for c in codes if c not in stimulus] or codes, levels,
        PLAN["srq"] + PLAN["erq"], domains,
    )
    report(
        "AFTER", len({c for c, _ in assignments}), len(codes),
        [lvl for _, lvl in assignments], stimulus, pairs, domains,
    )
    print(f"  model calls for Section A  : {len(orders)}"
          f" (one per SLO, biggest share {max(sum(m.values()) for _, m in orders)})")

    print("\nwhat each internal choice now offers:")
    for index, (first, second, level) in enumerate(pairs, 1):
        mark = "same domain" if domains.get(first) == domains.get(second) else "across domains"
        print(f"  {index}. {level}  {first} OR {second}  ({mark})")

    drift = off_target([lvl for _, lvl in assignments])
    print()
    if drift:
        print(f"the planned paper is off target: {drift}")
        return 1
    print("the planned paper is on target, draws on the whole scope, "
          "and repeats no scenario")
    return 0


if __name__ == "__main__":
    sys.exit(main())
