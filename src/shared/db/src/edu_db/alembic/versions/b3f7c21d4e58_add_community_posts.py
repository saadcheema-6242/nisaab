"""add community posts

Revision ID: b3f7c21d4e58
Revises: a7e3b19c5d02
Create Date: 2026-11-03

A room per grade and group, so Pre-Medical XI and Pre-Engineering XI are
different rooms. Both are stored on the post rather than looked up from the
author's profile when it is read: a student who moves up to XII, or changes
group, must not drag last year's messages with them or rewrite the room they
left.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3f7c21d4e58"
down_revision: Union[str, Sequence[str], None] = "a7e3b19c5d02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_posts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("group_code", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_posts_user_id", "community_posts", ["user_id"])
    op.create_index("ix_community_posts_parent_id", "community_posts", ["parent_id"])
    # Every read is "this room, newest first", so the index matches it exactly
    op.create_index(
        "ix_community_posts_room",
        "community_posts",
        ["grade", "group_code", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_community_posts_room", table_name="community_posts")
    op.drop_index("ix_community_posts_parent_id", table_name="community_posts")
    op.drop_index("ix_community_posts_user_id", table_name="community_posts")
    op.drop_table("community_posts")
