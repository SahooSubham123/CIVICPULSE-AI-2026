from pydantic import AnyHttpUrl, BaseModel, Field

from app.schemas.common import Timestamped


class DocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    source_url: AnyHttpUrl | None = None
    issuing_authority: str = Field(min_length=2, max_length=180)
    language: str = Field(default="en", min_length=2, max_length=20)
    document_type: str = Field(default="guidance", max_length=80)
    content: str = Field(min_length=10, max_length=200_000)


class DocumentRead(Timestamped):
    id: str
    title: str
    source_url: str | None
    issuing_authority: str
    language: str
    document_type: str
    content: str
    is_published: bool
