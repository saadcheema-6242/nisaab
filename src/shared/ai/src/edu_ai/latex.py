"""Clean LaTeX in AI output before it is saved.

Models sometimes double the backslashes of LaTeX commands (\\frac instead of
\frac), usually when writing JSON for structured output. In LaTeX \\ is a line
break, so the formula renders as broken plain words. A doubled backslash
directly before a letter is made single; "\\" followed by a space or newline
(a real line break, e.g. in aligned equations) is kept.
"""

import re
from typing import Any

DOUBLED_BACKSLASH = re.compile(r"\\{2,}(?=[A-Za-z])")


def clean_latex(text: str | None) -> str | None:
    if not text:
        return text
    return DOUBLED_BACKSLASH.sub(lambda _: "\\", text)


def clean_latex_deep(value: Any) -> Any:
    """clean_latex on every string inside dicts and lists."""
    if isinstance(value, str):
        return clean_latex(value)
    if isinstance(value, list):
        return [clean_latex_deep(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_latex_deep(item) for key, item in value.items()}
    return value
