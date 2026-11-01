"""How a study plan divides a student's time: what to revise, for how long, when.

Two ways in, and they answer different questions:

- A custom topic ("projectile motion", "Thermodynamics", "P-11-B-05"). The plan
  stays inside that topic, and within it the outcomes the student is worst at
  come first. A topic a student has never practised is still plannable, which
  is the point - most custom topics have no practice history at all.
- No topic. The plan covers everything the student is weak at, across the whole
  syllabus, ordered by how badly they are doing.

Weakness is measured, never guessed: every practice attempt is recorded against
the FBISE outcome it assessed, so an outcome's accuracy is a fact in the
database. An outcome with no attempts is not weak, it is unknown, and the two
are planned for differently - you drill the first and introduce the second.

The arithmetic lives here, as pure functions of the practice records and the
syllabus. A model is asked only to phrase the result. Left to decide the
allocation itself a model produces a plan that reads well and does not add up -
the same failure the paper generator had, where it chose its own spread and
wrote a paper with no recall questions in it.
"""

from dataclasses import dataclass, field

# An outcome at or below this accuracy is one the student is getting wrong
# often enough to need drilling rather than revision.
WEAK_BELOW = 0.70
# Below this it is not a gap, it is untaught: the plan starts from the
# explainer rather than throwing more questions at them.
STRUGGLING_BELOW = 0.40
# Fewer attempts than this says very little either way, so such an outcome is
# ordered after the ones there is real evidence about.
ENOUGH_ATTEMPTS = 3

# What one sitting of each kind costs, in minutes, and what it asks of them.
# Deliberately coarse: the point is a budget a student can keep, not a
# prediction of how long they will take.
ACTIONS = {
    "read": {"minutes": 15, "target": None},
    "flashcards": {"minutes": 10, "target": "Get every card right twice"},
    "quiz": {"minutes": 20, "target": "Score 70% or more"},
    "srq": {"minutes": 25, "target": "Score 3 of 4 marks or better"},
}

# The order work is introduced for one outcome. A student who cannot do the
# questions is sent back to the explanation first; one who nearly has it goes
# straight to the questions.
LADDERS = {
    "struggling": ["read", "flashcards", "quiz", "srq"],
    "weak": ["flashcards", "quiz", "srq"],
    "unknown": ["read", "quiz", "srq"],
    "solid": ["quiz", "srq"],
}

MIN_DAYS, MAX_DAYS = 1, 180
MIN_HOURS, MAX_HOURS = 0.25, 16.0
# A session shorter than this is not worth switching topic for
MIN_SESSION_MINUTES = 10


@dataclass
class Outcome:
    """One FBISE outcome, with whatever the student's practice says about it."""

    code: str
    description: str = ""
    domain: str = ""
    attempts: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float | None:
        """Share correct, or None when they have never attempted it."""
        return self.correct / self.attempts if self.attempts else None

    @property
    def standing(self) -> str:
        """Which ladder this outcome needs: struggling, weak, unknown or solid."""
        rate = self.accuracy
        if rate is None:
            return "unknown"
        if rate < STRUGGLING_BELOW:
            return "struggling"
        if rate < WEAK_BELOW:
            return "weak"
        return "solid"

    @property
    def is_weak(self) -> bool:
        return self.standing in ("struggling", "weak")


@dataclass
class PlanItem:
    """One thing to do on one day, against one outcome."""

    day: int
    slo_code: str
    action: str
    minutes: int
    target: str | None = None
    title: str = ""
    domain: str = ""
    standing: str = ""


@dataclass
class Plan:
    """A whole plan, and the facts behind it, ready to be phrased and stored."""

    items: list[PlanItem] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    days: int = 0
    minutes_per_day: int = 0
    scope: str = "whole syllabus"

    @property
    def total_minutes(self) -> int:
        return sum(item.minutes for item in self.items)

    @property
    def weak_codes(self) -> list[str]:
        return [o.code for o in self.outcomes if o.is_weak]


def clamp_period(days: int | None, hours_per_day: float | None) -> tuple[int, int]:
    """A sane number of days, and minutes per day, from whatever was asked for.

    A student who says "one year, ten hours a day" is not describing a plan
    they will keep, and a plan of forty thousand minutes is not one this can
    schedule usefully, so both ends are capped rather than refused.
    """
    period = int(days or 7)
    period = max(MIN_DAYS, min(period, MAX_DAYS))
    hours = float(hours_per_day or 2.0)
    hours = max(MIN_HOURS, min(hours, MAX_HOURS))
    return period, int(round(hours * 60))


