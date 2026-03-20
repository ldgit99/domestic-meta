"""Add extraction revisions table.

Revision ID: 20260320_0003
Revises: 20260320_0002
Create Date: 2026-03-20 00:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0003"
down_revision = "20260320_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_revisions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("extraction_result_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("search_request_id", sa.String(length=64), nullable=False),
        sa.Column("revision_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_extraction_revisions_extraction_result_id",
        "extraction_revisions",
        ["extraction_result_id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_revisions_candidate_id",
        "extraction_revisions",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_revisions_search_request_id",
        "extraction_revisions",
        ["search_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_revisions_search_request_id", table_name="extraction_revisions")
    op.drop_index("ix_extraction_revisions_candidate_id", table_name="extraction_revisions")
    op.drop_index("ix_extraction_revisions_extraction_result_id", table_name="extraction_revisions")
    op.drop_table("extraction_revisions")
