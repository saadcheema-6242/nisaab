"""Check that LaTeX becomes readable plain text for Google Forms.

Run with:
    python scripts/admin/check_plain_math.py

Google Forms renders nothing: whatever is sent appears literally. A quiz
published on 27 Oct 2026 went out with options reading "$\\sqrt{x^2 + y^2}$"
and "$4$", because the questions are written in LaTeX for KaTeX in the app.
These cases are taken from that form and from the notation the five subjects
actually use.

Exits non-zero if any conversion regresses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/shared/core/src"))

from edu_core.plain_math import latex_to_text  # noqa: E402

CASES: list[tuple[str, str]] = [
    # --- straight from the form that came out wrong ---
    (r"$4$", "4"),
    (r"$\sqrt{x^2 + y^2}$", "√(x² + y²)"),
    (r"$\sqrt{y^2 + z^2}$", "√(y² + z²)"),
    (r"$|z|$", "|z|"),
    (r"negative $z$-axis", "negative z-axis"),
    (r"The $xy$-plane", "The xy-plane"),
    (r"The origin $O(0, 0, 0)$", "The origin O(0, 0, 0)"),
    (
        r"the simultaneous equations $x = 0$ and $y = 0$ represent",
        "the simultaneous equations x = 0 and y = 0 represent",
    ),
    # --- Physics ---
    (r"$v^2 / r$", "v² / r"),
    (r"$\frac{v^2}{r}$", "v²/r"),
    (r"$\frac{1}{2}mv^2$", "1/2mv²"),
    (r"$E = mc^2$", "E = mc²"),
    (r"$10^{-19}$", "10⁻¹⁹"),
    (r"$\theta = 30^\circ$", "θ = 30°"),
    (r"$v \times B$", "v × B"),
    (r"$\lambda = \frac{h}{p}$", "λ = h/p"),
    (r"$\vec{F} = m\vec{a}$", "F = ma"),
    (r"$\text{Force} = 10\,\text{N}$", "Force = 10 N"),
    # --- Chemistry ---
    (r"$H_2SO_4$", "H₂SO₄"),
    (r"$\Delta H$ is negative", "ΔH is negative"),
    (r"$\alpha$ and $\beta$ particles", "α and β particles"),
    # --- Mathematics ---
    (r"$\frac{a + b}{c + d}$", "(a + b)/(c + d)"),
    (r"$x_1 + x_2$", "x₁ + x₂"),
    (r"$x \leq 5$ and $y \geq 2$", "x ≤ 5 and y ≥ 2"),
    (r"$\sqrt[3]{8} = 2$", "∛(8) = 2"),
    (r"$\sin \theta + \cos \theta$", "sin θ + cos θ"),
    (r"$\alpha + \beta$", "α + β"),
    (r"$\infty$", "∞"),
    # --- text with no maths must survive untouched ---
    ("Speed is constant but direction is not.", "Speed is constant but direction is not."),
    ("", ""),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    failures = 0
    for source, expected in CASES:
        actual = latex_to_text(source)
        if actual == expected:
            continue
        failures += 1
        print(f"FAIL  {source}")
        print(f"        got      {actual}")
        print(f"        expected {expected}")

    if latex_to_text(None) != "":
        print("FAIL  None should convert to an empty string")
        failures += 1

    total = len(CASES) + 1
    if failures:
        print(f"\n{failures} of {total} failed")
        return 1
    print(f"All {total} conversions correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
