"""Let the answer options carry pictures of their own.

Some questions are answered by choosing between pictures - which structure is
benzene, which graph shows uniform acceleration - so the options need images,
not only the question.

Revision ID: d5a2c8e1f7b4
Revises: c4f1a7b2e6d3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5a2c8e1f7b4"
down_revision: str | Sequence[str] | None = "c4f1a7b2e6d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quiz_questions", sa.Column("option_images", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("quiz_questions", "option_images")
