import asyncio
import math
from typing import Literal

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

EMBEDDING_DIMENSIONS = 768
EmbeddingTask = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]


def _validate_vectors(vectors: list[list[float]], expected_count: int) -> list[list[float]]:
    if len(vectors) != expected_count:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The embedding provider returned an unexpected number of vectors.",
        )
    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSIONS or not all(
            math.isfinite(value) for value in vector
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The embedding provider returned an invalid vector.",
            )
        if not any(value != 0 for value in vector):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The embedding provider returned a zero vector.",
            )
    return vectors


async def embed_texts(
    texts: list[str],
    *,
    task: EmbeddingTask,
) -> list[list[float]]:
    if not texts:
        return []
    if settings.ai_provider == "openai":
        return await _embed_openai(texts)
    return await _embed_gemini(texts, task=task)


async def _embed_openai(texts: list[str]) -> list[list[float]]:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI embeddings are not configured.",
        )

    headers = {"Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"}
    payload = {
        "model": settings.openai_embedding_model,
        "input": texts,
        "dimensions": EMBEDDING_DIMENSIONS,
        "encoding_format": "float",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("The embedding response is missing its data list.")
            data = payload["data"]
            if any(
                not isinstance(item, dict)
                or "index" not in item
                or "embedding" not in item
                for item in data
            ):
                raise ValueError("The embedding response contains an invalid item.")
            data.sort(key=lambda item: item["index"])
            vectors = [[float(value) for value in item["embedding"]] for item in data]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The OpenAI embedding request failed.",
        ) from exc
    return _validate_vectors(vectors, len(texts))


async def _embed_gemini(texts: list[str], *, task: EmbeddingTask) -> list[list[float]]:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini embeddings are not configured.",
        )

    api_key = settings.gemini_api_key.get_secret_value()
    model = settings.gemini_embedding_model
    semaphore = asyncio.Semaphore(8)

    async def embed_one(client: httpx.AsyncClient, text: str) -> list[float]:
        async with semaphore:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                headers={"x-goog-api-key": api_key},
                json={
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task,
                    "outputDimensionality": EMBEDDING_DIMENSIONS,
                },
            )
            response.raise_for_status()
            payload = response.json()
            embedding = payload.get("embedding") if isinstance(payload, dict) else None
            if not isinstance(embedding, dict) or not isinstance(embedding.get("values"), list):
                raise ValueError("The embedding response is missing its values list.")
            vector = embedding["values"]
        return [float(value) for value in vector]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            vectors = await asyncio.gather(
                *(embed_one(client, text) for text in texts)
            )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The Gemini embedding request failed.",
        ) from exc
    return _validate_vectors(vectors, len(texts))
