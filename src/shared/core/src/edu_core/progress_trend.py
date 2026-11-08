"""Progress over time: a trend line, the FBISE cognitive levels, and streaks.

The progress page could only say where a student is standing. Every number on
it was "right now", so nobody could tell whether they were getting better -
and improvement is the thing that keeps a sixteen year old practising.

Three additions, and each has one decision in it worth stating plainly.

The trend replays the same estimator the headline mastery uses. If it used a
simpler average the last point on the graph would disagree with the number
printed above it, and a student who notices that stops believing both.

The cognitive levels are what makes this FBISE rather than generic. A paper
is 30% Knowledge, 50% Understanding, 20% Application, and a student strong on
recall and weak on application has a different problem from one who is weak
everywhere - a far more common and far more fixable problem. Nothing on the
page could tell them apart.

A streak is counted in the student's own day, not in UTC. Pakistan is five
hours ahead, so a UTC streak silently breaks for anyone revising after 7pm,
which is most of them.

All of it is plain functions over plain values, so the awkward cases - the
week with one answer, the streak across a month boundary, the SLO that is
Knowledge and Understanding at once - can be checked without a database.
"""

from datetime import date, datetime, timedelta, timezone

from edu_core.mastery import advance

# Where the students are. A streak has to be counted in the day the student
# lived through, not the one the server was in: at 9pm in Lahore it is
# already 4pm UTC, but at 2am it is still yesterday in UTC and a streak
# would break for anyone revising late.
PAKISTAN_OFFSET_HOURS = 5

# What the examination actually weights, from the FBISE scheme. Shown beside
# the student's own mastery so the gap is visible: being at 40% on
# Application matters differently from 40% on Knowledge.
PAPER_WEIGHTS = {"K": 30, "U": 50, "A": 20}

LEVEL_NAMES = {
    "K": "Knowledge",
    "U": "Understanding",
    "A": "Application",
}

# How many weeks of trend to return. A term is about this long, and a graph
# with sixty points on a phone is a smudge.
TREND_WEEKS = 12

# A streak needs somewhere to stop looking back.
STREAK_WINDOW_DAYS = 120


