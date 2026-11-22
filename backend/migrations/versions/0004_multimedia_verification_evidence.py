"""Extend verification records with evidence and multimedia transcripts.

Revision ID: 0004_verification_media
Revises: 0003_grievance_triage
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_verification_media"
down_revision = "0003_grievance_triage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_verifications_subject_type", "verifications", type_="check")
    op.create_check_constraint(
        "ck_verifications_subject_type",
        "verifications",
        "subject_type IN ('claim', 'image', 'audio', 'video')",
    )
    op.add_column(
        "verifications",
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("verifications", sa.Column("transcript", sa.Text(), nullable=True))
    op.add_column(
        "verifications",
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "verifications",
        sa.Column("limitations", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("verifications", "limitations")
    op.drop_column("verifications", "provider")
    op.drop_column("verifications", "transcript")
    op.drop_column("verifications", "evidence")
    op.drop_constraint("ck_verifications_subject_type", "verifications", type_="check")
    op.create_check_constraint(
        "ck_verifications_subject_type",
        "verifications",
        "subject_type IN ('claim', 'image')",
    )
