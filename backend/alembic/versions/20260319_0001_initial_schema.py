"""Initial relational schema for domestic-meta.

Revision ID: 20260319_0001
Revises:
Create Date: 2026-03-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_requests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("expanded_keywords", sa.JSON(), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=False),
        sa.Column("year_to", sa.Integer(), nullable=False),
        sa.Column("include_theses", sa.Boolean(), nullable=False),
        sa.Column("include_journal_articles", sa.Boolean(), nullable=False),
        sa.Column("inclusion_rules", sa.JSON(), nullable=False),
        sa.Column("exclusion_rules", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )

    op.create_table(
        "candidate_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("search_request_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("journal_or_school", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("duplicate_group_id", sa.String(length=64), nullable=True),
        sa.Column("canonical_record_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_candidate_records_search_request_id",
        "candidate_records",
        ["search_request_id"],
        unique=False,
    )

    op.create_table(
        "eligibility_decisions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_record_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("reviewed_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_eligibility_decisions_candidate_record_id",
        "eligibility_decisions",
        ["candidate_record_id"],
        unique=False,
    )

    op.create_table(
        "prisma_counts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("search_request_id", sa.String(length=64), nullable=False),
        sa.Column("identified_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_screened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_excluded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_sought_for_retrieval", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_not_retrieved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_assessed_for_eligibility", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_excluded_with_reasons_json", sa.JSON(), nullable=False),
        sa.Column("studies_included_in_review", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_prisma_counts_search_request_id", "prisma_counts", ["search_request_id"], unique=True)

    op.create_table(
        "full_text_artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_record_id", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("text_extraction_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_full_text_artifacts_candidate_record_id",
        "full_text_artifacts",
        ["candidate_record_id"],
        unique=True,
    )

    op.create_table(
        "extraction_results",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_extraction_results_candidate_id",
        "extraction_results",
        ["candidate_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_results_candidate_id", table_name="extraction_results")
    op.drop_table("extraction_results")

    op.drop_index("ix_full_text_artifacts_candidate_record_id", table_name="full_text_artifacts")
    op.drop_table("full_text_artifacts")

    op.drop_index("ix_prisma_counts_search_request_id", table_name="prisma_counts")
    op.drop_table("prisma_counts")

    op.drop_index("ix_eligibility_decisions_candidate_record_id", table_name="eligibility_decisions")
    op.drop_table("eligibility_decisions")

    op.drop_index("ix_candidate_records_search_request_id", table_name="candidate_records")
    op.drop_table("candidate_records")

    op.drop_table("search_requests")
