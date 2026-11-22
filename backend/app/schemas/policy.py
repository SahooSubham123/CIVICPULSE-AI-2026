from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

PolicyLanguage = Literal["en", "hi", "or"]


class PolicyQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2_000)
    language: PolicyLanguage = "en"

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PolicySourceReference(BaseModel):
    document_id: str
    title: str
    issuing_authority: str
    page_number: int
    source_url: str | None = None
    similarity: float = Field(ge=0, le=1)


class PolicyAnswerResponse(BaseModel):
    answer: str
    language: PolicyLanguage
    sources: list[PolicySourceReference]
    abstained: bool
    disclaimer: str


class PolicyDocumentIngestResponse(BaseModel):
    document_id: str
    title: str
    file_name: str
    page_count: int
    chunk_count: int
    embedding_provider: str
    is_published: bool
    message: str


class PolicyDocumentStatusUpdate(BaseModel):
    is_published: bool


class PolicyDocumentRead(ORMModel):
    id: str
    title: str
    issuing_authority: str
    language: PolicyLanguage
    document_type: str
    source_url: str | None
    file_name: str | None
    file_sha256: str | None
    page_count: int | None
    is_published: bool
    created_at: datetime
