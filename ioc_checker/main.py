from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging
import os
import tempfile

from fastapi import (
    FastAPI,
    Request,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from iocsearcher.searcher import Searcher
from iocsearcher.document import open_document

from .queue import add_task, get_task, get_queue_size
from .worker import start_workers
from .config import settings
from .database import init_db
from .providers import requires_token

logger = logging.getLogger(__name__)

# Normalize pattern names returned by iocsearcher so the API exposes
# consistent keys. Anything not listed here will use the original pattern
# name as-is so new IOC types automatically appear in responses.
NORMALIZE_KIND = {
    "ip4": "ipv4",
    "ip6": "ipv6",
    "url": "uri",
}


class ScanRequest(BaseModel):
    iocs: list[str]
    service: str = settings.providers[0]
    token: str | None = None


class ParseRequest(BaseModel):
    text: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    logger.info("Starting %s worker(s)", settings.worker_count)
    start_workers(settings.worker_count)
    yield
    logger.info("Application shutdown")


app = FastAPI(lifespan=lifespan)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html", {"request": request, "providers": settings.providers}
    )

@app.post("/parse")
async def parse_iocs(req: ParseRequest) -> dict[str, list[str]]:
    logger.info("Parsing IOC text of length %d", len(req.text))
    searcher = Searcher()
    parsed = searcher.search_data(req.text)
    logger.info("Found %d IOC(s)", len(parsed))
    result: dict[str, list[str]] = {}
    for item in parsed:
        key = NORMALIZE_KIND.get(item.name.lower(), item.name.lower())
        result.setdefault(key, []).append(item.value)
    return result


TEXT_FILE_TYPES = {".txt", ".log", ".csv", ".json"}
ALLOWED_FILE_TYPES = TEXT_FILE_TYPES | {".pdf", ".html", ".htm", ".docx"}


@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)) -> dict[str, list[str]]:
    logger.info("Parsing uploaded file %s", file.filename)
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await file.read()
    if ext in TEXT_FILE_TYPES:
        text = data.decode("utf-8", "ignore")
    else:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            doc = open_document(tmp_path)
            if doc is None:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            text, _ = doc.get_text(options={})
        finally:
            # Ensure any file handles opened by the document parser are
            # released before attempting to remove the temporary file.
            try:
                del doc  # triggers object destructor and closes handles
            except UnboundLocalError:
                pass
            os.unlink(tmp_path)
    searcher = Searcher()
    parsed = searcher.search_data(text)
    logger.info("Found %d IOC(s)", len(parsed))
    result: dict[str, list[str]] = {}
    for item in parsed:
        key = NORMALIZE_KIND.get(item.name.lower(), item.name.lower())
        result.setdefault(key, []).append(item.value)
    return result


@app.post("/scan")
async def scan(req: ScanRequest) -> dict:
    if requires_token(req.service) and not req.token:
        raise HTTPException(status_code=400, detail="API token required")
    logger.info("Queueing %d IOC(s) for service %s", len(req.iocs), req.service)
    task_ids = []
    for ioc in req.iocs:
        if not ioc:
            continue
        task_id = await add_task(ioc, req.service, req.token)
        task_ids.append({"id": task_id, "ioc": ioc, "service": req.service})
    queue_size = get_queue_size()
    return {"tasks": task_ids, "queue": queue_size}


@app.get("/queue")
async def queue_status() -> dict:
    """Return current global queue size."""
    return {"queue": get_queue_size()}

@app.get("/status/{task_id}")
async def status(task_id: str) -> dict:
    logger.debug("Status requested for task %s", task_id)
    task = get_task(task_id)
    if task is None:
        return {"error": "unknown task"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "ioc": task.ioc,
        "service": task.service,
    }
