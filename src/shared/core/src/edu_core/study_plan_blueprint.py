"""How a study plan divides a student's time: what to revise, for how long, when.

Two ways in, and they answer different questions. A student is asked which one
they mean, because guessing from whether they happened to name a topic got it
wrong often enough to matter:

- A topic ("projectile motion", "Thermodynamics", "data science"). The plan
  teaches that topic from the syllabus, in syllabus order, the way it would be
  taught in class. Practice records are not consulted and never mentioned: the
  student asked for a plan on a topic, not for a report on how they are doing.
- Weak topics. The plan covers everything the student's own practice says they
  are weak at, across the whole syllabus, worst first, and says so plainly.

Weakness is measured, never guessed: every practice attempt is recorded against
the FBISE outcome it assessed, so an outcome's accuracy is a fact in the
database. An outcome with no attempts is not weak, it is unknown, and the two
are planned for differently - you drill the first and introduce the second.

A plan also has to fill the time it was asked for. The first version walked the
outcomes once, gave each one its ladder, and stopped - so a topic holding four
outcomes produced the same four hours of work whether the student asked for a
week or for a month, and "thirty days, five hours a day" came back as one day.
Learning something once is not a month of study, so the passes after the first
revisit the same outcomes with harder work: practise, drill, then sit a paper.

The arithmetic lives here, as pure functions of the practice records and the
syllabus. A model is asked only to phrase the result. Left to decide the
allocation itself a model produces a plan that reads well and does not add up -
the same failure the paper generator had, where it chose its own spread and
wrote a paper with no recall questions in it.
"""

from dataclasses import dataclass, field

# How a plan was asked for. TOPIC teaches a named topic; WEAK drills whatever
# the practice records say is going wrong.
TOPIC, WEAK = "topic", "weak"

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
    "paper": {"minutes": 45, "target": "Finish it inside the time"},
}

# The order work is introduced for one outcome the student is weak at. A
# student who cannot do the questions is sent back to the explanation first;
# one who nearly has it goes straight to the questions.
LADDERS = {
    "struggling": ["read", "flashcards", "quiz", "srq"],
    "weak": ["flashcards", "quiz", "srq"],
    "unknown": ["read", "quiz", "srq"],
    "solid": ["quiz", "srq"],
}

# How a topic is met for the first time, whatever the student's record on it.
# In topic mode every outcome gets this, because the plan is teaching the
# topic rather than reacting to a score.
TOPIC_LADDER = ["read", "flashcards", "quiz", "srq"]

# What the passes after the first one do. Covering a topic once is not a month
# of study, so a long plan comes back to the same outcomes with harder work
# instead of being padded out or silently shortened. Each pass is a sweep of
# the whole scope, so an outcome is revisited days after it was learnt rather
# than twice in an afternoon.
REVISION_PASSES = [
    ["quiz", "srq"],
    ["flashcards", "quiz"],
    ["srq", "paper"],
]
MAX_PASSES = 1 + len(REVISION_PASSES)

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
class Sitting:
    """One piece of work against one outcome, before it has a day."""

    outcome: Outcome
    action: str
    # Which sweep of the scope this belongs to: 0 is meeting the outcome,
    # 1 and up are coming back to it.
    pass_index: int = 0


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
    pass_index: int = 0


@dataclass
class Plan:
    """A whole plan, and the facts behind it, ready to be phrased and stored."""

    items: list[PlanItem] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    days: int = 0
    minutes_per_day: int = 0
    scope: str = "whole syllabus"
    mode: str = WEAK
    # What the student asked for, kept even when the scope could not fill it,
    # so the plan can say so rather than quietly delivering something smaller
    # or padding itself out with work that is not really there.
    asked_days: int = 0
    asked_minutes_per_day: int = 0

    @property
    def total_minutes(self) -> int:
        return sum(item.minutes for item in self.items)

    @property
    def weak_codes(self) -> list[str]:
        return [o.code for o in self.outcomes if o.is_weak]

    @property
    def passes(self) -> int:
        """How many times the plan goes over the scope."""
        return max((item.pass_index for item in self.items), default=-1) + 1

    @property
    def offered_minutes(self) -> int:
        """All the time the student put on the table."""
        return self.asked_days * self.asked_minutes_per_day

    @property
    def is_light(self) -> bool:
        """Whether the scope held appreciably less work than was asked for.

        A topic holds the work it holds. Asked for a month on one chapter, the
        plan covers that chapter properly - several times over, harder each
        time - and then stops, rather than padding itself out with sittings
        nobody needs. The wording says so plainly, because a plan that quietly
        comes back a quarter of the length asked for reads as a broken plan.
        """
        return bool(self.items) and self.offered_minutes > 0 and (
            self.total_minutes < self.offered_minutes * 0.75
        )


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
    is what a plan over their weaknesses wants.
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


