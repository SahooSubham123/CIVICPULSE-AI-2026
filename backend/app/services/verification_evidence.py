import asyncio
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.core.config import settings
from app.core.errors import APIError

logger = logging.getLogger(__name__)
MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_TEXT = 16_000


class _PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._parts))[:MAX_SOURCE_TEXT]


@dataclass(frozen=True)
class FetchedSource:
    url: str
    publisher: str
    text: str


def _validate_source_url(url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise APIError(422, "invalid_source_url", "A supplied evidence URL is invalid.") from exc
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise APIError(
            422,
            "invalid_source_url",
            "Evidence URLs must use credential-free HTTPS on the default port without query strings or fragments.",
        )
    trusted_domains = settings.trusted_fact_source_domains
    if not any(hostname == domain or hostname.endswith(f".{domain}") for domain in trusted_domains):
        raise APIError(
            422,
            "untrusted_source",
            "This source domain is not in the administrator-configured trusted-source list.",
        )
    sanitized_url = urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))
    return sanitized_url, hostname


def validate_source_urls(urls: list[str]) -> list[tuple[str, str]]:
    return [_validate_source_url(url) for url in urls]


async def fetch_trusted_sources(urls: list[tuple[str, str]]) -> tuple[list[FetchedSource], list[str]]:
    sources: list[FetchedSource] = []
    limitations: list[str] = []
    timeout = httpx.Timeout(12.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for url, hostname in urls:
            try:
                async with asyncio.timeout(12):
                    async with client.stream(
                        "GET",
                        url,
                        headers={"Accept": "text/html,text/plain;q=0.9"},
                    ) as response:
                        if response.is_redirect:
                            limitations.append(f"{hostname}: redirects are not followed; verify the canonical URL.")
                            continue
                        if response.status_code != 200:
                            limitations.append(f"{hostname}: returned HTTP {response.status_code}.")
                            continue
                        media_type = response.headers.get("content-type", "").lower()
                        if "text/html" not in media_type and "text/plain" not in media_type:
                            limitations.append(f"{hostname}: unsupported evidence content type.")
                            continue
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_SOURCE_BYTES:
                                limitations.append(f"{hostname}: response exceeded the evidence size limit.")
                                body.clear()
                                break
                        if not body:
                            continue
                        decoded = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                        if "text/html" in media_type:
                            parser = _PageTextParser()
                            parser.feed(decoded)
                            text = parser.text()
                        else:
                            text = re.sub(r"\s+", " ", decoded).strip()[:MAX_SOURCE_TEXT]
                        if not text:
                            limitations.append(f"{hostname}: no readable text was found.")
                            continue
                        sources.append(FetchedSource(url=url, publisher=hostname, text=text))
            except TimeoutError:
                limitations.append(f"{hostname}: exceeded the source-fetch time limit.")
            except httpx.HTTPError as exc:
                logger.info("Trusted evidence fetch failed for %s (%s)", hostname, type(exc).__name__)
                limitations.append(f"{hostname}: could not be reached.")
    return sources, limitations


def select_evidence_excerpt(claim: str, source: FetchedSource) -> str:
    claim_terms = {
        term.lower()
        for term in re.findall(r"[A-Za-z0-9]{3,}", claim)
    }
    paragraphs = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source.text) if part.strip()]
    if not paragraphs:
        return source.text[:1_000]
    ranked = sorted(
        enumerate(paragraphs),
        key=lambda item: (
            len(claim_terms.intersection(set(re.findall(r"[A-Za-z0-9]{3,}", item[1].lower())))),
            -item[0],
        ),
        reverse=True,
    )
    excerpt = ranked[0][1]
    if len(excerpt) > 1_000:
        excerpt = excerpt[:997].rsplit(" ", 1)[0] + "..."
    return excerpt
