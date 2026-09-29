"""add_practice_papers

FBISE-style practice papers (MCQs, SRQs, ERQs) with saved answers and results.

Revision ID: b3e8f5a1c9d2
Revises: a7d2e9c4f8b1
Create Date: 2026-09-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e8f5a1c9d2'
down_revision: Union[str, Sequence[str], None] = 'a7d2e9c4f8b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'practice_papers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('length', sa.String(), nullable=False),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=False),
        sa.Column('sections', sa.JSON(), nullable=False),
        sa.Column('total_marks', sa.Float(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='ready'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_practice_papers_project_id', 'practice_papers', ['project_id'])
    op.create_index('ix_practice_papers_user_id', 'practice_papers', ['user_id'])

    # Same lock-down as c7f2a5e8d3b1: the app reaches its tables only through the backend
    op.execute('ALTER TABLE public.practice_papers ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_practice_papers_user_id', table_name='practice_papers')
    op.drop_index('ix_practice_papers_project_id', table_name='practice_papers')
    op.drop_table('practice_papers')
