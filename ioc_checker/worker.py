import asyncio
import logging
from typing import Dict, Any

from .queue import queue, get_task
from .config import settings
from .database import get_cached_result, cache_result
from .providers import init_contexts, fetch_ioc

logger = logging.getLogger(__name__)


async def worker() -> None:
    logger.info("Worker started")
    contexts, stack = await init_contexts(settings.providers)
    try:
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
                cached = await get_cached_result(task.ioc, task.service)
                if cached is not None:
                    task.result = cached
                    task.status = "done"
                    logger.info("Cache hit for task %s", task_id)
                else:
                    task.result = await fetch_ioc(
                        task.service, task.ioc, task.token, contexts
                    )
                    await cache_result(task.ioc, task.service, task.result)
                    task.status = "done"
                    logger.info("Task %s completed", task_id)
            except Exception as exc:  # noqa: BLE001
                task.status = "error"
                task.error = str(exc)
                logger.exception("Task %s failed: %s", task_id, exc)
            queue.task_done()
    finally:
        await stack.aclose()


def start_workers(count: int = 1) -> None:
    for _ in range(count):
        asyncio.create_task(worker())
