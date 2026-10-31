"""Delete every student account and everything belonging to it.

Run with:
    deploy/gcp/deploy.sh script scripts/admin/delete_all_users.py --yes

There is no undo. Take a Cloud SQL backup first:
    gcloud sql backups create --instance edu-db --project <project>

Deleting the User row cascades to that student's projects, chats, documents,
quizzes, flashcards, papers, attempts, mastery and study plans. The sign-in
itself lives in Identity Platform, not here, so it is removed separately (see
the note printed at the end).
"""

import sys

from edu_db.models import User
from edu_db.session import get_session_factory


def main() -> int:
    if "--yes" not in sys.argv:
        print("Refusing to run without --yes. This permanently deletes every account.")
        return 1

    factory = get_session_factory()
    with factory() as db:
        users = db.query(User).all()
        if not users:
            print("No users to delete.")
            return 0

        print(f"Deleting {len(users)} account(s):")
        for user in users:
            print(f"  - {user.email or '(no email)'}  id={user.id}")

        for user in users:
            db.delete(user)
        db.commit()

    with factory() as db:
        left = db.query(User).count()

    print(f"\nDone. Accounts remaining in the database: {left}")
    print(
        "\nThe sign-ins still exist in Identity Platform. Until those are removed too, "
        "anyone who signs in with an old password gets a brand new, empty account."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
