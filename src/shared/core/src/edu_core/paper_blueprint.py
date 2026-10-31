"""How an FBISE paper distributes itself: cognitive levels, SLO spread, choice pairs.

The FBISE Assessment Framework weights a paper by cognitive level, not by topic
alone. Left to itself a generator writes almost entirely application questions,
because those are the interesting ones to write - and a paper with no recall in
it assesses badly and reads as far harder than the real thing. A prepared
student is meant to be unable to lose roughly a third of the marks.

So the levels are decided here, before anything is written, and each question is
asked for at the level the paper needs rather than whatever the model felt like.
Everything in this module is a pure function of the syllabus map, so the rules
can be checked without a database or a model.
"""

import itertools
import re

LEVELS = ("K", "U", "A")
LEVEL_NAMES = {"K": "Knowledge", "U": "Understanding", "A": "Application"}

# FBISE's weighting for a summative paper. Knowledge is recall of facts and
# definitions, Understanding is explain/compare/interpret, Application is
# calculate or apply to a new situation.
COGNITIVE_SHARE = {"K": 0.30, "U": 0.50, "A": 0.20}
# How far a finished paper may drift from the shares above before it is wrong.
# Used by the checker, not the planner: the planner hits the target exactly, and
# the drift comes from the model labelling a question differently from the level
# it was asked for.
COGNITIVE_TOLERANCE = 0.05


def cognitive_targets(total: int) -> dict[str, int]:
    """How many of ``total`` questions each level gets.

    Largest remainder, so the three numbers always add up to ``total`` exactly -
    a paper that is one question short because of rounding is a paper that does
    not add up to 80 marks.
    """
    if total <= 0:
        return dict.fromkeys(LEVELS, 0)
    exact = {level: total * COGNITIVE_SHARE[level] for level in LEVELS}
    out = {level: int(exact[level]) for level in LEVELS}
    short = total - sum(out.values())
    by_remainder = sorted(LEVELS, key=lambda level: exact[level] - out[level], reverse=True)
    for level in by_remainder[:short]:
        out[level] += 1
    return out


def level_order(targets: dict[str, int]) -> list[str]:
    """The level for each question in turn, mixed rather than three blocks.

    A paper whose first sixteen MCQs are all recall and whose last eight are all
    application is correctly weighted and still reads wrongly. This spreads them
    the way a Bresenham line spreads pixels: at every point the levels are as
    close to their share as whole questions allow.
    """
    out: list[str] = []
    done = dict.fromkeys(targets, 0)
    for _ in range(sum(targets.values())):
        behind = [level for level in LEVELS if done.get(level, 0) < targets.get(level, 0)]
        if not behind:
            break
        # +0.5 so a level with a target of 1 is not starved by one with 50
        level = min(behind, key=lambda lvl: (done[lvl] + 0.5) / targets[lvl])
        done[level] += 1
        out.append(level)
    return out


def spread(codes: list[str], domain_of: dict[str, str], count: int) -> list[str]:
    """Up to ``count`` DISTINCT SLO codes, taking domains in turn.

    Never repeats a code. The caller asking for more codes than exist gets a
    shorter list and is expected to notice: silently repeating one is what made
    a paper print the same stimulus scenario three times.
    """
    by_domain: dict[str, list[str]] = {}
    for code in codes:
        by_domain.setdefault(domain_of.get(code, ""), []).append(code)
    picked: list[str] = []
    while len(picked) < count and any(by_domain.values()):
        for domain in list(by_domain):
            if by_domain[domain] and len(picked) < count:
                picked.append(by_domain[domain].pop(0))
    return picked


# How many MCQs one model call should write. Enough that the call can see a
# spread of its own work and vary it; few enough that one bad call costs little.
PER_CALL = 4


