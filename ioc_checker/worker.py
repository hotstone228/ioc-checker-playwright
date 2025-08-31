import asyncio
from .queue import queue, get_task
from . import virustotal

async def worker() -> None:
    async with virustotal.playwright_browser() as browser_context:
        while True:
            task_id = await queue.get()
            task = get_task(task_id)
            if task is None:
                queue.task_done()
                continue
            task.status = "processing"
            try:
                task.result = await virustotal.fetch_ioc_info(task.ioc, browser_context)
                task.status = "done"
            except Exception as exc:  # noqa: BLE001
                task.status = "error"
                task.error = str(exc)
            queue.task_done()


def start_workers(count: int = 1) -> None:
    for _ in range(count):
        asyncio.create_task(worker())
