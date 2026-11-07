"""The rules of a poll in a class room.

A poll is how a class settles something quickly: which chapter is hardest,
did anyone else get B for question 4, should we revise Thermodynamics first.
It is a post with options rather than a separate feature, so it threads and
moderates like everything else.

The counting lives here, away from the database, because an off-by-one in a
percentage is the kind of thing nobody notices and everybody sees.
"""

MIN_OPTIONS = 2
MAX_OPTIONS = 6
MAX_OPTION_LENGTH = 120
MAX_QUESTION_LENGTH = 300


def check_question(question: str | None) -> str:
    """The poll's question as it will be stored, or ValueError."""
    said = (question or "").strip()
    if not said:
        raise ValueError("A poll needs a question.")
    if len(said) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"A poll question can be at most {MAX_QUESTION_LENGTH} characters."
        )
    return said


def check_options(options: list[str] | None) -> list[str]:
    """The options as they will be stored, or ValueError.

    Blanks are dropped rather than refused: the form shows empty boxes, and a
    student who fills three of four has made a three option poll, not a
    mistake worth an error message.

    Duplicates are refused, because two identical options split the vote and
    the result means nothing.
    """
    given = [(o or "").strip() for o in (options or [])]
    kept = [o for o in given if o]

    if len(kept) < MIN_OPTIONS:
        raise ValueError(f"A poll needs at least {MIN_OPTIONS} options.")
    if len(kept) > MAX_OPTIONS:
        raise ValueError(f"A poll can have at most {MAX_OPTIONS} options.")
    for option in kept:
        if len(option) > MAX_OPTION_LENGTH:
            raise ValueError(
                f"An option can be at most {MAX_OPTION_LENGTH} characters."
            )

    seen = {o.lower() for o in kept}
    if len(seen) != len(kept):
        raise ValueError("Two options are the same. Make them different.")
    return kept


def tally(counts: list[int]) -> list[int]:
    """Whole percentages that add up to exactly 100.

    Rounding each share on its own gives 33 + 33 + 33 = 99, and a student
    reading a poll that totals 99 percent assumes the app is broken. The
    largest remainder goes the extra point, which is the standard way of
    apportioning and the only one that is defensible when it is questioned.
    """
    total = sum(counts)
    if total <= 0:
        return [0 for _ in counts]

    exact = [c * 100 / total for c in counts]
    floors = [int(e) for e in exact]
    short = 100 - sum(floors)

    # Hand the remaining points to whoever was cut by the most. Ties go to
    # the earlier option, so the same votes always give the same picture.
    order = sorted(
        range(len(counts)), key=lambda i: (-(exact[i] - floors[i]), i)
    )
    for i in order[:short]:
        floors[i] += 1
    return floors


def winning(counts: list[int]) -> set[int]:
    """Which options are in the lead. Empty before anyone has voted.

    A set, because a tie has no single winner and showing one of them as the
    winner would be a lie the data does not support.
    """
    if not counts or sum(counts) == 0:
        return set()
    best = max(counts)
    return {i for i, c in enumerate(counts) if c == best}
