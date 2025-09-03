from contextlib import asynccontextmanager
from typing import Any, Dict
from collections.abc import AsyncIterator
import logging

from playwright.async_api import async_playwright, BrowserContext
from iocsearcher.searcher import Searcher

from .config import settings

logger = logging.getLogger(__name__)

URL_MAP = {
    "ip": ("ip-address", "ip_addresses"),
    "domain": ("domain", "domains"),
    "hash": ("file", "files"),
}

TAG_PATHS = {
    "ip": ("ip-address-view", "vt-ui-ip-card"),
    "domain": ("domain-view", "vt-ui-domain-card"),
    "hash": ("file-view", "vt-ui-file-card"),
}


searcher = Searcher()


def classify_ioc(ioc: str) -> str:
    parsed = searcher.search_data(ioc)
    for item in parsed:
        kind = item.name.lower()
        if kind in {"ip4", "ip6"}:
            return "ip"
        if kind in {"md5", "sha1", "sha256", "sha512"}:
            return "hash"
    return "domain"


@asynccontextmanager
async def playwright_browser() -> AsyncIterator[BrowserContext]:
    logger.info("Launching browser (headless=%s)", settings.headless)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.headless)
        context = await browser.new_context(ignore_https_errors=True)
        try:
            logger.info("Browser context ready")
            yield context
        finally:
            logger.info("Closing browser")
            await context.close()
            await browser.close()


async def fetch_ioc_info(ioc: str, context: BrowserContext) -> Dict[str, Any]:
    logger.info("Fetching %s from VirusTotal", ioc)
    ioc_type = classify_ioc(ioc)
    gui_seg, api_seg = URL_MAP[ioc_type]
    gui_url = f"https://www.virustotal.com/gui/{gui_seg}/{ioc}"
    api_url = f"https://www.virustotal.com/ui/{api_seg}/{ioc}?relationships=*"

    page = await context.new_page()
    page.set_default_navigation_timeout(10_000)
    page.set_default_timeout(10_000)
    async with page.expect_response(lambda r: r.url.startswith(api_url)) as resp_info:
        await page.goto(gui_url, wait_until=settings.wait_until)
    response = await resp_info.value
    data = (await response.json())["data"]["attributes"]

    tags: list[str] = []
    view_tag, card_tag = TAG_PATHS.get(ioc_type, (None, None))
    if view_tag and card_tag:
        js = f"""
        () => {{
            const view = document.querySelector('#view-container > {view_tag}');
            if (!view) return [];
            const card = view.shadowRoot.querySelector('div > div > div.col-12.col-md > {card_tag}');
            if (!card) return [];
            return Array.from(card.shadowRoot.querySelectorAll('div > div.card-body.d-flex > div > div.hstack.gap-2 > a')).map(e => e.textContent.trim());
        }}
        """
        try:
            tags = await page.evaluate(js)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Tag extraction failed for %s: %s", ioc, exc)
    await page.close()

    result: Dict[str, Any] = {
        "ioc": ioc,
        "type": ioc_type,
        "reputation": data.get("reputation"),
        "last_analysis_stats": data.get("last_analysis_stats", {}),
        "tags": tags,
    }
    if ioc_type == "ip":
        result["country"] = data.get("country")
        result["as_owner"] = data.get("as_owner")
    logger.debug("Result for %s: %s", ioc, result)
    return result
