"""Let a quiz question carry a diagram.

Some questions cannot be asked in words - a free-body diagram, a circuit, a
velocity-time graph. The image is drawn from a typed spec and stored as an
object; this records where it lives and what it shows.

Revision ID: c4f1a7b2e6d3
Revises: b3e8f5a1c9d2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4f1a7b2e6d3"
down_revision: str | Sequence[str] | None = "b3e8f5a1c9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("quiz_questions", sa.Column("image_path", sa.String(), nullable=True))
    op.add_column("quiz_questions", sa.Column("image_alt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("quiz_questions", "image_alt")
    op.drop_column("quiz_questions", "image_path")
