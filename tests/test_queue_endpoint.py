import asyncio
import importlib
import sys
import types
from fastapi.testclient import TestClient

import ioc_checker.queue as queue


def test_queue_endpoint():
    importlib.reload(queue)

    magic = types.ModuleType("magic")
    def _from_file(path, mime=False):
        if not mime:
            raise NotImplementedError
        return "text/plain"
    def _from_buffer(buf, mime=False):
        if not mime:
            raise NotImplementedError
        return "text/plain"
    magic.from_file = _from_file
    magic.from_buffer = _from_buffer
    sys.modules["magic"] = magic

    import ioc_checker.main as main
    importlib.reload(main)
    client = TestClient(main.app)

    async def run():
        await queue.add_task("ioc1", token="A")
        await queue.add_task("ioc2", token="B")
    asyncio.run(run())

    resp_a = client.get("/queue", params={"token": "A"})
    resp_b = client.get("/queue", params={"token": "B"})
    assert resp_a.json()["queue"] == "1/2"
    assert resp_b.json()["queue"] == "1/2"
