"""add user suspension

Revision ID: c4d81a6f2b09
Revises: b3f7c21d4e58
Create Date: 2026-11-04

The dates are the whole state. banned_at says a ban was applied; banned_until
says when it lifts, and NULL there means it does not. No separate flag, because
a flag and a date eventually disagree - the temporary ban expires, the flag
stays true, and somebody is shut out permanently by accident.

Every column is nullable, so existing users are simply not banned.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d81a6f2b09"
down_revision: Union[str, Sequence[str], None] = "b3f7c21d4e58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("banned_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("ban_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("banned_by", sa.String(), nullable=True))
    # Every signed-in request checks this, and almost every row is NULL, so a
    # partial index keeps it small and only covers the rows that matter.
    op.create_index(
        "ix_users_banned_at",
        "users",
        ["banned_at"],
        postgresql_where=sa.text("banned_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_banned_at", table_name="users")
    op.drop_column("users", "banned_by")
    op.drop_column("users", "ban_reason")
    op.drop_column("users", "banned_until")
    op.drop_column("users", "banned_at")
