"""community moderation, attachments and polls

Revision ID: e6a13c5d8b27
Revises: d5e92b4c7a13
Create Date: 2026-11-07

The class room was a wall of text with no way to take anything down. A
student could delete their own post and nobody else could delete anything,
including an administrator. Combined with no rate limit, that meant one
person could fill a room with things that could not be removed.

This adds the four parts of moderation - a report button, an administrator
who can delete, a model that reads every post, and a warning sent to the
author - and the things students actually want: photos, files, voice notes
and polls.

The review is stored on the post rather than in its own table. Every post
has exactly one, and the administrator's queue sorts by severity, so a
separate table would mean a join on every row of every page.

review_severity defaults to 0 and is indexed, because the one query that has
to stay fast is "what needs looking at", and it runs over every post in the
system rather than one room.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6a13c5d8b27"
down_revision: Union[str, Sequence[str], None] = "d5e92b4c7a13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- what the model made of each post -------------------------------
    # Nullable on purpose. Null means never reviewed, which is not the same
    # as reviewed and clean: posts written before today have no verdict, and
    # so do posts written while Vertex was unreachable. The admin page
    # distinguishes them, because treating "never looked at" as "fine" is
    # how something sits unnoticed for a month.
    op.add_column(
        "community_posts", sa.Column("review_finding", sa.String(), nullable=True)
    )
    op.add_column(
        "community_posts", sa.Column("review_confidence", sa.Float(), nullable=True)
    )
    op.add_column(
        "community_posts", sa.Column("review_why", sa.Text(), nullable=True)
    )
    op.add_column(
        "community_posts",
        sa.Column(
            "review_severity", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "community_posts",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_posts", sa.Column("reviewed_by", sa.String(), nullable=True)
    )
    op.add_column(
        "community_posts",
        sa.Column("warned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_posts", sa.Column("warning_text", sa.Text(), nullable=True)
    )
    op.add_column(
        "community_posts",
        sa.Column("warning_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "community_posts", sa.Column("poll_question", sa.Text(), nullable=True)
    )

    op.create_index(
        "ix_community_posts_review_finding", "community_posts", ["review_finding"]
    )
    # The administrator's queue is "worst first, newest first" over every
    # post in the system. Without this it is a sort over the whole table
    # every time the page is opened.
    op.create_index(
        "ix_community_posts_review_severity", "community_posts", ["review_severity"]
    )

    # --- attachments -----------------------------------------------------
    op.create_table(
        "community_attachments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_community_attachments_post_id", "community_attachments", ["post_id"]
    )

    # --- polls -----------------------------------------------------------
    op.create_table(
        "community_poll_options",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_community_poll_options_post_id", "community_poll_options", ["post_id"]
    )

    op.create_table(
        "community_poll_votes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("option_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["option_id"], ["community_poll_options.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # One vote each, enforced here rather than in code. Two quick taps
        # race past an application-level check, and a poll that can be
        # stuffed is not a poll.
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_poll_one_vote"),
    )
    op.create_index(
        "ix_community_poll_votes_post_id", "community_poll_votes", ["post_id"]
    )
    op.create_index(
        "ix_community_poll_votes_option_id", "community_poll_votes", ["option_id"]
    )
    op.create_index(
        "ix_community_poll_votes_user_id", "community_poll_votes", ["user_id"]
    )

    # --- reports ---------------------------------------------------------
    op.create_table(
        "community_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # One report per student per post, so a single person cannot make a
        # post look urgent by tapping it repeatedly. The count is a signal.
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_report_once"),
    )
    op.create_index(
        "ix_community_reports_post_id", "community_reports", ["post_id"]
    )
    op.create_index(
        "ix_community_reports_user_id", "community_reports", ["user_id"]
    )
    op.create_index(
        "ix_community_reports_created_at", "community_reports", ["created_at"]
    )

    # --- how many posts a student has written today ----------------------
    # Every other expensive action already has a daily cap. Posting had
    # none, and with nothing removable that was the shape of a real problem.
    op.add_column(
        "user_usage",
        sa.Column(
            "community_posts_today",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_usage", "community_posts_today")

    op.drop_index("ix_community_reports_created_at", table_name="community_reports")
    op.drop_index("ix_community_reports_user_id", table_name="community_reports")
    op.drop_index("ix_community_reports_post_id", table_name="community_reports")
    op.drop_table("community_reports")

    op.drop_index("ix_community_poll_votes_user_id", table_name="community_poll_votes")
    op.drop_index(
        "ix_community_poll_votes_option_id", table_name="community_poll_votes"
    )
    op.drop_index("ix_community_poll_votes_post_id", table_name="community_poll_votes")
    op.drop_table("community_poll_votes")

    op.drop_index(
        "ix_community_poll_options_post_id", table_name="community_poll_options"
    )
    op.drop_table("community_poll_options")

    op.drop_index(
        "ix_community_attachments_post_id", table_name="community_attachments"
    )
    op.drop_table("community_attachments")

    op.drop_index("ix_community_posts_review_severity", table_name="community_posts")
    op.drop_index("ix_community_posts_review_finding", table_name="community_posts")
    for column in (
        "poll_question",
        "warning_seen_at",
        "warning_text",
        "warned_at",
        "reviewed_by",
        "reviewed_at",
        "review_severity",
        "review_why",
        "review_confidence",
        "review_finding",
    ):
        op.drop_column("community_posts", column)
