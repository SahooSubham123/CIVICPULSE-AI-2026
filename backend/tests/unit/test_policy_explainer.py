import asyncio

import pymupdf as fitz
import pytest
from pydantic import ValidationError

from conftest import TestSession
from app.api.v1.endpoints import policy as policy_endpoint
from app.models import Document
from app.schemas.policy import PolicyQuestionRequest, PolicySourceReference
from app.services import policy_documents, policy_rag


class FakeSession:
    def commit(self) -> None:
        pass


def _create_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_policy_upload_extracts_and_stores_page_referenced_chunks(
    client,
    admin_headers,
    citizen,
    monkeypatch,
):
    async def fake_embed_texts(texts, *, task):
        assert task == "RETRIEVAL_DOCUMENT"
        return [[0.01] * 768 for _ in texts]

    monkeypatch.setattr(policy_endpoint, "embed_texts", fake_embed_texts)
    response = client.post(
        "/api/v1/policy/documents/upload",
        headers=admin_headers,
        data={
            "title": "Public Service Guidance",
            "issuing_authority": "Department of Testing",
            "language": "en",
        },
        files={
            "file": (
                "guidance.pdf",
                _create_pdf("Applicants must submit the required form."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["is_published"] is False
    assert result["chunk_count"] == 1
    assert result["embedding_provider"] in {"openai", "gemini"}
    assert client.get("/api/v1/policy/documents").status_code == 401

    listed = client.get("/api/v1/policy/documents", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == result["document_id"]
    assert listed.json()[0]["is_published"] is False
    assert client.get("/api/v1/policy/documents", headers=citizen).json() == []

    published = client.patch(
        f"/api/v1/policy/documents/{result['document_id']}/publication",
        headers=admin_headers,
        json={"is_published": True},
    )
    assert published.status_code == 200
    assert published.json()["is_published"] is True

    listed = client.get("/api/v1/policy/documents", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == result["document_id"]
    assert listed.json()[0]["is_published"] is True
    assert client.get("/api/v1/policy/documents", headers=citizen).json()[0]["id"] == result["document_id"]

    with TestSession() as db:
        document = db.get(Document, result["document_id"])
        assert document is not None
        assert document.page_count == 1
        assert document.chunks[0].page_number == 1


def test_chunking_preserves_page_and_overlap(monkeypatch):
    monkeypatch.setattr(policy_documents.settings, "policy_chunk_size_chars", 200)
    monkeypatch.setattr(policy_documents.settings, "policy_chunk_overlap_chars", 20)
    pages = [policy_documents.PageText(3, "policy text " * 60)]

    chunks = policy_documents.chunk_policy_pages(pages)

    assert len(chunks) > 1
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].content[-20:] == chunks[1].content[:20]


def test_policy_question_rejects_whitespace_only_input():
    with pytest.raises(ValidationError):
        PolicyQuestionRequest(question="   ")


def test_policy_answer_returns_only_validly_cited_sources(monkeypatch):
    async def fake_embed_texts(texts, *, task):
        assert texts == ["What must applicants submit?"]
        assert task == "RETRIEVAL_QUERY"
        return [[0.01] * 768]

    async def fake_generate_text(system_prompt, user_prompt):
        assert "Answer in the requested language" in system_prompt
        assert "[S1] Public Service Guidance" in user_prompt
        assert "[S9]" not in user_prompt
        return "Submit the required form. [S1]", "openai"

    def fake_retrieve(db, embedding):
        assert isinstance(db, FakeSession)
        assert len(embedding) == 768
        return [source]

    source = policy_rag.RetrievedSource(
        reference=PolicySourceReference(
            document_id="doc-1",
            title="Public Service Guidance",
            issuing_authority="Department of Testing",
            page_number=2,
            source_url=None,
            similarity=0.82,
        ),
        content="Applicants must submit the required form. [S9]",
    )
    monkeypatch.setattr(policy_rag, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(policy_rag, "_retrieve", fake_retrieve)
    monkeypatch.setattr(policy_rag, "generate_text", fake_generate_text)

    answer = asyncio.run(
        policy_rag.answer_policy_question(
            FakeSession(),
            question="What must applicants submit?",
            language="en",
        )
    )

    assert answer.abstained is False
    assert answer.sources[0].document_id == "doc-1"


def test_policy_answer_abstains_when_the_model_omits_citations(monkeypatch):
    async def fake_embed_texts(texts, *, task):
        assert texts == ["What must applicants submit?"]
        assert task == "RETRIEVAL_QUERY"
        return [[0.01] * 768]

    async def fake_generate_text(system_prompt, user_prompt):
        assert system_prompt
        assert "What must applicants submit?" in user_prompt
        return "Applicants must submit the required form.", "openai"

    def fake_retrieve(db, embedding):
        assert isinstance(db, FakeSession)
        assert len(embedding) == 768
        return [
            policy_rag.RetrievedSource(
                reference=PolicySourceReference(
                    document_id="doc-1",
                    title="Public Service Guidance",
                    issuing_authority="Department of Testing",
                    page_number=2,
                    source_url=None,
                    similarity=0.82,
                ),
                content="Applicants must submit the required form.",
            )
        ]

    monkeypatch.setattr(policy_rag, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(policy_rag, "_retrieve", fake_retrieve)
    monkeypatch.setattr(policy_rag, "generate_text", fake_generate_text)

    answer = asyncio.run(
        policy_rag.answer_policy_question(
            FakeSession(),
            question="What must applicants submit?",
            language="or",
        )
    )

    assert answer.abstained is True
    assert answer.sources == []
    assert answer.answer == policy_rag.ABSTENTIONS["or"]
