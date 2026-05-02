"""add missing tables

Revision ID: e05dbce4cf09
Revises: a1b2c3d4e5f6
Create Date: 2026-05-02 16:51:58.095232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e05dbce4cf09'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workouts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        'exercises',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workout_id', sa.Integer(), sa.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
    )
    op.create_table(
        'planned_sets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('exercise_id', sa.Integer(), sa.ForeignKey('exercises.id', ondelete='CASCADE'), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
    )
    op.create_table(
        'workout_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workout_id', sa.Integer(), sa.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trainee_telegram_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'executed_sets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('workout_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('planned_set_id', sa.Integer(), sa.ForeignKey('planned_sets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actual_reps', sa.Integer(), nullable=True),
        sa.Column('actual_weight', sa.Float(), nullable=True),
    )
    op.create_table(
        'exercise_comments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('workout_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exercise_id', sa.Integer(), sa.ForeignKey('exercises.id', ondelete='CASCADE'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('exercise_comments')
    op.drop_table('executed_sets')
    op.drop_table('workout_sessions')
    op.drop_table('planned_sets')
    op.drop_table('exercises')
    op.drop_table('workouts')
