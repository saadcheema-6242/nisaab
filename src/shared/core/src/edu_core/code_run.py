"""Asking a model to draw by writing code, and reading back what it drew.

A model cannot draw a correct labelled figure. It cannot place a 60 degree
angle, it cannot spell "8.0 km", and a confidently wrong diagram in front of a
student about to sit a board paper is worse than no diagram at all. That is why
the image maker was taken out.

But a model can write the ten lines of matplotlib that draw the figure exactly,
and Google will run them in its own sandbox and hand back the picture. The
arithmetic is then done by Python rather than guessed by a language model,
which is the same split the paper and study plan blueprints already use.

This module is the part of that with no network in it: the rules the model is
given, and the reading of what comes back. Both are pure functions, so they can
be checked on their own - which matters, because the alternative is finding out
from a student that the figure never appeared.

What search is still for: a photograph or a drawn-from-life diagram, a lung, a
leaf section, a distillation set-up. Those exist already, drawn by people, and
no amount of matplotlib will produce one.
"""

import base64
import binascii
from dataclasses import dataclass, field

# Google's sandbox stops a run at thirty seconds and has no network. These are
# its limits, not ours, and are stated to the model so it does not write code
# that reaches for a dataset it cannot have.
SANDBOX_SECONDS = 30
SANDBOX_LIBRARIES = "numpy, pandas and matplotlib"

# What comes back when the model draws. PNG is what matplotlib emits.
PICTURE_TYPES = ("image/png", "image/jpeg")


@dataclass
class CodeRun:
    """What the model did when asked to work something out in code."""

    text: str = ""
    code: str = ""
    pictures: list[bytes] = field(default_factory=list)
    outcome: str = ""
    output: str = ""

    @property
    def drew_something(self) -> bool:
        return bool(self.pictures)

    @property
    def failed(self) -> bool:
        """Whether the sandbox reported the code did not run.

        An empty outcome means no code ran at all, which is its own failure:
        the model answered in words when it was asked for a figure.
        """
        return bool(self.outcome) and self.outcome != "OUTCOME_OK"


def _first(part: dict, *names: str):
    """A field of a reply part, under whichever spelling it arrived in.

    Google's own documentation shows camelCase in its REST examples and
    snake_case in its chat examples. A reader that trusted one of them would
    fail silently on the other: no picture, and no error saying why.
    """
    for name in names:
        if name in part:
            return part[name]
    return None


def read_parts(parts: list[dict]) -> CodeRun:
    """Pull a reply apart: the words, the code that ran, and any picture.

    Anything unrecognised is ignored rather than raising. A reply that carries
    a figure and one field this does not know about is still a reply with a
    figure in it.
    """
    run = CodeRun()
    words: list[str] = []
    code: list[str] = []

    for part in parts or []:
        if not isinstance(part, dict):
            continue

        text = part.get("text")
        if isinstance(text, str) and text.strip():
            words.append(text)

        wrote = _first(part, "executableCode", "executable_code")
        if isinstance(wrote, dict) and wrote.get("code"):
            code.append(str(wrote["code"]))

        ran = _first(part, "codeExecutionResult", "code_execution_result")
        if isinstance(ran, dict):
            run.outcome = str(ran.get("outcome") or run.outcome)
            if ran.get("output"):
                run.output = str(ran["output"])

        inline = _first(part, "inlineData", "inline_data")
        if isinstance(inline, dict):
            kind = str(_first(inline, "mimeType", "mime_type") or "").lower()
            data = inline.get("data")
            if kind in PICTURE_TYPES and isinstance(data, str):
                try:
                    run.pictures.append(base64.b64decode(data, validate=True))
                except (binascii.Error, ValueError):
                    # A picture that will not decode is not a picture. Saying
                    # so beats storing a broken file and linking the student
                    # to it.
                    continue

    run.text = "\n".join(words).strip()
    run.code = "\n\n".join(code).strip()
    return run


# How a figure has to be drawn to be worth putting in front of an FSc student.
# Written as rules rather than an example, because an example gets copied: ask
# for a velocity-time graph against a prompt showing projectile motion and the
# model draws the projectile.
FIGURE_RULES = f"""You are drawing one figure for a Pakistani FBISE FSc student, by writing Python.

Write Python that draws it with matplotlib and nothing else. You have {SANDBOX_LIBRARIES}, no internet, and {SANDBOX_SECONDS} seconds.

THE FIGURE
- Draw exactly one figure. End with plt.show() - without it nothing comes back.
- Use only the numbers in the request. Never invent a data point, a reading or a value the student did not give. If something needed is missing, draw what can be drawn and leave the rest off.
- Work the geometry out in code - trigonometry, components, intercepts, gradients - rather than typing in coordinates you worked out in your head. That is the whole point of drawing it this way.

LABELS, WHICH ARE WHAT IT IS FOR
- Label both axes with the quantity and its SI unit, as FBISE writes them: "Time t (s)", "Velocity v (m s^-1)".
- Put a short title on it.
- Label every vector, force, ray, component or curve on the figure itself, next to the thing it names.
- Add a legend only when more than one series is drawn.
- Mark the values that matter: a resultant's magnitude and angle, an intercept, a gradient, an apex.

HOW IT HAS TO LOOK
- figsize=(7, 5), dpi=150, white background. Never set a style sheet or a colour theme; the defaults are there and seaborn may not be.
- Font size 11 or more. It is read on a phone.
- For vectors, geometry, ray diagrams and anything where shape carries meaning, set ax.set_aspect('equal') or the angles are a lie.
- Draw vectors and forces with ax.annotate or ax.quiver so they have real arrowheads.
- Grid on for a graph, off for a diagram.
- No decoration: no emoji, no clip art, no shadows, no 3D unless the question is about three dimensions.

DO NOT
- Do not print an explanation; the words come separately. One short print of a computed value is fine if it is worth checking.
- Do not read or write files, and do not reach for the internet.
- Do not draw a photograph or anything drawn from life - a lung, a leaf section, a laboratory set-up. Those are found, not plotted, and another tool does it.
"""


def figure_prompt(description: str, subject: str = "", given: str = "") -> str:
    """The whole instruction sent to the model for one figure.

    ``description`` is what to draw, ``subject`` the student's subject, and
    ``given`` the numbers from their own question - kept apart from the
    description so the rule against inventing values has something to point at.
    """
    asked = (description or "").strip() or "a figure for this question"
    lines = [FIGURE_RULES, "", "WHAT TO DRAW", asked]
    if subject.strip():
        lines += ["", f"SUBJECT: {subject.strip()} (FBISE FSc)"]
    if given.strip():
        lines += [
            "",
            "THE STUDENT'S OWN NUMBERS - use these exactly, and no others:",
            given.strip(),
        ]
    return "\n".join(lines)
