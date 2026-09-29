"""IBCC 10-band grading scale (HSSC-I from the 2026 exams, HSSC-II from 2027).

Grade-point values per band are not yet published, so only the bands are used.
"""

# (minimum percentage, grade, descriptor), highest first
IBCC_BANDS = [
    (96, "A++", "Extraordinary"),
    (91, "A+", "Exceptional"),
    (86, "A", "Outstanding"),
    (81, "B++", "Excellent"),
    (76, "B+", "Very Good"),
    (71, "B", "Good"),
    (61, "C+", "Fairly Good"),
    (51, "C", "Above Average"),
    (40, "D", "Emerging"),
    (0, "U", "Ungraded"),
]
PASS_PERCENT = 40


def grade_for(percent: float) -> tuple[str, str]:
    """Return (grade, descriptor) for a percentage."""
    rounded = round(percent)
    for minimum, grade, descriptor in IBCC_BANDS:
        if rounded >= minimum:
            return grade, descriptor
    return IBCC_BANDS[-1][1], IBCC_BANDS[-1][2]
