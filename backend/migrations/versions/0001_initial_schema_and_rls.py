"""Create CIVICPULSE application schema and RLS policies.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('citizen', 'admin')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "schemes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("department", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("benefit", sa.String(length=240), nullable=False),
        sa.Column("eligibility_criteria", sa.JSON(), nullable=False),
        sa.Column("application_url", sa.String(length=500), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schemes_name", "schemes", ["name"])
    op.create_index("ix_schemes_is_active", "schemes", ["is_active"])

    op.create_table(
        "government_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("issuing_authority", sa.String(length=180), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_government_documents_title", "government_documents", ["title"])
    op.create_index("ix_government_documents_is_published", "government_documents", ["is_published"])

    op.create_table(
        "grievances",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reference_number", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("department", sa.String(length=180), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('received', 'in_progress', 'resolved', 'rejected')",
            name="ck_grievances_status",
        ),
    )
    op.create_index("ix_grievances_reference_number", "grievances", ["reference_number"], unique=True)
    op.create_index("ix_grievances_user_id", "grievances", ["user_id"])
    op.create_index("ix_grievances_category", "grievances", ["category"])
    op.create_index("ix_grievances_status", "grievances", ["status"])

    op.create_table(
        "service_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("service_name", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'pending', 'completed', 'cancelled')",
            name="ck_service_tasks_status",
        ),
    )
    op.create_index("ix_service_tasks_user_id", "service_tasks", ["user_id"])
    op.create_index("ix_service_tasks_status", "service_tasks", ["status"])

    op.create_table(
        "verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("assessment", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("subject_type IN ('claim', 'image')", name="ck_verifications_subject_type"),
        sa.CheckConstraint(
            "assessment IN ('supported', 'contradicted', 'inconclusive', "
            "'needs_human_review', 'possible_manipulation_indicators')",
            name="ck_verifications_assessment",
        ),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_verifications_confidence"),
    )
    op.create_index("ix_verifications_user_id", "verifications", ["user_id"])

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'civicpulse_app') THEN
                CREATE ROLE civicpulse_app NOLOGIN NOBYPASSRLS;
            ELSE
                ALTER ROLE civicpulse_app NOBYPASSRLS;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT civicpulse_app TO %I', current_user);
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO civicpulse_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON users TO civicpulse_app"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON schemes, government_documents TO civicpulse_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON grievances TO civicpulse_app")
    op.execute("GRANT SELECT, INSERT ON service_tasks, verifications TO civicpulse_app")
    op.execute("REVOKE ALL ON users, schemes, government_documents, grievances, service_tasks, verifications FROM PUBLIC")
    op.execute(
        """
        DO $$
        DECLARE
            role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format(
                        'REVOKE ALL ON users, schemes, government_documents, grievances, service_tasks, verifications FROM %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )

    for table in (
        "users",
        "schemes",
        "government_documents",
        "grievances",
        "service_tasks",
        "verifications",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY users_select_self_or_admin ON users FOR SELECT TO civicpulse_app
        USING (id = NULLIF(current_setting('app.user_id', true), '')
            OR email = NULLIF(current_setting('app.login_email', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY users_insert_self_or_bootstrap_admin ON users FOR INSERT TO civicpulse_app
        WITH CHECK (id = NULLIF(current_setting('app.user_id', true), '')
            AND (role = 'citizen' OR current_setting('app.is_admin', true) = 'true'))
        """
    )
    op.execute(
        """
        CREATE POLICY users_update_self_or_admin ON users FOR UPDATE TO civicpulse_app
        USING (id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_admin', true) = 'true'
            OR (id = NULLIF(current_setting('app.user_id', true), '') AND role = 'citizen'))
        """
    )

    op.execute(
        """
        CREATE POLICY schemes_public_read ON schemes FOR SELECT TO civicpulse_app
        USING (is_active OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY schemes_admin_write ON schemes FOR ALL TO civicpulse_app
        USING (current_setting('app.is_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY documents_public_read ON government_documents FOR SELECT TO civicpulse_app
        USING (is_published OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY documents_admin_write ON government_documents FOR ALL TO civicpulse_app
        USING (current_setting('app.is_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY grievances_select_owner_admin_or_tracker ON grievances FOR SELECT TO civicpulse_app
        USING (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true'
            OR reference_number = NULLIF(current_setting('app.tracking_reference', true), ''))
        """
    )
    op.execute(
        """
        CREATE POLICY grievances_insert_owner_or_admin ON grievances FOR INSERT TO civicpulse_app
        WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY grievances_update_admin ON grievances FOR UPDATE TO civicpulse_app
        USING (current_setting('app.is_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY service_tasks_owner_admin ON service_tasks FOR ALL TO civicpulse_app
        USING (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        """
    )
    op.execute(
        """
        CREATE POLICY verifications_owner_admin ON verifications FOR ALL TO civicpulse_app
        USING (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')
            OR current_setting('app.is_admin', true) = 'true')
        """
    )


def downgrade() -> None:
    for table in (
        "verifications",
        "service_tasks",
        "grievances",
        "government_documents",
        "schemes",
        "users",
    ):
        op.drop_table(table)
