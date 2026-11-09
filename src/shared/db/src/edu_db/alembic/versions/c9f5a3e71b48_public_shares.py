"""Public, read-only shares of a quiz or a paper

Revision ID: c9f5a3e71b48
Revises: b8e4d21f6c39
Create Date: 2026-11-09

The table behind a link anybody can open without signing in. The token is
unique and indexed because every read of this table starts with it, and
because two shares with the same token would mean one student opening
another's work.

No foreign key to the quiz or the paper: a share points at one of two
tables, and the kind decides which. The service checks the target still
exists when the link is opened, so a deleted quiz reads as an expired
link rather than a crash.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f5a3e71b48"
down_revision: Union[str, Sequence[str], None] = "b8e4d21f6c39"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shares",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "opened_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shares_token"), "shares", ["token"], unique=True)
    op.create_index(op.f("ix_shares_kind"), "shares", ["kind"], unique=False)
    op.create_index(
        op.f("ix_shares_target_id"), "shares", ["target_id"], unique=False
    )
    op.create_index(op.f("ix_shares_user_id"), "shares", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shares_user_id"), table_name="shares")
    op.drop_index(op.f("ix_shares_target_id"), table_name="shares")
    op.drop_index(op.f("ix_shares_kind"), table_name="shares")
    op.drop_index(op.f("ix_shares_token"), table_name="shares")
    op.drop_table("shares")