def order_for(outcomes: list[Outcome], mode: str) -> list[Outcome]:
    """The outcomes a plan will work through, in the order it will work through them.

    In topic mode that is syllabus order, because a topic is taught in
    sequence - you do not meet the hard outcome of a chapter before its first
    one just because a quiz went badly. In weak mode it is worst first, and
    anything the student is not weak at is dropped.
    """
    if mode == WEAK:
        return rank(outcomes, weak_only=True)
    return list(outcomes)


def ladder_for(outcome: Outcome, mode: str) -> list[str]:
    """How this outcome is met the first time.

    In topic mode every outcome gets the same teaching ladder: the plan is
    covering the topic, not responding to a score, and a student who asked for
    a plan on data science did not ask to be told what they are bad at.
    """
    if mode == TOPIC:
        return list(TOPIC_LADDER)
    return list(LADDERS[outcome.standing])


def share_out(
    ranked: list[Outcome], total_minutes: int, mode: str = WEAK
) -> list[Sitting]:
    """What to do, in order, for as long as the time lasts.

    The first sweep meets every outcome the time reaches. Each later sweep goes
    back over the same outcomes with harder work, so a plan asked for over a
    month is a month of study rather than one afternoon repeated. Without the
    later sweeps the plan's size came from how many outcomes the topic held and
    ignored the days and hours entirely.

    A budget too small for even the first sweep covers fewer outcomes properly
    rather than every outcome uselessly - ten minutes each on thirty topics
    teaches nobody anything.
    """
    out: list[Sitting] = []
    left = total_minutes
    for index in range(MAX_PASSES):
        if left < MIN_SESSION_MINUTES:
            break
        for outcome in ranked:
            actions = (
                ladder_for(outcome, mode)
                if index == 0
                else REVISION_PASSES[index - 1]
            )
            for action in actions:
                cost = ACTIONS[action]["minutes"]
                if cost > left:
                    break
                out.append(Sitting(outcome=outcome, action=action, pass_index=index))
                left -= cost
            if left < MIN_SESSION_MINUTES:
                break
    return out


