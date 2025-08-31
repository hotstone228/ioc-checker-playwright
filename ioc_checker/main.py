from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .queue import add_task, get_task
from .worker import start_workers

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.on_event("startup")
async def startup() -> None:
    start_workers(2)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/scan")
async def scan(iocs: list[str]) -> dict:
    task_ids = []
    for ioc in iocs:
        if not ioc:
            continue
        task_id = await add_task(ioc)
        task_ids.append({"id": task_id, "ioc": ioc})
    return {"tasks": task_ids}

@app.get("/status/{task_id}")
async def status(task_id: str) -> dict:
    task = get_task(task_id)
    if task is None:
        return {"error": "unknown task"}
    return {"status": task.status, "result": task.result, "error": task.error, "ioc": task.ioc}
