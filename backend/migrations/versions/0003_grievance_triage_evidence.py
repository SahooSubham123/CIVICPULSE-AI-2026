"""Add grievance evidence, location, AI triage, and human review fields.

Revision ID: 0003_grievance_triage
Revises: 0002_policy_chunks
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_grievance_triage"
down_revision = "0002_policy_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("grievances", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("grievances", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("grievances", sa.Column("evidence_image", sa.LargeBinary(), nullable=True))
    op.add_column("grievances", sa.Column("evidence_content_type", sa.String(length=40), nullable=True))
    op.add_column("grievances", sa.Column("evidence_filename", sa.String(length=255), nullable=True))
    op.add_column("grievances", sa.Column("ai_suggested_category", sa.String(length=80), nullable=True))
    op.add_column("grievances", sa.Column("ai_suggested_priority", sa.String(length=20), nullable=True))
    op.add_column("grievances", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("grievances", sa.Column("ai_rationale", sa.Text(), nullable=True))
    op.add_column(
        "grievances",
        sa.Column("ai_triage_status", sa.String(length=20), nullable=False, server_default="unavailable"),
    )
    op.add_column(
        "grievances",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
    )
    op.add_column(
        "grievances",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column("grievances", sa.Column("reviewed_by_id", sa.String(length=36), nullable=True))
    op.add_column("grievances", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_grievances_reviewed_by_id_users",
        "grievances",
        "users",
        ["reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_grievances_priority", "grievances", ["priority"])
    op.create_index("ix_grievances_review_status", "grievances", ["review_status"])
    op.create_check_constraint(
        "ck_grievances_priority",
        "grievances",
        "priority IN ('low', 'medium', 'high', 'urgent')",
    )
    op.create_check_constraint(
        "ck_grievances_ai_priority",
        "grievances",
        "ai_suggested_priority IS NULL OR ai_suggested_priority IN ('low', 'medium', 'high', 'urgent')",
    )
    op.create_check_constraint(
        "ck_grievances_review_status",
        "grievances",
        "review_status IN ('pending', 'reviewed')",
    )
    op.create_check_constraint(
        "ck_grievances_coordinates",
        "grievances",
        "(latitude IS NULL OR latitude BETWEEN -90 AND 90) "
        "AND (longitude IS NULL OR longitude BETWEEN -180 AND 180)",
    )
    op.create_check_constraint(
        "ck_grievances_ai_confidence",
        "grievances",
        "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
    )
    op.create_check_constraint(
        "ck_grievances_ai_triage_status",
        "grievances",
        "ai_triage_status IN ('completed', 'unavailable')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_grievances_ai_triage_status", "grievances", type_="check")
    op.drop_constraint("ck_grievances_ai_confidence", "grievances", type_="check")
    op.drop_constraint("ck_grievances_coordinates", "grievances", type_="check")
    op.drop_constraint("ck_grievances_review_status", "grievances", type_="check")
    op.drop_constraint("ck_grievances_ai_priority", "grievances", type_="check")
    op.drop_constraint("ck_grievances_priority", "grievances", type_="check")
    op.drop_index("ix_grievances_review_status", table_name="grievances")
    op.drop_index("ix_grievances_priority", table_name="grievances")
    op.drop_constraint("fk_grievances_reviewed_by_id_users", "grievances", type_="foreignkey")
    for column in (
        "reviewed_at",
        "reviewed_by_id",
        "review_status",
        "priority",
        "ai_triage_status",
        "ai_rationale",
        "ai_confidence",
        "ai_suggested_priority",
        "ai_suggested_category",
        "evidence_filename",
        "evidence_content_type",
        "evidence_image",
        "longitude",
        "latitude",
    ):
        op.drop_column("grievances", column)
