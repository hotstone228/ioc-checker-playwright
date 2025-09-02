from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncIterator, Optional
import logging

import httpx
from iocparser import IOCParser

from .config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://opentip.kaspersky.com/api/v1"

ERROR_MAP = {
    400: "incorrect query",
    401: "user authentication failed",
    403: "quota or request limit exceeded",
    404: "lookup results not found",
    413: "file size exceeds limit",
    414: "web address length exceeds limit",
    429: "too many requests",
}


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

def _parse_body(resp: httpx.Response) -> Optional[Any]:
    """Attempt to decode the response body as JSON and fallback to plain text."""
    try:
        return resp.json()
    except Exception:  # pragma: no cover - defensive
        text = resp.text.strip()
        return text or None


def _handle_response(resp: httpx.Response) -> Dict[str, Any]:
    body = _parse_body(resp)
    if resp.status_code == 200:
        return {"status_code": 200, "data": body}
    if resp.status_code == 204:
        return {"status_code": 204, "data": None}
    message = ERROR_MAP.get(resp.status_code, resp.reason_phrase)
    return {"status_code": resp.status_code, "error": message, "details": body}


def _parse_hash(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "zone": data.get("Zone"),
        "status": data.get("FileStatus"),
        "sha1": data.get("Sha1"),
        "md5": data.get("Md5"),
        "sha256": data.get("Sha256"),
        "first_seen": data.get("FirstSeen"),
        "last_seen": data.get("LastSeen"),
        "signer": data.get("Signer"),
        "general_info": data.get("FileGeneralInfo"),
    }


def _parse_ip(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "zone": data.get("Zone"),
        "status": data.get("Status"),
        "ip": data.get("Ip"),
        "country_code": data.get("CountryCode"),
        "first_seen": data.get("FirstSeen"),
        "hits_count": data.get("HitsCount"),
        "categories": data.get("Categories"),
        "general_info": data.get("IpGeneralInfo"),
    }


def _parse_domain(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "zone": data.get("Zone"),
        "domain": data.get("Domain"),
        "files_count": data.get("FilesCount"),
        "urls_count": data.get("UrlsCount"),
        "hits_count": data.get("HitsCount"),
        "ipv4_count": data.get("Ipv4Count"),
        "categories": data.get("Categories"),
        "general_info": data.get("DomainGeneralInfo"),
    }


def _parse_url(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "zone": data.get("Zone"),
        "url": data.get("Url"),
        "host": data.get("Host"),
        "ipv4_count": data.get("Ipv4Count"),
        "files_count": data.get("FilesCount"),
        "categories": data.get("Categories"),
        "general_info": data.get("UrlGeneralInfo"),
    }


def _parse_file(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "zone": data.get("Zone"),
        "status": data.get("FileStatus"),
        "sha1": data.get("Sha1"),
        "md5": data.get("Md5"),
        "sha256": data.get("Sha256"),
        "first_seen": data.get("FirstSeen"),
        "last_seen": data.get("LastSeen"),
        "signer": data.get("Signer"),
        "packer": data.get("Packer"),
        "size": data.get("Size"),
        "type": data.get("Type"),
        "hits_count": data.get("HitsCount"),
        "general_info": data.get("FileGeneralInfo"),
    }


async def lookup_hash(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/hash", params={"request": value})
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_hash(result["data"])
    return result


async def lookup_ip(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/ip", params={"request": value})
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_ip(result["data"])
    return result


async def lookup_domain(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/domain", params={"request": value})
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_domain(result["data"])
    return result


async def lookup_url(value: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/search/url", params={"request": value})
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_url(result["data"])
    return result


async def submit_file(data: bytes, filename: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    files = {"file": (filename, data)}
    resp = await client.post("/scan/file", files=files)
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_file(result["data"])
    return result


async def get_file_report(task_id: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get("/getresult/file", params={"task_id": task_id})
    result = _handle_response(resp)
    if isinstance(result.get("data"), dict):
        result["data"] = _parse_file(result["data"])
    return result


async def fetch_ioc_info(ioc: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    ioc_type = classify_ioc(ioc)
    logger.info("Fetching %s from Kaspersky", ioc)
    if ioc_type == "hash":
        result = await lookup_hash(ioc, client)
    elif ioc_type == "ip":
        result = await lookup_ip(ioc, client)
    elif ioc_type == "url":
        result = await lookup_url(ioc, client)
    else:
        result = await lookup_domain(ioc, client)
    result.update({"ioc": ioc, "type": ioc_type})
    return result
