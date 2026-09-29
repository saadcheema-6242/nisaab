"""One-off clean-up: make doubled LaTeX backslashes single in stored AI content.

New AI output is cleaned before saving (edu_ai.latex); this repairs rows saved
before that. The web app also repairs text on display, so this only makes the
stored data (review page, exports, tutor context) clean too. Safe to run again.

Usage (from the repository root, with DATABASE_URL set):
    uv run --package edu-worker python scripts/content/fix_latex.py [--dry-run]
On Google Cloud: deploy/gcp/deploy.sh script scripts/content/fix_latex.py
"""

import argparse
import os

from edu_ai.latex import clean_latex, clean_latex_deep
from edu_db.models import ContentItem, Flashcard, Note, QuizQuestion, SrqAttempt, SrqQuestion
from edu_db.session import get_session_factory, init_db

TEXT_FIELDS = {
    QuizQuestion: ["question_text", "option_a", "option_b", "option_c", "option_d", "explanation"],
    Flashcard: ["question", "answer"],
    SrqQuestion: ["question", "model_answer"],
    Note: ["content"],
}
JSON_FIELDS = {
    ContentItem: ["payload"],
    SrqQuestion: ["rubric"],
    SrqAttempt: ["result"],
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Only count what would change")
    args = parser.parse_args()

    init_db(os.environ["DATABASE_URL"])
    with get_session_factory()() as db:
        for model in sorted({*TEXT_FIELDS, *JSON_FIELDS}, key=lambda m: m.__tablename__):
            changed = 0
            for row in db.query(model).yield_per(200):
                row_changed = False
                for field in TEXT_FIELDS.get(model, []):
                    value = getattr(row, field)
                    fixed = clean_latex(value)
                    if fixed != value:
                        setattr(row, field, fixed)
                        row_changed = True
                for field in JSON_FIELDS.get(model, []):
                    value = getattr(row, field)
                    fixed = clean_latex_deep(value)
                    if fixed != value:
                        setattr(row, field, fixed)
                        row_changed = True
                changed += row_changed
            print(f"{model.__tablename__}: {changed} row(s) {'to fix' if args.dry_run else 'fixed'}")
        if args.dry_run:
            db.rollback()
        else:
            db.commit()


if __name__ == "__main__":
    main()
