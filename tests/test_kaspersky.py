import httpx

from ioc_checker import kaspersky


def test_parse_hash_only_first_seen():
    data = {
        "Zone": "Red",
        "FileStatus": "Malware",
        "Sha1": "a" * 40,
        "Md5": "b" * 32,
        "Sha256": "c" * 64,
        "FirstSeen": "2024-01-01T00:00:00Z",
        "LastSeen": "2024-01-02T00:00:00Z",
        "Signer": "ACME",
        "FileGeneralInfo": {},
    }
    parsed = kaspersky._parse_hash(data)
    assert parsed["first_seen"] == "2024-01-01T00:00:00Z"
    assert "last_seen" not in parsed


def test_lookup_ip_uses_ip_param():
    called = {}

    async def handler(request: httpx.Request) -> httpx.Response:  # noqa: D401
        called["url"] = str(request.url)
        return httpx.Response(200, json={})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
            await kaspersky.lookup_ip("1.2.3.4", client)

    import asyncio

    asyncio.run(run())

    assert "ip=1.2.3.4" in called["url"]

