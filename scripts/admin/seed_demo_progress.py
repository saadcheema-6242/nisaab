"""Fill a demo account's practice history, so the Progress page has shape.

Run with:
    deploy/gcp/deploy.sh script scripts/admin/seed_demo_progress.py --email you@example.com
    deploy/gcp/deploy.sh script scripts/admin/seed_demo_progress.py --email you@example.com --undo

Why this exists: Progress is the most convincing screen in NISAAB and the
only one that cannot be demonstrated on a fresh account. A judge clicking
it sees an empty chart, and so does a camera. This writes a term's worth
of practice for one named account against that account's own real
subjects and real SLOs, so every number on the page is computed by the
same code that computes a real student's.

What it is not: it does not invent outcomes, subjects or scores out of
nothing. It reads the SLOs the account's grade subjects actually have and
writes answers against those. The shape of the history is chosen - a
student who starts shaky and improves, with one bad week - but every
figure the page then shows is derived, not planted.

Deterministic: the same email and the same `--weeks` always produce the
same history, because the generator is seeded from the email rather than
from the clock. Re-running replaces rather than doubling.
"""

import argparse
import hashlib
import pathlib
import random
import sys
from datetime import datetime, timedelta, timezone

HERE = pathlib.Path(__file__).resolve().parents[2]
for pkg in ("db", "core"):
    sys.path.insert(0, str(HERE / f"src/shared/{pkg}/src"))

from edu_db.models import (  # noqa: E402
    GradeSubject,
    PracticeRecord,
    Project,
    Slo,
    StudentProfile,
    User,
)
from edu_db.session import get_session_factory  # noqa: E402

# A term. Long enough for the weekly trend to have a story in it.
DEFAULT_WEEKS = 10
# Answers per week. Enough that mastery settles, few enough to be credible
# for one student revising alongside school.
PER_WEEK = (14, 26)
# The arc: roughly what fraction of answers are right in week n. Starts
# shaky, improves, dips once - a flat climb reads as fabricated.
ARC = (0.42, 0.48, 0.55, 0.52, 0.61, 0.68, 0.64, 0.74, 0.79, 0.83)

ITEM_TYPES = ("quiz_question", "flashcard", "srq")


def seeded(email: str) -> random.Random:
    """Same account, same history, every run."""
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--email", required=True, help="The account to fill")
    ap.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    ap.add_argument(
        "--undo",
        action="store_true",
        help="Remove only the records this script wrote for that account",
    )
    args = ap.parse_args()

    rng = seeded(args.email)
    db = get_session_factory()()
    try:
        user = (
            db.query(User)
            .filter(User.email.ilike(args.email.strip()))
            .one_or_none()
        )
        if user is None:
            print(f"No account with email {args.email!r}.")
            return 1

        # Every record this script writes is marked, so --undo can take
        # back exactly what it put in and nothing a person actually did.
        mark = "demo-seed"

        if args.undo:
            n = (
                db.query(PracticeRecord)
                .filter(
                    PracticeRecord.user_id == user.id,
                    PracticeRecord.item_id.like(f"{mark}:%"),
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            print(f"Removed {n} seeded records. Real practice is untouched.")
            return 0

        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == user.id)
            .one_or_none()
        )
        if profile is None:
            print("That account has no student profile; finish onboarding first.")
            return 1

        projects = (
            db.query(Project)
            .filter(
                Project.owner_id == user.id,
                Project.kind == "subject_workspace",
                Project.archived_at.is_(None),
            )
            .all()
        )
        if not projects:
            print("That account has no subject workspaces.")
            return 1

        # The real SLOs of the account's own subjects. Nothing invented.
        pool: list[tuple[Project, Slo]] = []
        for project in projects:
            if not project.grade_subject_id:
                continue
            gs = db.get(GradeSubject, project.grade_subject_id)
            if gs is None:
                continue
            slos = (
                db.query(Slo)
                .join(Slo.domain)
                .filter(Slo.domain.has(grade_subject_id=gs.id))
                .all()
            )
            for slo in slos:
                pool.append((project, slo))

        if not pool:
            print(
                "No SLOs found for those subjects. Load the curriculum first:\n"
                "  deploy/gcp/deploy.sh seed"
            )
            return 1

        # A student does not practise every outcome. Pick a believable
        # working set, weighted so a handful are drilled and most are met
        # once or twice - which is what makes the mastery spread look real.
        working = rng.sample(pool, min(len(pool), max(24, len(pool) // 6)))
        favourites = working[: max(4, len(working) // 5)]

        existing = (
            db.query(PracticeRecord)
            .filter(
                PracticeRecord.user_id == user.id,
                PracticeRecord.item_id.like(f"{mark}:%"),
            )
            .count()
        )
        if existing:
            db.query(PracticeRecord).filter(
                PracticeRecord.user_id == user.id,
                PracticeRecord.item_id.like(f"{mark}:%"),
            ).delete(synchronize_session=False)
            print(f"Replacing {existing} records from a previous run.")

        now = datetime.now(timezone.utc)
        written = 0
        for week in range(args.weeks):
            # Week 0 is the oldest. The last week is the current one.
            age = args.weeks - 1 - week
            accuracy = ARC[min(week, len(ARC) - 1)]
            for _ in range(rng.randint(*PER_WEEK)):
                project, slo = (
                    rng.choice(favourites) if rng.random() < 0.45 else rng.choice(working)
                )
                correct = rng.random() < accuracy
                when = now - timedelta(
                    days=age * 7 + rng.randint(0, 6),
                    hours=rng.randint(6, 21),
                    minutes=rng.randint(0, 59),
                )
                written += 1
                db.add(
                    PracticeRecord(
                        user_id=user.id,
                        project_id=project.id,
                        item_type=rng.choice(ITEM_TYPES),
                        item_id=f"{mark}:{week}:{written}",
                        topic=(slo.description or "")[:180],
                        slo_code=slo.code,
                        user_answer="seeded",
                        correct_answer="seeded",
                        was_correct=correct,
                        score=1.0 if correct else 0.0,
                        created_at=when,
                    )
                )
        db.commit()

        print(f"Wrote {written} practice records for {user.email}.")
        print(f"  {args.weeks} weeks, {len(working)} outcomes across {len(projects)} subjects.")
        print("  Accuracy climbs from about 42% to about 83%, with one dip.")
        print("Undo with the same command plus --undo.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
