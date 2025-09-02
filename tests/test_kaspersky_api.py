import asyncio
import json
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
import httpx
from ioc_checker import kaspersky


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_lookup_hash_parsing():
    sample = {
        "Zone": "Green",
        "FileStatus": "Clean",
        "Sha1": "abc",
        "Md5": "def",
        "Sha256": "ghi",
    }

    async def handler(request):
        assert request.url.path == "/api/v1/search/hash"
        return httpx.Response(200, json=sample)

    transport = httpx.MockTransport(handler)

    async def main():
        async with httpx.AsyncClient(transport=transport, base_url=kaspersky.API_BASE) as client:
            return await kaspersky.lookup_hash("abc", client)

    res = run(main())
    assert res["status_code"] == 200
    assert res["data"]["zone"] == "Green"
    assert res["data"]["sha256"] == "ghi"


def test_lookup_url_error():
    async def handler(request):
        return httpx.Response(414, json={"message": "too long"})

    transport = httpx.MockTransport(handler)

    async def main():
        async with httpx.AsyncClient(transport=transport, base_url=kaspersky.API_BASE) as client:
            return await kaspersky.lookup_url("x" * 2001, client)

    res = run(main())
    assert res["status_code"] == 414
    assert res["error"] == kaspersky.ERROR_MAP[414]


def test_submit_file_parsing():
    sample = {
        "Zone": "Yellow",
        "FileStatus": "Adware and other",
        "Sha1": "aaa",
        "Md5": "bbb",
        "Sha256": "ccc",
        "Size": 100,
        "Type": "exe",
    }

    async def handler(request):
        assert request.url.path == "/api/v1/scan/file"
        return httpx.Response(200, json=sample)

    transport = httpx.MockTransport(handler)

    async def main():
        async with httpx.AsyncClient(transport=transport, base_url=kaspersky.API_BASE) as client:
            return await kaspersky.submit_file(b"data", "file.bin", client)

    res = run(main())
    assert res["status_code"] == 200
    assert res["data"]["status"] == "Adware and other"
    assert res["data"]["size"] == 100


def test_lookup_ip_with_text_body():
    sample = {
        "Zone": "Green",
        "Status": "Clean",
        "Ip": "1.2.3.4",
    }

    async def handler(request):
        return httpx.Response(
            200,
            text=json.dumps(sample),
            headers={"content-type": "text/plain"},
        )

    transport = httpx.MockTransport(handler)

    async def main():
        async with httpx.AsyncClient(transport=transport, base_url=kaspersky.API_BASE) as client:
            return await kaspersky.lookup_ip("1.2.3.4", client)

    res = run(main())
    assert res["status_code"] == 200
    assert res["data"]["ip"] == "1.2.3.4"
