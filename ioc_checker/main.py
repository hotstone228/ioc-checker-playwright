from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator

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

from iocparser import IOCParser

from .queue import add_task, get_task
from .worker import start_workers


class ScanRequest(BaseModel):
    iocs: list[str]
    service: str = "virustotal"


class ParseRequest(BaseModel):
    text: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    start_workers(2)
    yield


app = FastAPI(lifespan=lifespan)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/parse")
async def parse_iocs(req: ParseRequest) -> dict[str, list[str]]:
    parser = IOCParser(req.text)
    parsed = parser.parse()
    result: dict[str, list[str]] = {}
    for item in parsed:
        key = item.kind.lower()
        result.setdefault(key, []).append(item.value)
    return result


ALLOWED_FILE_TYPES = {".txt", ".log", ".csv", ".json"}


@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)) -> dict[str, list[str]]:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    content = (await file.read()).decode("utf-8", "ignore")
    parser = IOCParser(content)
    parsed = parser.parse()
    result: dict[str, list[str]] = {}
    for item in parsed:
        key = item.kind.lower()
        result.setdefault(key, []).append(item.value)
    return result


@app.post("/scan")
async def scan(req: ScanRequest) -> dict:
    task_ids = []
    for ioc in req.iocs:
        if not ioc:
            continue
        task_id = await add_task(ioc, req.service)
        task_ids.append({"id": task_id, "ioc": ioc, "service": req.service})
    return {"tasks": task_ids}

@app.get("/status/{task_id}")
async def status(task_id: str) -> dict:
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
