"""add_content_bank

Shared, teacher-reviewed content per SLO (explainers, MCQs, SRQs) so practice
can start instantly with reviewed material.

Revision ID: f1c4a8e2b6d3
Revises: e5b9c2d7f4a1
Create Date: 2026-09-26 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1c4a8e2b6d3'
down_revision: Union[str, Sequence[str], None] = 'e5b9c2d7f4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'content_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('grade_subject_id', sa.String(), nullable=False),
        sa.Column('slo_code', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('review_status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(), nullable=False, server_default='ai_generated'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['grade_subject_id'], ['grade_subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_items_slo', 'content_items', ['grade_subject_id', 'slo_code', 'kind'])
    op.create_index('ix_content_items_review_status', 'content_items', ['review_status'])

    # Same lock-down as c7f2a5e8d3b1: the app reaches its tables only through the backend
    op.execute('ALTER TABLE public.content_items ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_content_items_review_status', table_name='content_items')
    op.drop_index('ix_content_items_slo', table_name='content_items')
    op.drop_table('content_items')
