"""Add policy PDF metadata and pgvector document chunks.

Revision ID: 0002_policy_chunks
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_policy_chunks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")

    op.add_column(
        "government_documents",
        sa.Column("file_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "government_documents",
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "government_documents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "government_documents",
        sa.Column("uploaded_by_id", sa.String(length=36), nullable=True),
    )
    op.create_unique_constraint(
        "uq_government_documents_file_sha256",
        "government_documents",
        ["file_sha256"],
    )
    op.create_foreign_key(
        "fk_government_documents_uploaded_by_id_users",
        "government_documents",
        "users",
        ["uploaded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("government_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("page_number > 0", name="ck_document_chunks_page_number"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.execute("GRANT USAGE ON SCHEMA extensions TO civicpulse_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON document_chunks TO civicpulse_app")
    op.execute("REVOKE ALL ON document_chunks FROM PUBLIC")
    op.execute(
        """
        DO $$
        DECLARE
            role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON document_chunks FROM %I', role_name);
                END IF;
            END LOOP;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY document_chunks_published_read ON document_chunks FOR SELECT TO civicpulse_app
        USING (
            current_setting('app.is_admin', true) = 'true'
            OR EXISTS (
                SELECT 1
                FROM government_documents
                WHERE government_documents.id = document_chunks.document_id
                  AND government_documents.is_published
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY document_chunks_admin_write ON document_chunks FOR ALL TO civicpulse_app
        USING (current_setting('app.is_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_admin', true) = 'true')
        """
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_constraint(
        "fk_government_documents_uploaded_by_id_users",
        "government_documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_government_documents_file_sha256",
        "government_documents",
        type_="unique",
    )
    op.drop_column("government_documents", "uploaded_by_id")
    op.drop_column("government_documents", "page_count")
    op.drop_column("government_documents", "file_sha256")
    op.drop_column("government_documents", "file_name")
