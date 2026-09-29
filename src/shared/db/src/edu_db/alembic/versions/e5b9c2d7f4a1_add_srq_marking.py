"""add_srq_marking

Short-response questions (SRQs) with marking rubrics, students' written
answers with AI-estimated marks, and a partial-marks score on practice
records so written answers count towards SLO mastery.

Revision ID: e5b9c2d7f4a1
Revises: d8a3f1c6b2e4
Create Date: 2026-09-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b9c2d7f4a1'
down_revision: Union[str, Sequence[str], None] = 'd8a3f1c6b2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'srq_questions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('slo_code', sa.String(), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('marks', sa.Integer(), nullable=False),
        sa.Column('model_answer', sa.Text(), nullable=False),
        sa.Column('rubric', sa.JSON(), nullable=False),
        sa.Column('cognitive_level', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False, server_default='ai_generated'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_srq_questions_project_id', 'srq_questions', ['project_id'])
    op.create_index('ix_srq_questions_slo_code', 'srq_questions', ['slo_code'])
    op.create_table(
        'srq_attempts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('awarded_marks', sa.Float(), nullable=False),
        sa.Column('max_marks', sa.Integer(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['srq_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_srq_attempts_question_id', 'srq_attempts', ['question_id'])
    op.create_index('ix_srq_attempts_user_id', 'srq_attempts', ['user_id'])
    op.add_column('practice_records', sa.Column('score', sa.Float(), nullable=True))

    # Same lock-down as c7f2a5e8d3b1: the app reaches its tables only through the backend
    op.execute('ALTER TABLE public.srq_questions ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.srq_attempts ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('practice_records', 'score')
    op.drop_index('ix_srq_attempts_user_id', table_name='srq_attempts')
    op.drop_index('ix_srq_attempts_question_id', table_name='srq_attempts')
    op.drop_table('srq_attempts')
    op.drop_index('ix_srq_questions_slo_code', table_name='srq_questions')
    op.drop_index('ix_srq_questions_project_id', table_name='srq_questions')
    op.drop_table('srq_questions')