def local_day(moment: datetime, offset_hours: int = PAKISTAN_OFFSET_HOURS) -> date:
    """The calendar day this happened on, where the student is.

    Naive values are read as UTC, which is what everything here is stored in.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (moment.astimezone(timezone(timedelta(hours=offset_hours)))).date()


def week_start(day: date) -> date:
    """The Monday of this day's week.

    Weeks rather than days for the trend: most students practise a few times
    a week, and a daily line is mostly gaps with a few spikes, which reads as
    doing badly rather than as doing normally.
    """
    return day - timedelta(days=day.weekday())


def trend(
    answers: list[tuple[datetime, str, float, float]],
    weeks: int = TREND_WEEKS,
    today: date | None = None,
    offset_hours: int = PAKISTAN_OFFSET_HOURS,
) -> list[dict]:
    """Mastery as it stood at the end of each week.

    answers are (when, slo_code, score, weight) in any order; sorted here.

    Mastery is estimated per outcome and then averaged, which is what the
    overview does, and the slo_code is in the tuple for no other reason.
    Pooling every subject's answers into one stream instead looks equivalent
    and is not: the estimator weights by how many answers it has seen, so
    forty pooled answers drive the weight to its floor and forget the early
    mistakes, while ten answers per outcome still remember them. That is not
    a rounding difference. It read 100% against the overview's 88%, and the
    end-to-end check caught it only because it compares the two.

    Weeks with no practice still appear, holding the previous value. Dropping
    them would compress a quiet fortnight into a single step and make a flat
    patch look like progress.
    """
    if not answers:
        return []

    ordered = sorted(answers, key=lambda a: a[0])
    last_day = local_day(ordered[-1][0], offset_hours)
    end = week_start(today or last_day)
    start = end - timedelta(weeks=weeks - 1)

    # Replay every answer in order, remembering where the estimate stood at
    # the end of each week. Answers from before the window still count - they
    # are what the student knew when the window opened.
    #
    # The per-outcome states are carried forward rather than recomputed from
    # scratch at each week, so this stays one pass over the answers however
    # long the student has been practising.
    state: dict[str, tuple[int, float]] = {}
    at_week: dict[date, tuple[int, float | None]] = {}
    for when, code, score, weight in ordered:
        attempts, mastery = state.get(code, (0, 0.0))
        state[code] = advance(attempts, mastery, score, weight)
        total = sum(a for a, _ in state.values())
        mean = sum(m for _, m in state.values()) / len(state)
        at_week[week_start(local_day(when, offset_hours))] = (total, round(mean, 3))

    points = []
    carried: tuple[int, float | None] = (0, None)
    for before in sorted(w for w in at_week if w < start):
        carried = at_week[before]

    for index in range(weeks):
        monday = start + timedelta(weeks=index)
        if monday in at_week:
            carried = at_week[monday]
        attempts, mastery = carried
        points.append(
            {
                "week_start": monday.isoformat(),
                "mastery": mastery,
                "attempts": attempts,
            }
        )
    return points


def answers_this_week(
    moments: list[datetime],
    today: date | None = None,
    offset_hours: int = PAKISTAN_OFFSET_HOURS,
) -> int:
    """How many answers fall in the week the student is currently in."""
    if not moments:
        return 0
    this = week_start(today or local_day(max(moments), offset_hours))
    return sum(
        1 for m in moments if week_start(local_day(m, offset_hours)) == this
    )


def active_days(
    moments: list[datetime],
    today: date | None = None,
    offset_hours: int = PAKISTAN_OFFSET_HOURS,
) -> list[dict]:
    """How many answers on each of the last STREAK_WINDOW_DAYS days.

    Every day in the window is present, including the empty ones, because the
    gaps are the point: a calendar that only lists the good days is a trophy
    cabinet, not a record of what happened.
    """
    end = today or (local_day(max(moments), offset_hours) if moments else None)
    if end is None:
        return []
    counts: dict[date, int] = {}
    for moment in moments:
        day = local_day(moment, offset_hours)
        counts[day] = counts.get(day, 0) + 1
    return [
        {
            "day": (end - timedelta(days=n)).isoformat(),
            "answers": counts.get(end - timedelta(days=n), 0),
        }
        for n in range(STREAK_WINDOW_DAYS - 1, -1, -1)
    ]


def streaks(
    moments: list[datetime],
    today: date | None = None,
    offset_hours: int = PAKISTAN_OFFSET_HOURS,
) -> dict:
    """The run of consecutive days practised, now and at its longest.

    Today not being practised yet does not break the streak. Somebody opening
    the app at nine in the morning has not failed; telling them their streak
    is over before the day has happened is how an app loses them. It breaks
    when a whole day passes with nothing in it.
    """
    if not moments:
        return {"current": 0, "longest": 0, "days_practised": 0, "last_day": None}

    days = sorted({local_day(m, offset_hours) for m in moments})
    now = today or days[-1]

    longest = run = 1
    for earlier, later in zip(days, days[1:]):
        run = run + 1 if (later - earlier).days == 1 else 1
        longest = max(longest, run)

    # Count back from today, or from yesterday if today is still empty.
    current = 0
    anchor = now if days[-1] == now else now - timedelta(days=1)
    if days[-1] >= anchor:
        have = set(days)
        while anchor in have:
            current += 1
            anchor -= timedelta(days=1)

    return {
        "current": current,
        "longest": longest,
        "days_practised": len(days),
        "last_day": days[-1].isoformat(),
    }


def cognitive_split(entries: list[tuple[list[str], float | None, int]]) -> list[dict]:
    """Mastery by FBISE cognitive level, against what the paper weights it.

    entries are (levels, mastery, examined_count) per SLO, where levels is the
    SLO's own list such as ["K", "U"].

    An SLO carrying two levels counts towards both rather than being split
    between them. Splitting would need a weighting the curriculum does not
    give, and inventing one would make the number look precise when it is
    not. Counting it twice says "this SLO tests both", which is what the
    curriculum actually says.
    """
    totals: dict[str, list[float]] = {level: [] for level in PAPER_WEIGHTS}
    examined: dict[str, int] = {level: 0 for level in PAPER_WEIGHTS}
    practised: dict[str, int] = {level: 0 for level in PAPER_WEIGHTS}

    for levels, mastery, count in entries:
        for level in levels or []:
            key = (level or "").strip().upper()[:1]
            if key not in PAPER_WEIGHTS:
                continue
            examined[key] += count
            if mastery is not None:
                totals[key].append(mastery)
                practised[key] += count

    out = []
    for level, weight in PAPER_WEIGHTS.items():
        scores = totals[level]
        out.append(
            {
                "level": level,
                "name": LEVEL_NAMES[level],
                "paper_weight": weight,
                "mastery": round(sum(scores) / len(scores), 3) if scores else None,
                "examined_count": examined[level],
                "practised_count": practised[level],
            }
        )
    return out


def weakest_level(split: list[dict]) -> dict | None:
    """Which level is costing the most marks, or None if it cannot be said.

    Not simply the lowest mastery: being weak on something worth 20% of the
    paper is a smaller problem than being slightly weak on something worth
    50%. The cost is the gap from full marks multiplied by the weight, which
    is the number of marks actually at stake.
    """
    scored = [row for row in split if row["mastery"] is not None]
    if not scored:
        return None
    worst = max(scored, key=lambda row: (1 - row["mastery"]) * row["paper_weight"])
    at_stake = (1 - worst["mastery"]) * worst["paper_weight"]
    # Under a mark or two is not worth sending anyone to revise.
    if at_stake < 2:
        return None
    return {
        "level": worst["level"],
        "name": worst["name"],
        "marks_at_stake": round(at_stake),
    }
