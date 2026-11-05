"""Catching a question whose answer key disagrees with its own explanation.

A teacher sat one of our quizzes, chose the option the explanation itself
calls correct, and was marked wrong. The marking was fine: it compares the
chosen letter with the stored one. What was wrong was the question. The model
had written four options, picked a letter, and written an explanation
concluding something else, and nothing anywhere compared the two.

That is the worst failure this product can have. A student who is told their
right answer is wrong does not conclude the app is broken - they conclude they
do not understand, and they change their mind about something they had
correct. It costs them marks in the real paper.

So a question has to agree with itself before a student ever sees it. The
explanation does the arithmetic; the letter is one token the model might label
wrongly. Where they clearly disagree the question is dropped, because a
shorter quiz is better than one that marks a right answer wrong - the same
reason the generator already drops duplicates.

Pure functions of the question's own text, so the rule can be checked against
real cases with no model and no database.
"""

import re

LETTERS = ("a", "b", "c", "d")

# A number as a student would write one, including decimals and a leading
# sign. Scientific notation is matched as its mantissa, which is enough to
# tell four options apart.
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")

# Words that mean an option is being ruled out rather than chosen. An
# explanation that says "not 30 degrees, because..." mentions 30 without
# meaning it, and a checker that missed this would drop good questions.
REJECTING = (
    "not ", "n't", "incorrect", "wrong", "rather than", "instead of",
    "would be", "common mistake", "trap", "distractor", "rules out",
)

# Where the claim stops and the reasoning starts. "Launched at 45 degrees,
# because sin(2x) is largest when 2x is 90" names 45 and 90, and only the
# first is the answer - the 90 belongs to the working. Cutting here is what
# turns an ambiguous sentence into a clear one.
BECAUSE = re.compile(
    r"\b(?:because|since|as|which|where|when|given that|using)\b",
    re.I,
)


def letter_of(option: str | None) -> str | None:
    """The single letter a model meant, or None if it did not name one."""
    first = (option or "").strip().lower()[:1]
    return first if first in LETTERS else None


def numbers_in(text: str | None) -> set[str]:
    """Every number in the text, as comparable strings.

    Trailing zeros are dropped so that "45.0" and "45" are the same answer,
    which is how a student reads them.
    """
    found = set()
    for raw in NUMBER.findall(text or ""):
        value = raw.rstrip("0").rstrip(".") if "." in raw else raw
        found.add(value or "0")
    return found


def distinguishing(options: dict[str, str]) -> dict[str, set[str]]:
    """The numbers that tell each option apart from the others.

    A number appearing in more than one option says nothing about which was
    meant, so it is ignored. Four options of 10.2 m, 14.4 m, 20.4 m and
    40.8 m each keep their own value; four options that all say "m" keep
    nothing from the unit.
    """
    seen: dict[str, int] = {}
    per_option = {letter: numbers_in(text) for letter, text in options.items()}
    for values in per_option.values():
        for value in values:
            seen[value] = seen.get(value, 0) + 1
    return {
        letter: {v for v in values if seen[v] == 1}
        for letter, values in per_option.items()
    }


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _rejecting(sentence: str) -> bool:
    low = sentence.lower()
    return any(word in low for word in REJECTING)


def implied_letter(options: dict[str, str], explanation: str | None) -> str | None:
    """Which option the explanation actually concludes, or None if unclear.

    Only sentences that are asserting something count. An explanation saying
    "the answer is 45 degrees, not 30" names two option values, and only one
    of them is being claimed.

    None is returned whenever the answer is not obvious, which is most of the
    time for questions with wordy options. Silence is the right answer there:
    this exists to catch a clear contradiction, not to grade the model.
    """
    marks = distinguishing(options)
    if not any(marks.values()):
        return None

    asserting = [s for s in _sentences(explanation or "") if not _rejecting(s)]
    if not asserting:
        return None

    def only_hit(text: str) -> str | None:
        said = numbers_in(text)
        hits = [letter for letter, values in marks.items() if values & said]
        return hits[0] if len(hits) == 1 else None

    # The claim first, with each sentence's reasoning trimmed off. Only if
    # that is still unclear is the whole thing considered, because a working
    # full of given values names numbers that were never options.
    claims = " ".join(BECAUSE.split(s)[0] for s in asserting)
    return only_hit(claims) or only_hit(" ".join(asserting))


def disagrees(
    correct_option: str | None, options: dict[str, str], explanation: str | None
) -> bool:
    """Whether the key and the explanation clearly contradict each other.

    False when the answer cannot be read out of the explanation, so a question
    is only ever dropped on evidence, never on a hunch.
    """
    stated = letter_of(correct_option)
    if stated is None:
        return True
    implied = implied_letter(options, explanation)
    return implied is not None and implied != stated


def options_of(question: object) -> dict[str, str]:
    """The four options of a generated question, by letter."""
    return {
        letter: str(getattr(question, f"option_{letter}", "") or "")
        for letter in LETTERS
    }


def sound(question: object) -> bool:
    """Whether this question is safe to put in front of a student."""
    return not disagrees(
        getattr(question, "correct_option", None),
        options_of(question),
        getattr(question, "explanation", None),
    )


def keep_sound(questions: list) -> tuple[list, list]:
    """Split generated questions into the ones to keep and the ones to drop."""
    keep, drop = [], []
    for question in questions:
        (keep if sound(question) else drop).append(question)
    return keep, drop
