"""Per-SLO mastery estimated from practice answers.

Mastery is an exponentially weighted accuracy: the first answers are averaged,
then each new answer moves the estimate by at least 30%, so recent practice
counts more than old mistakes. Right/wrong items count as 1 or 0; written
answers count as their share of marks. Flashcards are self-rated by the
student, so they move the estimate half as much. Kept simple and explainable.
"""

from collections.abc import Iterable

from edu_db.models import PracticeRecord
from sqlalchemy.orm import Session

MIN_WEIGHT = 0.3
SELF_RATED_WEIGHT = 0.5  # flashcards: the student marks "knew it" themselves


def estimate(results: Iterable[float | tuple[float, float]]) -> tuple[int, float | None]:
    """Return (attempts, mastery) for answers in chronological order.

    Each result is a score (0..1) or (score, weight), where weight scales how much
    the answer moves the estimate.
    """
    attempts = 0
    mastery = 0.0
    for result in results:
        score, factor = result if isinstance(result, tuple) else (result, 1.0)
        attempts += 1
        weight = min(1.0, max(1 / attempts, MIN_WEIGHT) * factor)
        if attempts == 1:
            weight = 1.0  # the first answer sets the starting point
        mastery += weight * (score - mastery)
    return attempts, (round(mastery, 3) if attempts else None)


def slo_mastery(
    db: Session, user_id: str, slo_codes: Iterable[str]
) -> dict[str, tuple[int, float | None]]:
    """Return {slo_code: (attempts, mastery)} for the SLOs the user has practised."""
    codes = list(slo_codes)
    if not codes:
        return {}
    rows = (
        db.query(
            PracticeRecord.slo_code,
            PracticeRecord.was_correct,
            PracticeRecord.score,
            PracticeRecord.item_type,
        )
        .filter(PracticeRecord.user_id == user_id, PracticeRecord.slo_code.in_(codes))
        .order_by(PracticeRecord.created_at)
        .all()
    )
    answers: dict[str, list[tuple[float, float]]] = {}
    for code, correct, score, item_type in rows:
        value = score if score is not None else (1.0 if correct else 0.0)
        factor = SELF_RATED_WEIGHT if item_type == "flashcard" else 1.0
        answers.setdefault(code, []).append((value, factor))
    return {code: estimate(results) for code, results in answers.items()}
