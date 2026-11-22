import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import APIError
from app.schemas.verification import AIAnalysis

logger = logging.getLogger(__name__)


def _configured_provider() -> tuple[str, str, str]:
    if settings.ai_provider == "openai" and settings.openai_api_key:
        return "openai", settings.openai_api_key.get_secret_value(), settings.openai_model
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return "gemini", settings.gemini_api_key.get_secret_value(), settings.gemini_model
    raise APIError(503, "ai_provider_unavailable", "The configured AI provider is not available. Configure its API key.")


async def generate_json(system_prompt: str, user_prompt: str) -> tuple[str, str]:
    provider, api_key, model = _configured_provider()
    timeout = httpx.Timeout(30.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "openai":
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            else:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "generationConfig": {"responseMimeType": "application/json"},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    },
                )
                response.raise_for_status()
                content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except httpx.HTTPStatusError as exc:
        logger.warning("Configured AI provider returned HTTP %s", exc.response.status_code)
        raise APIError(502, "ai_provider_error", "The AI provider could not complete the request.") from exc
    except httpx.RequestError as exc:
        logger.warning("Configured AI provider request failed: %s", type(exc).__name__)
        raise APIError(502, "ai_provider_error", "The AI provider could not be reached.") from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        logger.exception("Configured AI provider returned an unreadable JSON response")
        raise APIError(502, "ai_response_invalid", "The AI provider returned an invalid response.") from exc

    if not isinstance(content, str) or not content.strip():
        raise APIError(502, "ai_response_empty", "The AI provider returned an empty response.")
    return content.strip(), provider


async def generate_text(system_prompt: str, user_prompt: str) -> tuple[str, str]:
    provider, api_key, model = _configured_provider()
    timeout = httpx.Timeout(30.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "openai":
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            else:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    },
                )
                response.raise_for_status()
                content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except httpx.HTTPStatusError as exc:
        logger.warning("Configured AI provider returned HTTP %s", exc.response.status_code)
        raise APIError(502, "ai_provider_error", "The AI provider could not complete the request.") from exc
    except httpx.RequestError as exc:
        logger.warning("Configured AI provider request failed: %s", type(exc).__name__)
        raise APIError(502, "ai_provider_error", "The AI provider could not be reached.") from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        logger.exception("Configured AI provider returned an unreadable response")
        raise APIError(502, "ai_response_invalid", "The AI provider returned an invalid response.") from exc

    if not isinstance(content, str) or not content.strip():
        raise APIError(502, "ai_response_empty", "The AI provider returned an empty response.")
    return content.strip(), provider


async def analyze_claim(system_prompt: str, user_prompt: str) -> tuple[AIAnalysis, str]:
    raw, provider = await generate_text(
        f"{system_prompt}\nReturn only a JSON object with assessment, confidence, analysis, and sources.",
        user_prompt,
    )
    try:
        payload: Any = json.loads(raw)
        analysis = AIAnalysis.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("AI fact analysis did not match the expected schema")
        raise APIError(502, "ai_response_invalid", "The AI provider returned an invalid analysis.") from exc
    return analysis, provider
