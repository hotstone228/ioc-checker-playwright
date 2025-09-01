from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncIterator

from playwright.async_api import async_playwright, BrowserContext
from iocparser import IOCParser

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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()


async def fetch_ioc_info(ioc: str, context: BrowserContext) -> Dict[str, Any]:
    ioc_type = classify_ioc(ioc)
    gui_seg, api_seg = URL_MAP[ioc_type]
    gui_url = f"https://www.virustotal.com/gui/{gui_seg}/{ioc}"
    api_url = f"https://www.virustotal.com/ui/{api_seg}/{ioc}?relationships=*"

    page = await context.new_page()
    async with page.expect_response(lambda r: r.url.startswith(api_url)) as resp_info:
        await page.goto(gui_url, wait_until="networkidle")
    response = await resp_info.value
    data = (await response.json())["data"]["attributes"]
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
    return result
