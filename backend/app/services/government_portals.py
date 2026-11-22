import logging
from typing import Literal
from urllib.parse import urljoin, urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Route
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.config import settings
from app.core.errors import APIError
from app.schemas.services import PortalInspectionResponse, SupportedPortal

logger = logging.getLogger(__name__)
CHALLENGE_MARKERS = ("captcha", "robot check", "verify you are human", "access denied")
ERROR_MARKERS = (
    "page not found",
    "service unavailable",
    "internal server error",
    "something went wrong",
    "temporarily unavailable",
)
MAX_EXCERPT_LENGTH = 12_000


def _origin(url: str) -> tuple[str, str, int]:
    try:
        parsed = urlsplit(url)
        port = parsed.port or 443
    except ValueError as exc:
        raise APIError(422, "invalid_portal_url", "The configured portal URL is invalid.") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port != 443
    ):
        raise APIError(422, "invalid_portal_url", "Only credential-free HTTPS government portals are supported.")
    return parsed.scheme, parsed.hostname.lower(), port


def _configured_portal(portal_id: str) -> str:
    portal_url = settings.government_service_portals.get(portal_id)
    if portal_url is None:
        raise APIError(404, "portal_not_supported", "This government portal is not configured as supported.")
    _origin(portal_url)
    return portal_url


def list_supported_portals() -> list[SupportedPortal]:
    return [
        SupportedPortal(portal_id=portal_id, url=portal_url)
        for portal_id, portal_url in sorted(settings.government_service_portals.items())
    ]


def resolve_portal_url(portal_id: str, path: str) -> tuple[str, tuple[str, str, int]]:
    portal_url = _configured_portal(portal_id)
    base_origin = _origin(portal_url)
    if path and (path.startswith("//") or urlsplit(path).scheme or urlsplit(path).netloc):
        raise APIError(422, "invalid_portal_path", "Provide a path within the configured portal, not another URL.")
    parsed_path = urlsplit(path)
    if parsed_path.query or parsed_path.fragment:
        raise APIError(422, "invalid_portal_path", "Portal inspection paths cannot include a query or fragment.")
    target_url = urljoin(portal_url.rstrip("/") + "/", path.lstrip("/"))
    if _origin(target_url) != base_origin:
        raise APIError(422, "invalid_portal_path", "The requested page is outside the configured portal.")
    return target_url, base_origin


async def inspect_portal(portal_id: str, path: str = "") -> PortalInspectionResponse:
    requested_url, allowed_origin = resolve_portal_url(portal_id, path)
    warnings: list[str] = []
    http_status: int | None = None
    title = ""
    excerpt = ""
    navigation_status: Literal["ok", "http_error", "page_error", "challenge"] = "ok"

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except PlaywrightError as exc:
            logger.warning("Government portal browser could not start (%s)", type(exc).__name__)
            raise APIError(
                503,
                "browser_unavailable",
                "Portal inspection is unavailable. Install the Playwright Chromium browser runtime.",
            ) from exc
        try:
            context = await browser.new_context(
                accept_downloads=False,
                java_script_enabled=False,
                service_workers="block",
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(15_000)
            page.set_default_timeout(5_000)

            async def restrict_requests(route: Route) -> None:
                request_url = route.request.url
                if request_url.startswith(("data:", "blob:", "about:")):
                    await route.continue_()
                    return
                try:
                    request_origin = _origin(request_url)
                except APIError:
                    await route.abort()
                    return
                if (
                    request_origin != allowed_origin
                    or route.request.method != "GET"
                    or route.request.resource_type not in {"document", "stylesheet", "image", "font"}
                ):
                    await route.abort()
                    return
                await route.continue_()

            await page.route("**/*", restrict_requests)
            try:
                response = await page.goto(requested_url, wait_until="domcontentloaded")
                if response is not None:
                    http_status = response.status
                    if response.status >= 400:
                        navigation_status = "http_error"
                        warnings.append(f"The portal returned HTTP {response.status}.")
            except PlaywrightTimeoutError:
                navigation_status = "page_error"
                warnings.append("The portal page did not finish loading before the timeout.")
            except PlaywrightError as exc:
                navigation_status = "page_error"
                warnings.append("The portal could not be reached or completed navigation.")
                logger.info("Government portal navigation failed (%s)", type(exc).__name__)

            final_url = page.url
            try:
                if _origin(final_url) != allowed_origin:
                    final_url = requested_url
                    navigation_status = "page_error"
                    warnings.append("A redirect outside the configured portal was blocked.")
            except APIError:
                final_url = requested_url
                navigation_status = "page_error"
            try:
                title = (await page.title())[:300]
                excerpt = (await page.locator("body").inner_text())[:MAX_EXCERPT_LENGTH]
            except PlaywrightError as exc:
                if navigation_status == "ok":
                    navigation_status = "page_error"
                warnings.append("Portal page content could not be read.")
                logger.info("Government portal content extraction failed (%s)", type(exc).__name__)

            lower_content = f"{title}\n{excerpt}".lower()
            if any(marker in lower_content for marker in CHALLENGE_MARKERS):
                navigation_status = "challenge"
                warnings.append("The portal requires an interactive check; complete it yourself in your browser.")
            elif any(marker in lower_content for marker in ERROR_MARKERS) and navigation_status == "ok":
                navigation_status = "page_error"
                warnings.append("The portal page reports that it could not complete the request.")
        except PlaywrightError as exc:
            logger.warning("Government portal inspection failed (%s)", type(exc).__name__)
            raise APIError(
                503,
                "portal_inspection_unavailable",
                "The supported portal could not be inspected. Try again or open the portal directly.",
            ) from exc
        finally:
            await browser.close()

    return PortalInspectionResponse(
        portal_id=portal_id,
        requested_url=requested_url,
        final_url=final_url,
        title=title,
        excerpt=excerpt,
        navigation_status=navigation_status,
        http_status=http_status,
        warnings=warnings,
    )
