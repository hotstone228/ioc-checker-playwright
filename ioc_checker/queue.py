import asyncio
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
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
    logger.info("Queued task %s for %s", task_id, service)
    return task_id

def get_task(task_id: str) -> Optional[Task]:
    return _tasks.get(task_id)
