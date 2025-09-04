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
        await queue.add_task("ioc1")
        await queue.add_task("ioc2")
    asyncio.run(run())

    resp = client.get("/queue")
    assert resp.json()["queue"] == 2

    # Mark one task as processing; count should remain until done
    task_id = asyncio.run(queue.queue.get())
    task = queue.get_task(task_id)
    task.status = "processing"
    queue.queue.task_done()
    resp = client.get("/queue")
    assert resp.json()["queue"] == 2

    # Complete the task and ensure counts decrease
    task.status = "done"
    resp = client.get("/queue")
    assert resp.json()["queue"] == 1
