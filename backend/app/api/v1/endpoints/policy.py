import hashlib
import re
from pathlib import PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import AnyHttpUrl
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.dependencies import AdminUser, CurrentUser, Database
from app.core.errors import APIError
from app.models import Document, DocumentChunk
from app.schemas.policy import (
    PolicyAnswerResponse,
    PolicyDocumentIngestResponse,
    PolicyDocumentRead,
    PolicyDocumentStatusUpdate,
    PolicyLanguage,
    PolicyQuestionRequest,
)
from app.services.policy_documents import (
    chunk_policy_pages,
    extract_policy_pages,
    read_policy_pdf,
)
from app.services.policy_embeddings import embed_texts
from app.services.policy_rag import answer_policy_question

router = APIRouter(prefix="/policy", tags=["Government policy explainer"])


@router.post(
    "/documents/upload",
    response_model=PolicyDocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_policy_document(
    db: Database,
    admin: AdminUser,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(min_length=3, max_length=240)],
    issuing_authority: Annotated[str, Form(min_length=2, max_length=180)],
    language: Annotated[PolicyLanguage, Form()] = "en",
    source_url: Annotated[AnyHttpUrl | None, Form()] = None,
    is_published: Annotated[bool, Form()] = False,
) -> PolicyDocumentIngestResponse:
    title = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", title)).strip()
    issuing_authority = re.sub(
        r"\s+",
        " ",
        re.sub(r"[\x00-\x1f\x7f]", " ", issuing_authority),
    ).strip()
    if len(title) < 3 or len(issuing_authority) < 2:
        raise APIError(
            422,
            "invalid_policy_metadata",
            "Provide a non-empty document title and issuing authority.",
        )

    pdf_bytes = await read_policy_pdf(file)
    pages = await run_in_threadpool(extract_policy_pages, pdf_bytes)
    chunks = await run_in_threadpool(chunk_policy_pages, pages)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No usable text chunks were extracted from the PDF.",
        )

    file_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    existing_document = db.scalar(
        select(Document.id).where(Document.file_sha256 == file_sha256)
    )
    if existing_document is not None:
        raise APIError(
            409,
            "duplicate_policy_document",
            "This PDF has already been uploaded.",
        )
    db.commit()

    vectors: list[list[float]] = []
    for batch_start in range(0, len(chunks), 32):
        batch = chunks[batch_start : batch_start + 32]
        vectors.extend(
            await embed_texts(
                [chunk.content for chunk in batch],
                task="RETRIEVAL_DOCUMENT",
            )
        )

    filename = PureWindowsPath(file.filename or "").name
    filename = re.sub(r"[\x00-\x1f]", "", filename).strip()[:255]
    if not filename:
        filename = "government-policy.pdf"
    document = Document(
        title=title,
        source_url=str(source_url) if source_url else None,
        issuing_authority=issuing_authority,
        language=language,
        document_type="policy_pdf",
        content="\n\n".join(f"[Page {page.page_number}]\n{page.content}" for page in pages),
        file_name=filename,
        file_sha256=file_sha256,
        page_count=len(pages),
        uploaded_by_id=admin.id,
        is_published=is_published,
    )
    db.add(document)
    db.flush()
    db.add_all(
        [
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
    )
    db.commit()
    db.refresh(document)

    return PolicyDocumentIngestResponse(
        document_id=document.id,
        title=document.title,
        file_name=filename,
        page_count=len(pages),
        chunk_count=len(chunks),
        embedding_provider=settings.ai_provider,
        is_published=document.is_published,
        message=(
            "Document processed and published."
            if document.is_published
            else "Document processed. An administrator must publish it before it can be used for answers."
        ),
    )


@router.get("/documents", response_model=list[PolicyDocumentRead])
def list_policy_documents(db: Database, user: CurrentUser) -> list[Document]:
    statement = select(Document).where(Document.file_sha256.is_not(None))
    if user.role != "admin":
        statement = statement.where(Document.is_published.is_(True))
    statement = statement.order_by(Document.created_at.desc()).limit(100)
    return list(db.scalars(statement).all())


@router.patch(
    "/documents/{document_id}/publication",
    response_model=PolicyDocumentRead,
)
def set_policy_document_publication(
    document_id: str,
    payload: PolicyDocumentStatusUpdate,
    db: Database,
    _: AdminUser,
) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.file_sha256 is None:
        raise APIError(404, "policy_document_not_found", "The policy document was not found.")
    document.is_published = payload.is_published
    db.commit()
    db.refresh(document)
    return document


@router.post("/ask", response_model=PolicyAnswerResponse)
async def ask_policy_question(
    payload: PolicyQuestionRequest,
    db: Database,
    _: CurrentUser,
) -> PolicyAnswerResponse:
    return await answer_policy_question(
        db,
        question=payload.question.strip(),
        language=payload.language,
    )
