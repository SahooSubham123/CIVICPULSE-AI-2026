from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select

from app.core.dependencies import Database, require_admin
from app.core.errors import APIError
from app.models import Document
from app.schemas.common import PaginatedResponse
from app.schemas.documents import DocumentCreate, DocumentRead

router = APIRouter(prefix="/documents", tags=["Government documents"])


@router.get("", response_model=PaginatedResponse[DocumentRead])
def list_documents(
    db: Database,
    query: str | None = None,
    language: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(Document).where(Document.is_published.is_(True))
    count_statement = select(func.count()).select_from(Document).where(Document.is_published.is_(True))
    if query:
        statement = statement.where(Document.title.ilike(f"%{query}%"))
        count_statement = count_statement.where(Document.title.ilike(f"%{query}%"))
    if language:
        statement = statement.where(Document.language == language)
        count_statement = count_statement.where(Document.language == language)
    items = db.scalars(statement.order_by(Document.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": db.scalar(count_statement) or 0, "limit": limit, "offset": offset}


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Database) -> Document:
    document = db.get(Document, document_id)
    if document is None or not document.is_published:
        raise APIError(404, "document_not_found", "The requested document was not found.")
    return document


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_document(payload: DocumentCreate, db: Database) -> Document:
    document = Document(**payload.model_dump(mode="json"), is_published=True)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
