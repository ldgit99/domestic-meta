"""Add pipeline event log table.

Revision ID: 20260320_0002
Revises: 20260319_0001
Create Date: 2026-03-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0002"
down_revision = "20260319_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("search_request_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_pipeline_events_search_request_id", "pipeline_events", ["search_request_id"], unique=False)
    op.create_index("ix_pipeline_events_candidate_id", "pipeline_events", ["candidate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pipeline_events_candidate_id", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_search_request_id", table_name="pipeline_events")
    op.drop_table("pipeline_events")
