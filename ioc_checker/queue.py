import asyncio
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import logging

from .config import settings

@dataclass
class Task:
    id: str
    ioc: str
    service: str = settings.providers[0]
    status: str = "queued"  # queued, processing, done, error
    result: Optional[dict] = None
    error: Optional[str] = None
    token: Optional[str] = None

# In-memory storage
_tasks: Dict[str, Task] = {}
queue: asyncio.Queue[str] = asyncio.Queue()

logger = logging.getLogger(__name__)


async def add_task(ioc: str, service: str = settings.providers[0], token: Optional[str] = None) -> str:
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, ioc=ioc, service=service, token=token)
    _tasks[task_id] = task
    await queue.put(task_id)
    mine, total = get_queue_counts(token)
    logger.info("Queued task %s for %s (%d/%d)", task_id, service, mine, total)
    return task_id

def get_task(task_id: str) -> Optional[Task]:
    return _tasks.get(task_id)


def get_queue_counts(token: Optional[str] = None) -> Tuple[int, int]:
    """Return outstanding task counts for a token and globally."""
    total = 0
    mine = 0
    for task in _tasks.values():
        if task.status not in {"done", "error"}:
            total += 1
            if task.token == token:
                mine += 1
    return mine, total


def get_queue_size(token: Optional[str] = None) -> str:
    """Return a formatted string of queued tasks for token/total."""
    mine, total = get_queue_counts(token)
    return f"{mine}/{total}"
