"""Render LaTeX as readable plain text, for places that cannot show maths.

Google Forms has no maths rendering: whatever is sent is shown literally, so
``$\\sqrt{x^2 + y^2}$`` appears on screen exactly like that, dollar signs and
all. Questions written for the app - where KaTeX renders them properly - have
to be converted before they go anywhere plain.

This turns LaTeX into Unicode: ``x^2`` becomes ``x²``, ``\\sqrt{a}`` becomes
``√(a)``, ``\\alpha`` becomes ``α``. It is deliberately lossy. The aim is a
line a student can read and answer, not typeset mathematics; anything that
cannot be mapped is left as readable text rather than dropped, because a
student can work with ``(a+b)/(c+d)`` and cannot work with nothing.
"""

import re

# Digits and the few letters Unicode actually provides in superscript form
SUPERSCRIPTS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "−": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    "n": "ⁿ", "i": "ⁱ",
}
SUBSCRIPTS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "−": "₋", "=": "₌", "(": "₍", ")": "₎",
    "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ",
    "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "x": "ₓ",
}

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "θ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

SYMBOLS = {
    "times": "×", "cdot": "·", "div": "÷", "pm": "±", "mp": "∓",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "approx": "≈", "equiv": "≡", "sim": "~", "propto": "∝",
    "infty": "∞", "partial": "∂", "nabla": "∇", "int": "∫",
    "sum": "Σ", "prod": "Π", "sqrt": "√",
    "rightarrow": "→", "to": "→", "leftarrow": "←", "longrightarrow": "→",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "leftrightarrow": "↔",
    "uparrow": "↑", "downarrow": "↓",
    "circ": "∘", "degree": "°", "angle": "∠", "perp": "⊥", "parallel": "∥",
    "in": "∈", "notin": "∉", "subset": "⊂", "supset": "⊃",
    "cup": "∪", "cap": "∩", "emptyset": "∅",
    "forall": "∀", "exists": "∃", "therefore": "∴", "because": "∵",
    "ldots": "…", "cdots": "⋯", "dots": "…", "vdots": "⋮",
    "prime": "′", "ast": "*", "star": "*", "bullet": "•",
    "lt": "<", "gt": ">", "neg": "¬", "oplus": "⊕", "otimes": "⊗",
    "hbar": "ℏ", "ell": "ℓ", "Re": "ℜ", "Im": "ℑ", "aleph": "ℵ",
}

# Commands that only style their argument; the argument itself is what matters
STYLE_COMMANDS = (
    "text", "textrm", "textbf", "textit", "mathrm", "mathbf", "mathit",
    "mathsf", "mathtt", "mathcal", "mathbb", "operatorname", "boldsymbol",
    "displaystyle", "textstyle", "bf", "rm", "it",
)

# Spacing commands, which carry no meaning once the maths is plain text
SPACING = re.compile(r"\\(?:quad|qquad|,|;|:|!|\s)")

_BRACED = r"\{((?:[^{}]|\{[^{}]*\})*)\}"  # one level of nesting is enough here


def _to_script(text: str, table: dict[str, str]) -> str | None:
    """Map every character, or give up so the caller can fall back."""
    out = []
    for ch in text:
        if ch in table:
            out.append(table[ch])
        elif ch.isspace():
            continue
        else:
            return None
    return "".join(out) or None


# The maths in a question is delimited; the words around it are not. They are
# converted separately, because a rule that is right inside $...$ can be wrong
# outside it - see the note on swallowed spaces in _convert.
MATH_SPAN = re.compile(
    r"\$\$(.+?)\$\$"
    r"|(?<!\\)\$(.+?)(?<!\\)\$"
    r"|\\\[(.+?)\\\]"
    r"|\\\((.+?)\\\)",
    re.S,
)


def _fractions(text: str) -> str:
    """\\frac{a}{b} -> a/b, bracketing either side only when it needs it."""
    pattern = re.compile(r"\\[dt]?frac\s*" + _BRACED + r"\s*" + _BRACED)

    def wrap(part: str) -> str:
        # A single term needs no brackets. Scripts have not been converted yet,
        # so v^2 counts as one term and gives v²/r rather than (v²)/r.
        part = part.strip()
        simple = re.fullmatch(r"[A-Za-z0-9.^_²³¹⁰-₟]+", part)
        return part if simple else f"({part})"

    for _ in range(4):  # nested fractions, innermost first
        text, count = pattern.subn(lambda m: f"{wrap(m.group(1))}/{wrap(m.group(2))}", text)
        if not count:
            break
    return text


