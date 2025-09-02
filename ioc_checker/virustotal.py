from contextlib import asynccontextmanager
from typing import Any, Dict
from collections.abc import AsyncIterator
import logging

from playwright.async_api import async_playwright, BrowserContext, Error
from iocparser import IOCParser

from .config import settings

logger = logging.getLogger(__name__)

URL_MAP = {
    "ip": ("ip-address", "ip_addresses"),
    "domain": ("domain", "domains"),
    "hash": ("file", "files"),
}


def classify_ioc(ioc: str) -> str:
    parsed = IOCParser(ioc).parse()
    if not parsed:
        return "domain"
    kind = parsed[0].kind.lower()
    if kind in {"ip", "ipv4", "ipv6"}:
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
    await page.goto(gui_url, wait_until=settings.wait_until)

    # detect "Item not found" or empty results pages
    not_found = await page.evaluate(
        """
        () => {
            const root = document.querySelector('#view-container');
            if (!root) return false;
            if (root.querySelector('custom-error-view')) return true;
            const limited = root.querySelector('limited-search-view');
            if (limited && limited.shadowRoot && limited.shadowRoot.querySelector('vt-ui-special-states')) {
                return true;
            }
            return false;
        }
        """
    )
    if not_found:
        await page.close()
        raise ValueError("IOC not found")

    try:
        response = await page.request.get(api_url)
    except Error as exc:
        await page.close()
        raise ValueError("Network error while fetching IOC") from exc
    if response.status == 404:
        await page.close()
        raise ValueError("IOC not found")

    json_data = await response.json()
    if "data" not in json_data:
        await page.close()
        raise ValueError("IOC not found")
    data = json_data["data"]["attributes"]
    await page.close()

    result: Dict[str, Any] = {
        "ioc": ioc,
        "type": ioc_type,
        "reputation": data.get("reputation"),
        "last_analysis_stats": data.get("last_analysis_stats", {}),
    }
    if ioc_type == "ip":
        result["country"] = data.get("country")
        result["as_owner"] = data.get("as_owner")
    logger.debug("Result for %s: %s", ioc, result)
    return result
