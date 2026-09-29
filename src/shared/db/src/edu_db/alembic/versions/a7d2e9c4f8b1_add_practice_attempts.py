"""add_practice_attempts

Finished attempts at quizzes, flashcard sets and practice papers, so results
can be shown again (e.g. the quiz card inside a chat).

Revision ID: a7d2e9c4f8b1
Revises: f1c4a8e2b6d3
Create Date: 2026-09-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d2e9c4f8b1'
down_revision: Union[str, Sequence[str], None] = 'f1c4a8e2b6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'practice_attempts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('ref_id', sa.String(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('max_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_practice_attempts_ref', 'practice_attempts', ['user_id', 'kind', 'ref_id'])
    op.create_index('ix_practice_attempts_project_id', 'practice_attempts', ['project_id'])

    # Same lock-down as c7f2a5e8d3b1: the app reaches its tables only through the backend
    op.execute('ALTER TABLE public.practice_attempts ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_practice_attempts_project_id', table_name='practice_attempts')
    op.drop_index('ix_practice_attempts_ref', table_name='practice_attempts')
    op.drop_table('practice_attempts')