def _roots(text: str) -> str:
    text = re.sub(r"\\sqrt\s*\[\s*3\s*\]\s*" + _BRACED, lambda m: f"∛({m.group(1).strip()})", text)
    text = re.sub(r"\\sqrt\s*\[\s*(\d+)\s*\]\s*" + _BRACED,
                  lambda m: f"{m.group(1)}√({m.group(2).strip()})", text)
    text = re.sub(r"\\sqrt\s*" + _BRACED, lambda m: f"√({m.group(1).strip()})", text)
    return text


def _scripts(text: str) -> str:
    """Superscripts and subscripts, braced or single-character."""
    def sup_braced(m: re.Match) -> str:
        mapped = _to_script(m.group(1), SUPERSCRIPTS)
        return mapped if mapped else f"^({m.group(1).strip()})"

    def sub_braced(m: re.Match) -> str:
        mapped = _to_script(m.group(1), SUBSCRIPTS)
        return mapped if mapped else f"_({m.group(1).strip()})"

    text = re.sub(r"\^\s*" + _BRACED, sup_braced, text)
    text = re.sub(r"_\s*" + _BRACED, sub_braced, text)
    text = re.sub(r"\^(.)", lambda m: SUPERSCRIPTS.get(m.group(1), f"^{m.group(1)}"), text)
    text = re.sub(r"_(.)", lambda m: SUBSCRIPTS.get(m.group(1), f"_{m.group(1)}"), text)
    return text


def _convert(text: str, in_math: bool) -> str:
    """Convert one run of text. ``in_math`` says it came from inside $...$."""
    if not text:
        return ""

    # Degrees before \circ becomes the ring operator, or 30^\circ reads "30∘"
    text = re.sub(r"\^\s*\{?\s*\\(?:circ|degree)\s*\}?", "°", text)

    # Styling wrappers: keep the argument, drop the command
    for command in STYLE_COMMANDS:
        text = re.sub(r"\\" + command + r"\s*" + _BRACED, r"\1", text)
        text = re.sub(r"\\" + command + r"(?![A-Za-z])", "", text)

    text = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)\s*(?=[\(\)\[\]\{\}|.])", "", text)
    text = re.sub(r"\\begin" + _BRACED + r"|\\end" + _BRACED, "", text)

    text = _roots(text)
    text = _fractions(text)

    for name, glyph in GREEK.items():
        # LaTeX swallows the space that ends a command name, so \Delta H is one
        # symbol: ΔH, not Δ H. Only before a letter or digit - \alpha + \beta
        # keeps its spacing around the operator - and only inside maths, where
        # what follows is a variable rather than the next English word.
        if in_math:
            text = re.sub(r"\\" + name + r"(?![A-Za-z]) +(?=[A-Za-z0-9])", glyph, text)
        text = re.sub(r"\\" + name + r"(?![A-Za-z])", glyph, text)
    # Operators keep their spacing: v \times B reads better as v × B than v ×B
    for name, glyph in sorted(SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"\\" + name + r"(?![A-Za-z])", glyph, text)

    # Any command left that decorates one argument - \vec{F}, \hat{n}, \bar{x} -
    # is worth less than the argument itself once the maths is plain text
    for _ in range(3):
        text, count = re.subn(r"\\[A-Za-z]+\s*" + _BRACED, r"\1", text)
        if not count:
            break

    text = _scripts(text)

    text = SPACING.sub(" ", text)
    text = text.replace("\\\\", " ")
    text = re.sub(r"\\([%$&#_{}])", r"\1", text)      # escaped literals
    # An unknown command keeps its name: \sin x should read "sin x", not " x"
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    return text.replace("{", "").replace("}", "")


def latex_to_text(value: str | None) -> str:
    """Convert LaTeX to plain readable Unicode. Safe on text with no maths."""
    if not value:
        return ""

    text = str(value)
    pieces: list[str] = []
    end = 0
    for match in MATH_SPAN.finditer(text):
        pieces.append(_convert(text[end : match.start()], in_math=False))
        body = next(group for group in match.groups() if group is not None)
        pieces.append(_convert(body, in_math=True))
        end = match.end()
    pieces.append(_convert(text[end:], in_math=False))

    joined = "".join(pieces)
    joined = re.sub(r"[ \t]+", " ", joined)
    joined = re.sub(r" +([,.;:)])", r"\1", joined)
    return joined.strip()
