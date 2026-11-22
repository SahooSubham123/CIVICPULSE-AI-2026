from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('citizen', 'admin')", name="ck_users_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="citizen", index=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    grievances: Mapped[list["Grievance"]] = relationship(
        back_populates="owner",
        foreign_keys="Grievance.user_id",
    )
    service_tasks: Mapped[list["ServiceTask"]] = relationship(back_populates="owner")
    verifications: Mapped[list["Verification"]] = relationship(back_populates="owner")


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180), index=True)
    department: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    benefit: Mapped[str] = mapped_column(String(240))
    eligibility_criteria: Mapped[list] = mapped_column(JSON, default=list)
    application_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Document(Base):
    __tablename__ = "government_documents"
    __table_args__ = (
        UniqueConstraint("file_sha256", name="uq_government_documents_file_sha256"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    issuing_authority: Mapped[str] = mapped_column(String(180))
    language: Mapped[str] = mapped_column(String(20), default="en")
    document_type: Mapped[str] = mapped_column(String(80), default="guidance")
    content: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_government_documents_uploaded_by_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    uploader: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_id])


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("page_number > 0", name="ck_document_chunks_page_number"),
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("government_documents.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(768).with_variant(JSON(), "sqlite"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[Document] = relationship(back_populates="chunks")

class Grievance(Base):
    __tablename__ = "grievances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('received', 'in_progress', 'resolved', 'rejected')",
            name="ck_grievances_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_grievances_priority",
        ),
        CheckConstraint(
            "ai_suggested_priority IS NULL OR ai_suggested_priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_grievances_ai_priority",
        ),
        CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
            name="ck_grievances_ai_confidence",
        ),
        CheckConstraint(
            "ai_triage_status IN ('completed', 'unavailable')",
            name="ck_grievances_ai_triage_status",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'reviewed')",
            name="ck_grievances_review_status",
        ),
        CheckConstraint(
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90) "
            "AND (longitude IS NULL OR longitude BETWEEN -180 AND 180)",
            name="ck_grievances_coordinates",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference_number: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
        default=lambda: f"CP-{uuid4().hex.upper()}",
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(240))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    evidence_content_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    evidence_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_suggested_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_suggested_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_triage_status: Mapped[str] = mapped_column(String(20), default="unavailable")
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    department: Mapped[str | None] = mapped_column(String(180), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner: Mapped[User] = relationship(back_populates="grievances", foreign_keys=[user_id])


class ServiceTask(Base):
    __tablename__ = "service_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'pending', 'completed', 'cancelled')",
            name="ck_service_tasks_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    service_name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="service_tasks")


class Verification(Base):
    __tablename__ = "verifications"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('claim', 'image', 'audio', 'video')",
            name="ck_verifications_subject_type",
        ),
        CheckConstraint(
            "assessment IN ('supported', 'contradicted', 'inconclusive', "
            "'needs_human_review', 'possible_manipulation_indicators')",
            name="ck_verifications_assessment",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_verifications_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(Text)
    subject_type: Mapped[str] = mapped_column(String(20), default="claim")
    assessment: Mapped[str] = mapped_column(String(40), default="inconclusive")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(40), default="unknown")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="verifications")
