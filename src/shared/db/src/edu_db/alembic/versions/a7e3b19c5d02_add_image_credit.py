"""Store who a question's picture belongs to.

Pictures now come from openly licensed sources - Wikimedia Commons and the
like - instead of being generated. Those licences allow reuse on condition
that the author, the licence and the source are named wherever the picture
appears. So the credit has to travel with the picture, into the app, the PDF
and the Google Form, which means it has to be stored beside it.

JSON rather than a string: the parts are shown separately (the licence is a
link, the source is a link) and a pre-formatted line cannot be taken apart
again.

Revision ID: a7e3b19c5d02
Revises: d5a2c8e1f7b4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7e3b19c5d02"
down_revision: str | Sequence[str] | None = "d5a2c8e1f7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quiz_questions", sa.Column("image_credit", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("quiz_questions", "image_credit")
