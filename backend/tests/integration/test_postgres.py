import os

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import set_rls_context
from app.models import Document, DocumentChunk, Grievance, Scheme, ServiceTask, User, Verification, new_id

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a migrated, disposable Supabase/PostgreSQL test database.",
)


def _test_engine():
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": os.getenv("TEST_DATABASE_SSL_MODE", "require")},
        pool_pre_ping=True,
    )
    @event.listens_for(engine, "connect")
    def assume_test_rls_role(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'SET ROLE "{settings.database_rls_role}"')
            cursor.execute("SET search_path TO public, extensions")
        finally:
            cursor.close()

    return engine


def test_supabase_postgres_connectivity():
    engine = _test_engine()
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            assert connection.dialect.name == "postgresql"
    finally:
        engine.dispose()


def test_postgres_models_crud_and_user_relationships():
    engine = _test_engine()
    admin_id = new_id()
    try:
        with Session(engine, expire_on_commit=False) as db:
            with db.begin():
                set_rls_context(db, user_id=admin_id, is_admin=True)
                user = User(
                    id=admin_id,
                    email=f"db-check-{admin_id}@example.test",
                    full_name="Database CRUD check",
                    password_hash="test-hash-not-for-authentication",
                    role="admin",
                )
                db.add(user)
                db.flush()

                scheme = Scheme(
                    name=f"Database CRUD check {admin_id[:8]}",
                    department="Test department",
                    description="Temporary row for a rolled-back database integration test.",
                    benefit="No real benefit",
                    eligibility_criteria=[],
                )
                document = Document(
                    title=f"Database CRUD check {admin_id[:8]}",
                    issuing_authority="Test authority",
                    content="Temporary test content.",
                    is_published=True,
                )
                grievance = Grievance(
                    user_id=user.id,
                    category="test",
                    title="Temporary database integration test",
                    description="This row must be rolled back after the integration check.",
                    location="Test environment",
                )
                service_task = ServiceTask(
                    user_id=user.id,
                    service_name="Database test plan",
                    steps=["Temporary test step"],
                )
                verification = Verification(
                    user_id=user.id,
                    subject="A test claim",
                    subject_type="claim",
                    assessment="inconclusive",
                    analysis="Temporary test analysis.",
                    sources=[],
                )
                db.add_all([scheme, document, grievance, service_task, verification])
                db.flush()
                chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    page_number=1,
                    content="Temporary policy chunk.",
                    embedding=[1 / 768] * 768,
                )
                db.add(chunk)
                db.flush()

                assert db.scalar(select(User).where(User.id == admin_id)).email == user.email
                assert db.scalar(select(Scheme).where(Scheme.id == scheme.id)).name == scheme.name
                assert db.scalar(select(Document).where(Document.id == document.id)).title == document.title
                cosine_distance = db.scalar(
                    select(DocumentChunk.embedding.cosine_distance([1 / 768] * 768)).where(
                        DocumentChunk.id == chunk.id
                    )
                )
                assert cosine_distance == pytest.approx(0, abs=1e-5)
                assert db.scalar(select(Grievance).where(Grievance.id == grievance.id)).owner.id == user.id
                assert db.scalar(select(ServiceTask).where(ServiceTask.id == service_task.id)).owner.id == user.id
                assert db.scalar(select(Verification).where(Verification.id == verification.id)).owner.id == user.id
    finally:
        engine.dispose()


def test_postgres_rls_isolates_citizen_grievances_and_allows_reference_tracking():
    engine = _test_engine()
    admin_id = new_id()
    citizen_id = new_id()
    other_citizen_id = new_id()
    own_reference = f"CP-{new_id().replace('-', '').upper()}"
    other_reference = f"CP-{new_id().replace('-', '').upper()}"
    try:
        with Session(engine, expire_on_commit=False) as db:
            with db.begin():
                set_rls_context(db, user_id=admin_id, is_admin=True)
                db.add_all(
                    [
                        User(
                            id=admin_id,
                            email=f"rls-admin-{admin_id}@example.test",
                            full_name="RLS integration test",
                            password_hash="test-hash",
                            role="admin",
                        ),
                        User(
                            id=citizen_id,
                            email=f"rls-citizen-{citizen_id}@example.test",
                            full_name="RLS citizen one",
                            password_hash="test-hash",
                            role="citizen",
                        ),
                        User(
                            id=other_citizen_id,
                            email=f"rls-citizen-{other_citizen_id}@example.test",
                            full_name="RLS citizen two",
                            password_hash="test-hash",
                            role="citizen",
                        ),
                    ]
                )
                db.flush()
                db.add_all(
                    [
                        Grievance(
                            reference_number=own_reference,
                            user_id=citizen_id,
                            category="test",
                            title="Own test grievance",
                            description="Temporary row for RLS integration.",
                            location="Test environment",
                        ),
                        Grievance(
                            reference_number=other_reference,
                            user_id=other_citizen_id,
                            category="test",
                            title="Other test grievance",
                            description="Temporary row for RLS integration.",
                            location="Test environment",
                        ),
                    ]
                )
                db.flush()
                published_document = Document(
                    title=f"Published policy {admin_id[:8]}",
                    issuing_authority="Test authority",
                    content="Published document text.",
                    is_published=True,
                )
                unpublished_document = Document(
                    title=f"Unpublished policy {admin_id[:8]}",
                    issuing_authority="Test authority",
                    content="Unpublished document text.",
                    is_published=False,
                )
                db.add_all([published_document, unpublished_document])
                db.flush()
                published_chunk = DocumentChunk(
                    document_id=published_document.id,
                    chunk_index=0,
                    page_number=1,
                    content="Published policy chunk.",
                    embedding=[1 / 768] * 768,
                )
                unpublished_chunk = DocumentChunk(
                    document_id=unpublished_document.id,
                    chunk_index=0,
                    page_number=1,
                    content="Unpublished policy chunk.",
                    embedding=[1 / 768] * 768,
                )
                db.add_all([published_chunk, unpublished_chunk])
                db.flush()

                set_rls_context(db, user_id=citizen_id)
                visible = db.scalars(select(Grievance)).all()
                assert [item.reference_number for item in visible] == [own_reference]
                visible_chunks = db.scalars(select(DocumentChunk)).all()
                assert [item.id for item in visible_chunks] == [published_chunk.id]

                set_rls_context(db, tracking_reference=other_reference)
                tracked = db.scalar(
                    select(Grievance).where(Grievance.reference_number == other_reference)
                )
                assert tracked is not None
                assert tracked.user_id == other_citizen_id
    finally:
        engine.dispose()
