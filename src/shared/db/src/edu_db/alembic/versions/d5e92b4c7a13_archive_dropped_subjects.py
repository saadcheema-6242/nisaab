"""archive dropped subject workspaces

Revision ID: d5e92b4c7a13
Revises: c4d81a6f2b09
Create Date: 2026-11-05

A student who changes group drops subjects. Onboarding only ever added
workspaces and never removed them, so an ICS student who had started as
Pre-Medical ended up with all five subjects: Chemistry and Biology that they
will never sit, counted in their mastery and scheduled in their study plans.

Hidden rather than deleted. Somebody who spent a month on Chemistry notes
before switching should not lose them to a dropdown, and switching back
restores the subject with its work intact.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e92b4c7a13"
down_revision: Union[str, Sequence[str], None] = "c4d81a6f2b09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Almost every row is NULL and every listing filters on it, so the index
    # covers only the archived ones.
    op.create_index(
        "ix_projects_archived_at",
        "projects",
        ["archived_at"],
        postgresql_where=sa.text("archived_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_projects_archived_at", table_name="projects")
    op.drop_column("projects", "archived_at")
