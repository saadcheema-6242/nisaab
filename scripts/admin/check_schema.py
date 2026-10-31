"""Report the database's migration state and the columns a feature needs.

Run with:
    bash deploy/gcp/deploy.sh script scripts/admin/check_schema.py

Reads only. Useful after a deploy to confirm a migration actually ran, rather
than inferring it from a job that exited zero.
"""

import sys

from edu_db.session import get_session_factory, init_db
from sqlalchemy import text

WANTED = {
    "quiz_questions": ["image_path", "image_alt", "option_images"],
}


def main() -> int:
    import os

    init_db(os.environ["DATABASE_URL"])
    with get_session_factory()() as db:
        version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"alembic head in the database: {version}")
        print()

        missing = 0
        for table, columns in WANTED.items():
            present = {
                row[0]
                for row in db.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t"
                    ),
                    {"t": table},
                )
            }
            for column in columns:
                ok = column in present
                missing += not ok
                print(f"  {'ok  ' if ok else 'MISS'}  {table}.{column}")

    print()
    if missing:
        print(f"{missing} column(s) missing - the migration has not run.")
        return 1
    print("Every column this feature needs is present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
