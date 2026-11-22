import re
from dataclasses import dataclass

import pymupdf as fitz
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


@dataclass(frozen=True)
class PageText:
    page_number: int
    content: str


@dataclass(frozen=True)
class PolicyChunk:
    page_number: int
    chunk_index: int
    content: str


async def read_policy_pdf(file: UploadFile) -> bytes:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a PDF document.",
        )

    content = await file.read(settings.policy_pdf_max_size_bytes + 1)
    if len(content) > settings.policy_pdf_max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The PDF exceeds the configured upload size limit.",
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )
    return content


def extract_policy_pages(pdf_bytes: bytes) -> list[PageText]:
    try:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF could not be opened.",
        ) from exc

    try:
        if pdf.needs_pass:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password-protected PDFs are not supported.",
            )
        if pdf.page_count == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The PDF has no pages.",
            )
        if pdf.page_count > settings.policy_pdf_max_pages:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The PDF exceeds the configured page limit.",
            )

        pages = []
        extracted_chars = 0
        for index, page in enumerate(pdf):
            page_text = page.get_text("text", sort=True).strip()
            extracted_chars += len(page_text)
            if extracted_chars > settings.policy_pdf_max_extracted_chars:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="The PDF exceeds the configured extracted-text limit.",
                )
            pages.append(PageText(index + 1, page_text))
    finally:
        pdf.close()

    if not any(page.content for page in pages):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No searchable text was found in the PDF. Scanned PDFs require OCR before upload.",
        )
    return pages


def chunk_policy_pages(pages: list[PageText]) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    chunk_index = 0
    chunk_size = settings.policy_chunk_size_chars
    overlap = settings.policy_chunk_overlap_chars

    for page in pages:
        normalized = re.sub(r"\s+", " ", page.content).strip()
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            content = normalized[start:end].strip()
            if content:
                chunks.append(
                    PolicyChunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )
                chunk_index += 1

            if end >= len(normalized):
                break
            start = max(start + 1, end - overlap)

    return chunks
