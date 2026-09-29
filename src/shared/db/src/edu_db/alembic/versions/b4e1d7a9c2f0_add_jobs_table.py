"""add_jobs_table

Background jobs for the worker, replacing the Azure Storage Queue.

Revision ID: b4e1d7a9c2f0
Revises: 12d284c3be7b
Create Date: 2026-09-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e1d7a9c2f0'
down_revision: Union[str, Sequence[str], None] = '12d284c3be7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('run_after', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_jobs_type', 'jobs', ['type'])
    op.create_index('ix_jobs_status_run_after', 'jobs', ['status', 'run_after'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jobs_status_run_after', table_name='jobs')
    op.drop_index('ix_jobs_type', table_name='jobs')
    op.drop_table('jobs')
