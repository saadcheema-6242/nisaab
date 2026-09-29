"""add_fbise_curriculum

FBISE curriculum (subjects, grade subjects, domains, SLOs), the student
profile filled in by onboarding, subject workspaces on projects, and SLO
codes on the practice items so mastery can be tracked per SLO.

Revision ID: d8a3f1c6b2e4
Revises: c7f2a5e8d3b1
Create Date: 2026-09-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3f1c6b2e4'
down_revision: Union[str, Sequence[str], None] = 'c7f2a5e8d3b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_TABLES = ['subjects', 'grade_subjects', 'curriculum_domains', 'slos', 'student_profiles']
SLO_TAGGED = ['flashcard_groups', 'flashcards', 'quizzes', 'quiz_questions', 'practice_records']


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'subjects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('has_practical', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'grade_subjects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('subject_id', sa.String(), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('scheme', sa.String(), nullable=False),
        sa.Column('curriculum', sa.String(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='coming_soon'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subject_id', 'grade', 'scheme'),
    )
    op.create_index('ix_grade_subjects_subject_id', 'grade_subjects', ['subject_id'])
    op.create_table(
        'curriculum_domains',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('grade_subject_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['grade_subject_id'], ['grade_subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grade_subject_id', 'code'),
    )
    op.create_index('ix_curriculum_domains_grade_subject_id', 'curriculum_domains', ['grade_subject_id'])
    op.create_table(
        'slos',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('grade_subject_id', sa.String(), nullable=False),
        sa.Column('domain_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('content_area', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('assessment_form', sa.String(), nullable=False),
        sa.Column('cognitive_levels', sa.JSON(), nullable=False),
        sa.Column('periods', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['grade_subject_id'], ['grade_subjects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['domain_id'], ['curriculum_domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grade_subject_id', 'code'),
    )
    op.create_index('ix_slos_grade_subject_id', 'slos', ['grade_subject_id'])
    op.create_index('ix_slos_domain_id', 'slos', ['domain_id'])
    op.create_index('ix_slos_code', 'slos', ['code'])
    op.create_table(
        'student_profiles',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('group_code', sa.String(), nullable=False),
        sa.Column('explanation_language', sa.String(), nullable=False, server_default='en'),
        sa.Column('exam_year', sa.Integer(), nullable=True),
        sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.add_column('projects', sa.Column('kind', sa.String(), nullable=False, server_default='custom'))
    op.add_column('projects', sa.Column('grade_subject_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_projects_grade_subject_id', 'projects', 'grade_subjects',
        ['grade_subject_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_projects_grade_subject_id', 'projects', ['grade_subject_id'])

    for table in SLO_TAGGED:
        op.add_column(table, sa.Column('slo_code', sa.String(), nullable=True))
        op.create_index(f'ix_{table}_slo_code', table, ['slo_code'])
    op.add_column('quiz_questions', sa.Column('cognitive_level', sa.String(), nullable=True))

    # Same lock-down as c7f2a5e8d3b1: the app reaches its tables only through the backend
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quiz_questions', 'cognitive_level')
    for table in reversed(SLO_TAGGED):
        op.drop_index(f'ix_{table}_slo_code', table_name=table)
        op.drop_column(table, 'slo_code')

    op.drop_index('ix_projects_grade_subject_id', table_name='projects')
    op.drop_constraint('fk_projects_grade_subject_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'grade_subject_id')
    op.drop_column('projects', 'kind')

    op.drop_table('student_profiles')
    op.drop_index('ix_slos_code', table_name='slos')
    op.drop_index('ix_slos_domain_id', table_name='slos')
    op.drop_index('ix_slos_grade_subject_id', table_name='slos')
    op.drop_table('slos')
    op.drop_index('ix_curriculum_domains_grade_subject_id', table_name='curriculum_domains')
    op.drop_table('curriculum_domains')
    op.drop_index('ix_grade_subjects_subject_id', table_name='grade_subjects')
    op.drop_table('grade_subjects')
    op.drop_table('subjects')