def outcomes_from(
    syllabus: list[dict], records: list[dict], codes: list[str] | None = None
) -> list[Outcome]:
    """Join the syllabus to what the student has actually attempted.

    ``syllabus`` is the outcomes in scope; ``records`` is one entry per practice
    attempt with ``slo_code`` and ``was_correct``. An attempt whose outcome is
    not in scope is ignored, so a topic plan is not skewed by work on another.
    """
    wanted = set(codes) if codes is not None else None
    found: dict[str, Outcome] = {}
    for slo in syllabus:
        code = slo.get("code") or ""
        if not code or (wanted is not None and code not in wanted):
            continue
        found[code] = Outcome(
            code=code,
            description=slo.get("description") or "",
            domain=slo.get("domain") or "",
        )

    for record in records:
        outcome = found.get(record.get("slo_code") or "")
        if outcome is None:
            continue
        outcome.attempts += 1
        if record.get("was_correct"):
            outcome.correct += 1
    return list(found.values())


def rank(outcomes: list[Outcome], weak_only: bool = False) -> list[Outcome]:
    """Outcomes in the order a student should spend time on them.

    Worst first, and an outcome with real evidence behind it ahead of one with
    a single unlucky attempt. Outcomes never practised come after the weak ones
    - they may well be fine - but ahead of the ones already solid.

    ``weak_only`` drops everything the student is not actually weak at, which
    is what a plan over the whole syllabus wants. A plan on one topic keeps
    them, because a topic with no weaknesses still needs to be revised.
    """
    if weak_only:
        outcomes = [o for o in outcomes if o.is_weak]

    def key(outcome: Outcome) -> tuple:
        order = {"struggling": 0, "weak": 1, "unknown": 2, "solid": 3}
        return (
            order[outcome.standing],
            0 if outcome.attempts >= ENOUGH_ATTEMPTS else 1,
            outcome.accuracy if outcome.accuracy is not None else 1.0,
            -outcome.attempts,
            outcome.code,
        )

    return sorted(outcomes, key=key)


def share_out(ranked: list[Outcome], total_minutes: int) -> list[tuple[Outcome, list[str]]]:
    """How far down the list the time reaches, and what to do with each outcome.

    Each outcome is given its ladder until the budget runs out. A short plan
    therefore covers a few outcomes properly rather than every outcome
    uselessly - ten minutes each on thirty topics teaches nobody anything.
    """
    out: list[tuple[Outcome, list[str]]] = []
    left = total_minutes
    for outcome in ranked:
        ladder = LADDERS[outcome.standing]
        afford: list[str] = []
        for action in ladder:
            cost = ACTIONS[action]["minutes"]
            if cost > left:
                break
            afford.append(action)
            left -= cost
        if afford:
            out.append((outcome, afford))
        if left < MIN_SESSION_MINUTES:
            break
    return out


def lay_out(
    shared: list[tuple[Outcome, list[str]]], days: int, minutes_per_day: int
) -> list[PlanItem]:
    """Put the work on days, filling each day before starting the next.

    An outcome's steps stay in order and stay together where a day has room,
    because reading about something and then practising it a week later is not
    the same lesson twice.
    """
    items: list[PlanItem] = []
    day = 1
    used = 0
    for outcome, actions in shared:
        for action in actions:
            cost = ACTIONS[action]["minutes"]
            if used + cost > minutes_per_day and day < days:
                day += 1
                used = 0
            items.append(
                PlanItem(
                    day=day,
                    slo_code=outcome.code,
                    action=action,
                    minutes=cost,
                    target=ACTIONS[action]["target"],
                    domain=outcome.domain,
                    standing=outcome.standing,
                )
            )
            used += cost
    return items


def build(
    syllabus: list[dict],
    records: list[dict],
    days: int | None = None,
    hours_per_day: float | None = None,
    weak_only: bool = False,
    scope: str = "whole syllabus",
) -> Plan:
    """The whole plan: who is weak at what, for how long, on which day."""
    period, per_day = clamp_period(days, hours_per_day)
    outcomes = outcomes_from(syllabus, records)
    ranked = rank(outcomes, weak_only=weak_only)
    shared = share_out(ranked, period * per_day)
    return Plan(
        items=lay_out(shared, period, per_day),
        outcomes=ranked,
        days=period,
        minutes_per_day=per_day,
        scope=scope,
    )


def summarise(plan: Plan) -> str:
    """What the student's practice says, as lines for the model to read.

    Facts only. The model is asked to phrase a plan, not to work out which
    outcomes are weak - it has no way of knowing and would guess.
    """
    lines = [
        f"Scope: {plan.scope}",
        f"Time: {plan.days} days at {plan.minutes_per_day} minutes a day "
        f"({plan.total_minutes} minutes planned)",
    ]
    graded = [o for o in plan.outcomes if o.attempts]
    if graded:
        lines.append("Practice so far:")
        for outcome in graded[:20]:
            lines.append(
                f"- {outcome.code}: {outcome.correct}/{outcome.attempts} correct "
                f"({(outcome.accuracy or 0):.0%}) - {outcome.standing}"
            )
    else:
        lines.append("Practice so far: none recorded for these outcomes.")
    fresh = [o for o in plan.outcomes if not o.attempts]
    if fresh:
        lines.append(f"Never practised: {', '.join(o.code for o in fresh[:15])}")
    return "\n".join(lines)