def mcq_pool(
    codes: list[str],
    domain_of: dict[str, str],
    total: int,
    per_call: int = PER_CALL,
) -> list[str]:
    """Which SLOs Section A should be written from, spread over the domains.

    Every SLO in scope would be ideal for coverage and is wrong in practice: a
    hundred and fifty outcomes means a hundred and fifty model calls of one
    question each, which is slow, costs the most per question and rate-limits
    us at Vertex. This takes as many SLOs as the paper can give about
    ``per_call`` questions to, so coverage is wide and the calls stay few.
    """
    if total <= 0 or not codes:
        return []
    return spread(codes, domain_of, max(1, -(-total // per_call)))


def assign_levels(
    codes: list[str],
    levels_of: dict[str, list[str]],
    total: int,
    domain_of: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """Which SLO to ask about and at which level, for each of ``total`` MCQs.

    Returns ``(slo_code, level)`` pairs. SLOs rotate, so a paper draws on the
    whole scope instead of asking one outcome fourteen times, and each level
    prefers the SLOs the framework lists it under.

    An SLO is allowed at a level it does not list when nothing else can serve
    that level: asking for the definition behind an "explain" outcome is a fair
    Knowledge question, and the alternative - dropping the level - is a paper
    with no recall in it at all.
    """
    if total <= 0 or not codes:
        return []
    ordered = spread(codes, domain_of or {}, len(codes)) or list(codes)
    # No outcome may dominate. Without a cap, a level that only two or three
    # SLOs list is asked of those same SLOs over and over, which is the bug
    # this module replaces wearing different clothes.
    cap = max(2, -(-total // len(ordered)) + 1)
    wheels = {}
    for level in LEVELS:
        able = [code for code in ordered if level in (levels_of.get(code) or ())]
        wheels[level] = itertools.cycle(able or ordered)
    asked = dict.fromkeys(ordered, 0)
    out = []
    for level in level_order(cognitive_targets(total)):
        code = _next_under_cap(wheels[level], asked, cap, ordered)
        asked[code] += 1
        out.append((code, level))
    return out


def _next_under_cap(
    wheel, asked: dict[str, int], cap: int, ordered: list[str]
) -> str:
    """The wheel's next SLO that is not already carrying its share of the paper.

    When every SLO listed at this level is at its cap, the least-asked SLO in
    the whole scope takes the question instead - better a fair Knowledge
    question from an "explain" outcome than the same outcome asked eight times.
    """
    for _ in range(len(ordered)):
        code = next(wheel)
        if asked.get(code, 0) < cap:
            return code
    return min(ordered, key=lambda code: asked.get(code, 0))


def choice_pairs(
    codes: list[str],
    levels_of: dict[str, list[str]],
    count: int,
    domain_of: dict[str, str] | None = None,
) -> list[tuple[str, str, str]]:
    """``count`` pairs of SLOs for an internal choice, as ``(a, b, level)``.

    Both options of a choice must be comparable: the same cognitive level, and
    the same domain wherever the scope allows it. A student picking (a) OR (b)
    should be choosing how to show one skill - not gambling on which of two
    unrelated topics they happened to revise, which is what pairing adjacent
    entries of a domain-alternating list produced.
    """
    if count <= 0 or not codes:
        return []
    domains = domain_of or {}
    used: set[str] = set()
    pairs: list[tuple[str, str, str]] = []
    for level in level_order(cognitive_targets(count)):
        pairs.append(_pick_pair(codes, levels_of, domains, level, used))
    return pairs


def _pick_pair(
    codes: list[str],
    levels_of: dict[str, list[str]],
    domain_of: dict[str, str],
    level: str,
    used: set[str],
) -> tuple[str, str, str]:
    """Two SLOs for one choice, as alike as the scope allows.

    Tried in order: unused SLOs listed at this level in one domain, then unused
    at this level anywhere, then any unused, then whatever exists. A small scope
    ends up reusing an SLO, which is honest - two questions on one outcome is a
    real FBISE paper, two unrelated topics offered as alternatives is not.
    """
    able = [c for c in codes if level in (levels_of.get(c) or ())]

    for pool in (able, codes):
        free = [c for c in pool if c not in used]
        by_domain: dict[str, list[str]] = {}
        for code in free:
            by_domain.setdefault(domain_of.get(code, ""), []).append(code)
        together = next((v for v in by_domain.values() if len(v) >= 2), None)
        if together:
            first, second = together[0], together[1]
            used.update((first, second))
            return first, second, level
        if len(free) >= 2:
            used.update((free[0], free[1]))
            return free[0], free[1], level

    # Nothing unused left: fall back to the pool itself, newest choice first
    pool = able or codes
    first = pool[0]
    second = pool[1] if len(pool) > 1 else first
    return first, second, level


def group_by_slo(
    assignments: list[tuple[str, str]],
) -> list[tuple[str, dict[str, int]]]:
    """Turn per-question assignments into one order per SLO: how many at each level.

    One model call per SLO rather than one per SLO and level. Asking for the
    whole SLO's share in a single call is both cheaper and better: the model can
    see everything it has written for that outcome, so it cannot repeat itself
    within the call, which is where the duplicates came from.
    """
    grouped: dict[str, dict[str, int]] = {}
    for code, level in assignments:
        mix = grouped.setdefault(code, {})
        mix[level] = mix.get(level, 0) + 1
    return list(grouped.items())


def _key(text: str) -> str:
    """A question's identity for comparison: its words, nothing else."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def distinct_by_text(items: list, text_of=lambda q: q.question_text) -> list:
    """The items that ask something new, in order, comparing by question text.

    Same rule as ``dedupe`` but for a list of objects rather than dicts, so the
    quiz path can use it on the model's structured output directly.
    """
    seen: set[str] = set()
    out = []
    for item in items:
        key = _key(text_of(item))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def dedupe(questions: list[dict], field: str = "question_text") -> list[dict]:
    """Drop questions that ask the same thing as an earlier one.

    MCQs are written in small independent batches so they can run in parallel,
    and no batch knows what the others wrote. Without this a paper asks one
    question eight times with the options shuffled.
    """
    seen: set[str] = set()
    out = []
    for question in questions:
        key = _key(question.get(field, ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(question)
    return out


def measure(levels: list[str | None]) -> dict[str, float]:
    """The share of each level in a finished paper, for checking against target."""
    known = [lvl for lvl in levels if lvl in LEVELS]
    if not known:
        return dict.fromkeys(LEVELS, 0.0)
    return {level: known.count(level) / len(known) for level in LEVELS}


def off_target(levels: list[str | None]) -> dict[str, float]:
    """How far each level is outside tolerance, empty when the paper is sound."""
    share = measure(levels)
    return {
        level: round(share[level] - COGNITIVE_SHARE[level], 3)
        for level in LEVELS
        if abs(share[level] - COGNITIVE_SHARE[level]) > COGNITIVE_TOLERANCE
    }
