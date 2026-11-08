"""Weekly class sessions, and a role so an account can be a teacher

Revision ID: a7f3c91d2e58
Revises: e6a13c5d8b27
Create Date: 2026-11-08

Both new columns on users carry a server default, so the rows that already
exist get a value without a second pass. Every account becomes a student,
which is what every account currently is.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7f3c91d2e58"
down_revision: Union[str, Sequence[str], None] = "e6a13c5d8b27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(),
            nullable=False,
            server_default="student",
        ),
    )
    op.add_column("users", sa.Column("headline", sa.String(), nullable=True))

    op.create_table(
        "class_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_code", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        # SET NULL rather than CASCADE: deleting a teacher's account must not
        # silently delete the classes they were down to take. The timetable
        # keeps teacher_name, so the session still reads correctly and an
        # administrator can reassign it.
        sa.Column("teacher_id", sa.String(), nullable=True),
        sa.Column("teacher_name", sa.String(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("join_url", sa.String(), nullable=True),
        sa.Column(
            "meeting_source", sa.String(), nullable=False, server_default="manual"
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_class_sessions_subject_code", "class_sessions", ["subject_code"]
    )
    op.create_index("ix_class_sessions_grade", "class_sessions", ["grade"])
    op.create_index("ix_class_sessions_teacher_id", "class_sessions", ["teacher_id"])
    op.create_index("ix_class_sessions_starts_at", "class_sessions", ["starts_at"])
    # The query every student makes: their grade and subject, soonest first.
    op.create_index(
        "ix_class_sessions_timetable",
        "class_sessions",
        ["grade", "subject_code", "starts_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_class_sessions_timetable", table_name="class_sessions")
    op.drop_index("ix_class_sessions_starts_at", table_name="class_sessions")
    op.drop_index("ix_class_sessions_teacher_id", table_name="class_sessions")
    op.drop_index("ix_class_sessions_grade", table_name="class_sessions")
    op.drop_index("ix_class_sessions_subject_code", table_name="class_sessions")
    op.drop_table("class_sessions")
    op.drop_column("users", "headline")
    op.drop_column("users", "role")
