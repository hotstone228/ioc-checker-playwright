from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncIterator
import logging

import httpx
from iocparser import IOCParser

from .config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://opentip.kaspersky.com/api/v1"


def classify_ioc(ioc: str) -> str:
    parsed = IOCParser(ioc).parse()
    if parsed:
        kind = parsed[0].kind.lower()
        if kind in {"ip", "ipv4", "ipv6"}:
            return "ip"
        if kind in {"md5", "sha1", "sha256", "sha512"}:
            return "hash"
        if kind == "url":
            return "url"
    return "domain"


@asynccontextmanager
async def get_context() -> AsyncIterator[httpx.AsyncClient]:
    headers = {}
    if settings.kaspersky_token:
        headers["x-api-key"] = settings.kaspersky_token
    async with httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=10) as client:
        yield client


async def lookup_hash(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/hash", params={"request": value})
    resp.raise_for_status()
    return resp.json()


async def lookup_ip(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/ip", params={"request": value})
    resp.raise_for_status()
    return resp.json()


async def lookup_domain(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/domain", params={"request": value})
    resp.raise_for_status()
    return resp.json()


async def lookup_url(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/url", params={"request": value})
    resp.raise_for_status()
    return resp.json()


async def submit_file(data: bytes, filename: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    files = {"file": (filename, data)}
    resp = await client.post("/scan/file", files=files)
    resp.raise_for_status()
    return resp.json()


async def get_file_report(task_id: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/getresult/file", params={"task_id": task_id})
    resp.raise_for_status()
    return resp.json()


async def fetch_ioc_info(ioc: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    ioc_type = classify_ioc(ioc)
    logger.info("Fetching %s from Kaspersky", ioc)
    if ioc_type == "hash":
        data = await lookup_hash(ioc, client)
    elif ioc_type == "ip":
        data = await lookup_ip(ioc, client)
    elif ioc_type == "url":
        data = await lookup_url(ioc, client)
    else:
        data = await lookup_domain(ioc, client)
    return {"ioc": ioc, "type": ioc_type, "data": data}
