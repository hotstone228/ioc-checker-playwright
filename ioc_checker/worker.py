import asyncio
import logging
from .queue import queue, get_task
from . import virustotal

logger = logging.getLogger(__name__)

async def worker() -> None:
    logger.info("Worker started")
    async with virustotal.playwright_browser() as browser_context:
        while True:
            task_id = await queue.get()
            logger.info("Processing task %s", task_id)
            task = get_task(task_id)
            if task is None:
                logger.warning("Task %s not found", task_id)
                queue.task_done()
                continue
            task.status = "processing"
            try:
                if task.service == "virustotal":
                    task.result = await virustotal.fetch_ioc_info(task.ioc, browser_context)
                    task.status = "done"
                    logger.info("Task %s completed", task_id)
                else:
                    raise ValueError(f"unsupported service {task.service}")
            except Exception as exc:  # noqa: BLE001
                task.status = "error"
                task.error = str(exc)
                logger.exception("Task %s failed: %s", task_id, exc)
            queue.task_done()


def start_workers(count: int = 1) -> None:
    for _ in range(count):
        asyncio.create_task(worker())
