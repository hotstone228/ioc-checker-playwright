import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
import asyncio
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
import pytest

from ioc_checker import main, worker
from ioc_checker.queue import queue

IOC_LIST = [
    "1.1.1.1",
    "8.8.8.8",
    "9.9.9.9",
    "7.7.7.7",
    "example.com",
    "test.org",
    "malware.net",
    "44d88612fea8a8f36de82e1278abb02f",
    "d41d8cd98f00b204e9800998ecf8427e",
    "e242ed3bffccdf271b7fbaf34ed72d089537b42f",
]


def test_parse_iocs(monkeypatch):
    monkeypatch.setattr(main, "start_workers", lambda count: None)
    text = "\n".join(IOC_LIST)
    with TestClient(main.app) as client:
        resp = client.post("/parse", json={"text": text})
        assert resp.status_code == 200
        data = resp.json()
    assert sum(len(v) for v in data.values()) == len(IOC_LIST)
    assert "1.1.1.1" in data["ipv4"]
    assert "example.com" in data["fqdn"]
    assert "44d88612fea8a8f36de82e1278abb02f" in data["md5"]
    assert "e242ed3bffccdf271b7fbaf34ed72d089537b42f" in data["sha1"]


def test_scan_iocs(monkeypatch):
    class DummyPage:
        async def goto(self, url: str, wait_until=None) -> None:
            return None

        async def close(self) -> None:
            return None

    class DummyContext:
        async def new_page(self) -> DummyPage:
            return DummyPage()

    @asynccontextmanager
    async def dummy_browser():
        yield DummyContext()

    async def dummy_fetch_ioc_info(ioc: str, context: DummyContext):
        return {"ioc": ioc, "fetched": True}

    monkeypatch.setattr(worker.virustotal, "playwright_browser", dummy_browser)
    monkeypatch.setattr(worker.virustotal, "fetch_ioc_info", dummy_fetch_ioc_info)

    with TestClient(main.app) as client:
        resp = client.post("/scan", json={"iocs": IOC_LIST, "service": "virustotal"})
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert len(tasks) == len(IOC_LIST)
        asyncio.get_event_loop().run_until_complete(queue.join())
        for task, ioc in zip(tasks, IOC_LIST):
            status_resp = client.get(f"/status/{task['id']}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["status"] == "done"
            assert status_data["result"]["ioc"] == ioc
