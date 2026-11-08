"""Teacher accounts: what they teach, and when an administrator approved them

Revision ID: b8e4d21f6c39
Revises: a7f3c91d2e58
Create Date: 2026-11-08

Nothing is backfilled. Every account that exists today is a student with
role 'student' already, and teacher_approved_at stays NULL for all of them,
which is exactly right: nobody has been approved, because until now there
was nothing to approve.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4d21f6c39"
down_revision: Union[str, Sequence[str], None] = "a7f3c91d2e58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("teacher_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users", sa.Column("teacher_approved_by", sa.String(), nullable=True)
    )

    op.create_table(
        "teacher_profiles",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("subjects", sa.JSON(), nullable=False),
        sa.Column("grades", sa.JSON(), nullable=False),
        sa.Column("school", sa.String(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column(
            "applied_at",
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
        # CASCADE, unlike class_sessions.teacher_id: a profile describes an
        # account and is meaningless without it, whereas a class happened and
        # should survive the teacher leaving.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # The administrator's queue: teachers waiting, oldest first. A partial
    # index, because the rows that matter are the few with no approval date,
    # not the many with one.
    op.create_index(
        "ix_users_awaiting_approval",
        "users",
        ["role"],
        postgresql_where=sa.text("teacher_approved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_awaiting_approval", table_name="users")
    op.drop_table("teacher_profiles")
    op.drop_column("users", "teacher_approved_by")
    op.drop_column("users", "teacher_approved_at")
