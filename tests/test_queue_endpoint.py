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
        await queue.add_task("ioc1", tab_id="A")
        await queue.add_task("ioc2", tab_id="B")
    asyncio.run(run())

    resp_a = client.get("/queue", params={"tab_id": "A"})
    resp_b = client.get("/queue", params={"tab_id": "B"})
    assert resp_a.json()["queue"] == "1/2"
    assert resp_b.json()["queue"] == "1/2"

    # Mark one task as processing; counts should remain until done
    task_id = asyncio.run(queue.queue.get())
    task = queue.get_task(task_id)
    task.status = "processing"
    queue.queue.task_done()
    resp_a = client.get("/queue", params={"tab_id": task.tab_id})
    resp_b = client.get("/queue", params={"tab_id": "B" if task.tab_id != "B" else "A"})
    assert resp_a.json()["queue"] == "1/2"
    assert resp_b.json()["queue"] == "1/2"

    # Complete the task and ensure counts decrease
    task.status = "done"
    resp_a = client.get("/queue", params={"tab_id": "A"})
    resp_b = client.get("/queue", params={"tab_id": "B"})
    assert resp_a.json()["queue"] == ("0/1" if task.tab_id == "A" else "1/1")
    assert resp_b.json()["queue"] == ("0/1" if task.tab_id == "B" else "1/1")
