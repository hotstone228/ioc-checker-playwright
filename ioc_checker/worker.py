import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Dict, Any

from .queue import queue, get_task
from .config import settings
from . import virustotal, kaspersky
from .database import get_cached_result, cache_result

logger = logging.getLogger(__name__)


SERVICE_MAP: Dict[str, Any] = {
    "virustotal": virustotal,
    "kaspersky": kaspersky,
}


async def worker() -> None:
    logger.info("Worker started")
    stack = AsyncExitStack()
    contexts: Dict[str, Any] = {}
    for name in settings.providers:
        module = SERVICE_MAP.get(name)
        if not module:
            logger.warning("Unknown provider %s configured", name)
            continue
        ctx = await stack.enter_async_context(module.get_context())
        contexts[name] = ctx
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
                    module = SERVICE_MAP.get(task.service)
                    context = contexts.get(task.service)
                    if module and context is not None:
                        task.result = await module.fetch_ioc_info(task.ioc, context)
                        await cache_result(task.ioc, task.service, task.result)
                        task.status = "done"
                        logger.info("Task %s completed", task_id)
                    else:
                        raise ValueError(f"unsupported service {task.service}")
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
