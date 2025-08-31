import re
from contextlib import asynccontextmanager
from typing import Any, Dict
from playwright.async_api import async_playwright, BrowserContext

URL_MAP = {
    "ip": ("ip-address", "ip_addresses"),
    "domain": ("domain", "domains"),
    "hash": ("file", "files"),
}

IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
HASH_RE = re.compile(r"^[A-Fa-f0-9]{32,64}$")


def classify_ioc(ioc: str) -> str:
    if IP_RE.match(ioc):
        return "ip"
    if HASH_RE.match(ioc):
        return "hash"
    return "domain"


@asynccontextmanager
async def playwright_browser() -> BrowserContext:
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
