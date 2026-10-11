"""What the student chose before practice (question type, level, notes), as generation
instructions and as a filter for teacher-bank questions."""

import re

# Question type → instructions for the AI
STYLES = {
    "theory": (
        "Theory and concept questions only: definitions, explanations, 'why' and 'what happens "
        "if' questions, comparisons and properties. No calculations."
    ),
    "numerical": (
        "Numerical problems only: every question gives realistic values in SI units and asks for "
        "a calculated result, the options are numbers with units, and the explanation shows the "
        "full working."
    ),
    "derivation": (
        "Questions on derivations and proofs: the starting relations, assumptions, key steps, "
        "intermediate results and the final expression."
    ),
    "mixed": "A mix like the FBISE paper: about half concept questions and half numericals.",
}

# Level → the difficulty line of the prompt, and the cognitive levels a bank question may have
LEVELS = {
    "easy": ("easy: recall and simple understanding, one step each", {"K", "U"}),
    "board": ("mixed like the FBISE annual paper (easy, medium and hard)", {"K", "U", "A"}),
    "challenging": ("hard: application, multi-step problems and tricky distractors", {"A"}),
}

NUMBER_WITH_UNIT = re.compile(
    r"\d(?:[\d.,]*)\s*(?:\\,|~|\s)*(?:\\(?:text|mathrm)\{\s*)?"
    r"(?:m|s|kg|g|N|J|W|Pa|Hz|K|V|A|C|mol|cm|km|mm|nm|L|eV|rad|m/s|ms)\b"
)
CALCULATE = re.compile(
    r"\b(calculate|compute|evaluate|solve|find|determine|work out|how (much|many|far|long|fast)"
    r"|what (is|will be) the (value|magnitude|angle|resultant|area|volume|work|torque))\b",
    re.IGNORECASE,
)
# Given values without units: A = 2i + 3j, x = -4, (2, 5)
GIVEN_VALUES = re.compile(r"=\s*[-−+]?\s*\(?\d|\d\s*\\?(?:hat\{)?[ijk]\b|\(\s*-?\d+\s*,\s*-?\d+")
# SLOs examined with numericals in Physics and Chemistry (all of Mathematics)
NUMERICAL_SLO = re.compile(
    r"\b(calculat|solv|comput|determin|numerical|quantitativ|evaluat|find|equation|formula|problems?)\w*",
    re.IGNORECASE,
)
NUMERICAL_SUBJECTS = ("PHY", "CHEM", "MATH")


def normalize_style(style: str | None) -> str:
    style = (style or "mixed").strip().lower()
    for key in STYLES:
        if style.startswith(key[:5]):
            return key
    if "numer" in style or "calcul" in style:
        return "numerical"
    if "proof" in style or "deriv" in style:
        return "derivation"
    if "concept" in style or "defin" in style:
        return "theory"
    return "mixed"


def normalize_level(level: str | None) -> str:
    level = (level or "board").strip().lower()
    if level.startswith(("easy", "basic", "simple")):
        return "easy"
    if level.startswith(("hard", "chall", "difficult", "tough")):
        return "challenging"
    return "board"


def difficulty(level: str) -> str:
    return LEVELS[normalize_level(level)][0]


def instructions(style: str, notes: str | None = None, focus: str | None = None) -> str:
    """Extra instructions for the generation prompt."""
    parts = [STYLES[normalize_style(style)]]
    if focus:
        parts.append(f"Focus on: {focus}.")
    if notes:
        parts.append(f"The student also said: {notes.strip()[:300]}")
    return " ".join(parts)


def card_instructions(focus: str | None = None, notes: str | None = None) -> str:
    """Extra instructions for flashcards: what to focus on and anything else the student said."""
    parts = []
    if focus:
        parts.append(f"Focus the cards on: {focus}.")
    if notes:
        parts.append(f"The student also said: {notes.strip()[:300]}")
    return " ".join(parts)


STYLE_NAMES = {"theory": "theory", "numerical": "numericals", "derivation": "derivations", "mixed": "practice"}


def is_numerical(text: str) -> bool:
    if NUMBER_WITH_UNIT.search(text):
        return True
    return bool(re.search(r"\d", text) and (CALCULATE.search(text) or GIVEN_VALUES.search(text)))


def numerical_slo(subject_code: str, description: str, cognitive_levels: list[str] | None) -> bool:
    """Whether an SLO gets numerical questions: all of Mathematics, and in Physics and
    Chemistry the SLOs at the Apply level or about calculations."""
    if subject_code not in NUMERICAL_SUBJECTS:
        return False
    return (
        subject_code == "MATH"
        or "A" in (cognitive_levels or [])
        or bool(NUMERICAL_SLO.search(description))
    )


def bank_fits(payload: dict, style: str, level: str) -> bool:
    """Whether a bank MCQ suits the chosen question type and level."""
    style, level = normalize_style(style), normalize_level(level)
    if style == "derivation":
        return False
    cognitive = payload.get("cognitive_level")
    if cognitive and cognitive not in LEVELS[level][1]:
        return False
    if style == "mixed":
        return True
    numerical = is_numerical(payload.get("question_text") or "")
    return numerical if style == "numerical" else not numerical


def split(total: int, parts: int) -> list[int]:
    """Spread total over parts as evenly as possible: split(5, 2) == [3, 2]."""
    parts = max(parts, 1)
    return [total // parts + (1 if i < total % parts else 0) for i in range(parts)]


# AI-written questions per call; more are written in parallel batches
BATCH = 3


def batch_note(number: int, total: int) -> str:
    """Tell parallel batches apart so they don't write the same questions."""
    if total <= 1:
        return ""
    return (
        f" This is batch {number} of {total} written separately: use different situations, "
        f"values and sub-ideas from the other batches (for batch {number}, prefer less common "
        "examples)."
    )
