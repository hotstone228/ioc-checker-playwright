import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Task:
    id: str
    ioc: str
    status: str = "queued"  # queued, processing, done, error
    result: Optional[dict] = None
    error: Optional[str] = None

# In-memory storage
_tasks: Dict[str, Task] = {}
queue: asyncio.Queue[str] = asyncio.Queue()

async def add_task(ioc: str) -> str:
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, ioc=ioc)
    _tasks[task_id] = task
    await queue.put(task_id)
    return task_id

def get_task(task_id: str) -> Optional[Task]:
    return _tasks.get(task_id)