def lay_out(
    sittings: list[Sitting], days: int, minutes_per_day: int
) -> list[PlanItem]:
    """Put the work on days, spread rather than packed into the first few.

    Filling each day to the brim before starting the next put a four-hour plan
    entirely on day one and left the other twenty-nine days of a month-long
    plan empty.

    So each day takes an even share of the work that is still to be placed,
    over the days still to come, and never more than the student said they
    could manage. The share is recomputed at every step, which is the part
    that matters: a day that comes out light makes the days after it heavier,
    instead of the last day being left to absorb everything that did not fit.
    A fixed share did exactly that, and put 190 minutes on day ten of a plan
    the student had capped at 120.

    An outcome's steps stay in order, because reading about something and then
    practising it a week later is not the same lesson twice.
    """
    items: list[PlanItem] = []
    if not sittings or days < 1:
        return items

    costs = [ACTIONS[s.action]["minutes"] for s in sittings]
    left = sum(costs)
    day = 1
    used = 0
    for index, sitting in enumerate(sittings):
        cost = costs[index]
        # The share this day should take: an even cut of the work still to be
        # placed, over the days still to come, and never past the student's
        # own limit.
        share = min(
            minutes_per_day,
            max(MIN_SESSION_MINUTES, -(-left // (days - day + 1))),
        )
        if used > 0 and used + cost > share and day < days:
            day += 1
            used = 0
        # The last day gets no more than any other. Packing a day greedily
        # always leaves a little of it unused, so a budget of days times hours
        # is slightly more work than those days can actually hold, and the
        # remainder used to land on the final day - 235 minutes of it against
        # a limit of 120. The honest answer is a plan that ends when the time
        # is used up, not a last day nobody could sit through.
        if used > 0 and used + cost > minutes_per_day:
            break
        items.append(
            PlanItem(
                day=day,
                slo_code=sitting.outcome.code,
                action=sitting.action,
                minutes=cost,
                target=ACTIONS[sitting.action]["target"],
                domain=sitting.outcome.domain,
                standing=sitting.outcome.standing,
                pass_index=sitting.pass_index,
            )
        )
        used += cost
        left -= cost
    return items


def build(
    syllabus: list[dict],
    records: list[dict],
    days: int | None = None,
    hours_per_day: float | None = None,
    mode: str = WEAK,
    scope: str = "whole syllabus",
) -> Plan:
    """The whole plan: what to study, for how long, on which day.

    ``mode`` is ``TOPIC`` to teach the outcomes in ``syllabus`` in syllabus
    order, or ``WEAK`` to drill whatever the records say is going wrong.
    """
    mode = TOPIC if mode == TOPIC else WEAK
    period, per_day = clamp_period(days, hours_per_day)
    outcomes = outcomes_from(syllabus, records)
    ordered = order_for(outcomes, mode)
    sittings = share_out(ordered, period * per_day, mode)
    items = lay_out(sittings, period, per_day)
    if mode == TOPIC:
        # Why a step is here is a claim about the student's practice. A topic
        # plan makes no such claim, so it carries none, and nothing downstream
        # can label a step "Not practised yet" on a topic they never asked to
        # be assessed on.
        for item in items:
            item.standing = ""

    # What the plan actually comes to, which is what the student is told. A
    # month asked for on one chapter is however many days that chapter really
    # holds; reporting the thirty days and showing eight of them is the kind
    # of mismatch that makes a working plan look broken.
    by_day: dict[int, int] = {}
    for item in items:
        by_day[item.day] = by_day.get(item.day, 0) + item.minutes

    return Plan(
        items=items,
        outcomes=ordered,
        days=max(by_day, default=0) or period,
        minutes_per_day=max(by_day.values(), default=0) or per_day,
        scope=scope,
        mode=mode,
        asked_days=period,
        asked_minutes_per_day=per_day,
    )


def summarise(plan: Plan) -> str:
    """The facts behind the plan, as lines for the model to read.

    Facts only, and only the ones that bear on how this plan was made. A topic
    plan is told nothing about practice records: mentioning them is what put
    "there are no practice records on file" at the top of a plan the student
    asked for on data science, which is not an answer to what they asked.
    """
    lines = [
        f"Scope: {plan.scope}",
        f"Time: {plan.days} days at about {plan.minutes_per_day} minutes a day "
        f"({plan.total_minutes} minutes planned)",
    ]

    if plan.mode == TOPIC:
        lines.append(
            "This is a plan on a topic the student named. It teaches the "
            "outcomes below in syllabus order."
        )
        if plan.passes > 1:
            lines.append(
                f"It goes over the topic {plan.passes} times: first to learn "
                "it, then with harder practice each time."
            )
        lines.append(
            "Outcomes covered: " + ", ".join(o.code for o in plan.outcomes[:25])
        )
        if plan.is_light:
            lines.append(
                f"The student offered {plan.asked_days} days at about "
                f"{plan.asked_minutes_per_day} minutes a day. This topic does "
                "not hold that much work, and the plan covers it properly "
                "rather than being padded out. Say this plainly in one "
                "sentence and offer a wider topic, or the whole syllabus, if "
                "they want to use all that time."
            )
        return "\n".join(lines)

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
    if plan.passes > 1:
        lines.append(
            f"The plan goes over these outcomes {plan.passes} times, with "
            "harder practice each time."
        )
    if plan.is_light:
        lines.append(
            f"The student offered {plan.asked_days} days at about "
            f"{plan.asked_minutes_per_day} minutes a day, and there is less "
            "than that to drill. Say so in one sentence, and suggest they use "
            "the spare time on a topic they name."
        )
    return "\n".join(lines)
