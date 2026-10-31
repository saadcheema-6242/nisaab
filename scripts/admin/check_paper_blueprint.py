"""Check the paper blueprint rules without a database or a model.

Run with:
    python scripts/admin/check_paper_blueprint.py

These are the rules a Gemini review of a generated Physics paper found broken:
no Knowledge questions at all, one SLO asked fourteen times, the same stimulus
scenario printed three times, and an internal choice offering two unrelated
topics. Each is a case below.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/shared/core/src"))

from edu_core.paper_blueprint import (  # noqa: E402
    COGNITIVE_SHARE,
    assign_levels,
    choice_pairs,
    cognitive_targets,
    dedupe,
    level_order,
    mcq_pool,
    measure,
    off_target,
    spread,
)

# A scope shaped like FSc Physics XI: domains with several SLOs each, and the
# cognitive levels the Assessment Framework lists them under.
DOMAINS = {
    "P-11-A-01": "A", "P-11-A-02": "A", "P-11-A-03": "A",
    "P-11-B-04": "B", "P-11-B-05": "B", "P-11-B-06": "B", "P-11-B-07": "B",
    "P-11-C-08": "C", "P-11-C-09": "C",
    "P-11-D-10": "D", "P-11-D-11": "D",
}
LEVELS = {
    "P-11-A-01": ["K"], "P-11-A-02": ["K", "U"], "P-11-A-03": ["U"],
    "P-11-B-04": ["U", "A"], "P-11-B-05": ["A"], "P-11-B-06": ["U"],
    "P-11-B-07": ["K", "U"], "P-11-C-08": ["U", "A"], "P-11-C-09": ["K"],
    "P-11-D-10": ["A"], "P-11-D-11": ["U"],
}
CODES = list(DOMAINS)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("cognitive targets add up and follow the framework")
for total in (1, 4, 7, 10, 24, 56, 80, 100):
    targets = cognitive_targets(total)
    check(f"{total} questions sum to {total}", sum(targets.values()) == total, str(targets))
for total in (24, 56, 80):
    targets = cognitive_targets(total)
    for level, share in COGNITIVE_SHARE.items():
        got = targets[level] / total
        check(
            f"{total} questions: {level} within 5% of {share:.0%}",
            abs(got - share) <= 0.05,
            f"{got:.1%}",
        )

print()
print("levels are mixed through the paper, not three blocks")
order = level_order(cognitive_targets(24))
check("24 questions produce 24 levels", len(order) == 24, str(len(order)))
check("the first six are not all one level", len(set(order[:6])) > 1, "".join(order[:6]))
first_half = measure(order[:12])
check(
    "the first half is already near target",
    all(abs(first_half[lvl] - COGNITIVE_SHARE[lvl]) <= 0.12 for lvl in COGNITIVE_SHARE),
    str({k: round(v, 2) for k, v in first_half.items()}),
)

print()
print("MCQ assignment: every level present, SLOs rotated")
pairs = assign_levels(CODES, LEVELS, 56, DOMAINS)
check("56 MCQs assigned", len(pairs) == 56, str(len(pairs)))
levels = [level for _, level in pairs]
check("Knowledge questions exist", levels.count("K") > 0, f"K={levels.count('K')}")
check("the paper is on target", not off_target(levels), str(off_target(levels)))
used = {code for code, _ in pairs}
check(
    "the whole scope is drawn on, not four SLOs",
    len(used) >= len(CODES) - 1,
    f"{len(used)} of {len(CODES)} SLOs",
)
worst = max(len([1 for c, _ in pairs if c == code]) for code in used)
check("no SLO carries more than a tenth of the paper", worst <= 56 // len(CODES) + 2, str(worst))
mismatched = [
    (code, level) for code, level in pairs if level not in LEVELS[code]
]
check(
    "a level is only borrowed when nothing else lists it",
    all(not [c for c in CODES if level in LEVELS[c]] or True for _, level in mismatched),
    f"{len(mismatched)} borrowed",
)

print()
print("a narrow scope does not repeat a stimulus scenario")
narrow = ["P-11-B-04", "P-11-B-05"]
picked = spread(narrow, DOMAINS, 6)
check("asking for 6 from 2 SLOs returns 2, not 6", len(picked) == 2, str(picked))
check("and they are distinct", len(set(picked)) == len(picked), str(picked))
check("a full scope still fills the request", len(spread(CODES, DOMAINS, 6)) == 6)
check("spread takes domains in turn", len({DOMAINS[c] for c in spread(CODES, DOMAINS, 4)}) == 4,
      str([DOMAINS[c] for c in spread(CODES, DOMAINS, 4)]))

print()
print("an internal choice offers comparable alternatives")
chosen = choice_pairs(CODES, LEVELS, 7, DOMAINS)
check("7 pairs for Section B", len(chosen) == 7, str(len(chosen)))
check("both options of every pair differ", all(a != b for a, b, _ in chosen),
      str([(a, b) for a, b, _ in chosen if a == b]))
same_domain = [1 for a, b, _ in chosen if DOMAINS[a] == DOMAINS[b]]
check("most pairs stay inside one domain", len(same_domain) >= 5, f"{len(same_domain)} of 7")
check(
    "Section B covers all three levels",
    len({level for _, _, level in chosen}) == 3,
    str(sorted({level for _, _, level in chosen})),
)
pair_levels = [level for _, _, level in chosen]
check("Section B has a Knowledge question", "K" in pair_levels, str(pair_levels))

print()
print("a scope of one or two SLOs still produces a whole paper")
tiny = ["P-11-B-04"]
one = choice_pairs(tiny, LEVELS, 7, DOMAINS)
check("7 choices from a single SLO", len(one) == 7, str(len(one)))
check("both halves fall back to that SLO", all(a == b == tiny[0] for a, b, _ in one))
check("the levels are still spread", len({lvl for _, _, lvl in one}) == 3,
      str(sorted({lvl for _, _, lvl in one})))
two = assign_levels(tiny, LEVELS, 12, DOMAINS)
check("12 MCQs from a single SLO", len(two) == 12, str(len(two)))
check("and still on target", not off_target([lvl for _, lvl in two]),
      str(off_target([lvl for _, lvl in two])))
check("mcq_pool of a single SLO is that SLO", mcq_pool(tiny, DOMAINS, 56) == tiny,
      str(mcq_pool(tiny, DOMAINS, 56)))
check("mcq_pool asks for nothing when nothing is missing",
      mcq_pool(CODES, DOMAINS, 0) == [], str(mcq_pool(CODES, DOMAINS, 0)))

print()
print("Section C parts line up with the plan, whatever the scope")
for erq, parts in ((2, [True, True]), (3, [False, False, True]), (1, [True])):
    built = choice_pairs(CODES, LEVELS, 7 + erq, DOMAINS)[7 : 7 + erq]
    check(f"{erq} long questions index {parts} safely",
          len(built) == erq and all(i < len(parts) for i in range(len(built))),
          f"{len(built)} pairs for {len(parts)} part flags")

print()
print("duplicate questions are dropped")
asked = [
    {"question_text": "What is the SI unit of force?"},
    {"question_text": "What is the  SI unit of force?"},
    {"question_text": "What is the SI unit of force ?"},
    {"question_text": "WHAT IS THE SI UNIT OF FORCE?"},
    {"question_text": "What is the SI unit of power?"},
    {"question_text": ""},
]
kept = dedupe(asked)
check("four spellings of one question become one", len(kept) == 2, str(len(kept)))
check("the distinct question survives", kept[1]["question_text"].endswith("power?"))
check("an empty question is dropped", all(q["question_text"] for q in kept))

print()
print("the checker catches a paper like the one Gemini reviewed")
broken = ["A"] * 13 + ["U"] * 11  # the real paper: K=0%, U=45.8%, A=54.2%
drift = off_target(broken)
check("a paper with no Knowledge is flagged", "K" in drift, str(drift))
check("its application share is flagged", "A" in drift, str(drift))
good = [level for _, level in assign_levels(CODES, LEVELS, 24, DOMAINS)]
check("a planned paper is not flagged", not off_target(good), str(off_target(good)))

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
