from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse, Response

from .config import settings
from .logging_setup import get_logger, setup_logging
from .models import AddTaskRequest, AgentResult, RunRequest, ShareCopy, SharePack, Task, UpdateTaskStatusRequest
from .service import OnePersonCompanyService

setup_logging()
logger = get_logger("onepersoncompany.api")

app = FastAPI(title=settings.project_name, version="0.1.0")
service: Optional[OnePersonCompanyService] = None
web_index = Path(__file__).resolve().parent / "web" / "index.html"
web_demo = Path(__file__).resolve().parent / "web" / "demo.html"


def get_service() -> OnePersonCompanyService:
    global service
    if service is None:
        try:
            service = OnePersonCompanyService()
            logger.info("Service initialized")
        except ValueError as exc:
            logger.exception("Service initialization failed: %s", exc)
            raise HTTPException(status_code=500, detail=f"LLM config error: {exc}")
    return service


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    start = perf_counter()
    try:
        response = await call_next(request)
        cost_ms = (perf_counter() - start) * 1000
        if request.url.path != "/favicon.ico":
            logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, cost_ms)
        return response
    except Exception:
        cost_ms = (perf_counter() - start) * 1000
        logger.exception("%s %s -> 500 (%.1f ms)", request.method, request.url.path, cost_ms)
        raise


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


@app.get("/")
def web_console() -> FileResponse:
    if not web_index.exists():
        raise HTTPException(status_code=404, detail="Web console not found")
    return FileResponse(web_index)


@app.get("/demo")
def public_demo_page() -> FileResponse:
    if not web_demo.exists():
        raise HTTPException(status_code=404, detail="Public demo page not found")
    return FileResponse(web_demo)


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/public/snapshot")
def public_snapshot() -> Dict[str, object]:
    svc = get_service()
    tasks = svc.list_tasks()
    artifacts = svc.storage.list_artifacts()
    latest_artifacts = sorted(artifacts, key=lambda item: item.created_at, reverse=True)[:3]

    def _preview(text: str, limit: int = 220) -> str:
        clean = text.replace("\n", " ").strip()
        return clean if len(clean) <= limit else clean[:limit] + "..."

    return {
        "service": settings.project_name,
        "task_count": len(tasks),
        "done_task_count": len([task for task in tasks if task.status.value == "done"]),
        "artifact_count": len(artifacts),
        "latest_artifacts": [
            {
                "id": item.id,
                "title": item.title,
                "artifact_type": item.artifact_type.value,
                "created_at": item.created_at.isoformat(),
                "preview": _preview(item.content),
            }
            for item in latest_artifacts
        ],
    }


@app.post("/init")
def init_workspace() -> Dict[str, int]:
    created = get_service().init_seed_tasks()
    return {"created_tasks": len(created)}


@app.post("/run/daily-brief", response_model=AgentResult)
def run_daily_brief(payload: RunRequest) -> AgentResult:
    try:
        return get_service().run_daily_brief(payload.updates, lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/run/launch-pack", response_model=AgentResult)
def run_launch_pack(payload: RunRequest) -> AgentResult:
    try:
        return get_service().run_launch_pack(payload.updates, lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/run/weekly-review", response_model=AgentResult)
def run_weekly_review(payload: RunRequest = Body(default_factory=RunRequest)) -> AgentResult:
    try:
        return get_service().run_weekly_review(lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/tasks", response_model=List[Task])
def list_tasks() -> List[Task]:
    return get_service().list_tasks()


@app.post("/tasks", response_model=Task)
def add_task(payload: AddTaskRequest) -> Task:
    return get_service().add_task(title=payload.title, priority=payload.priority, source=payload.source)


@app.post("/tasks/status", response_model=Task)
def update_task_status(payload: UpdateTaskStatusRequest) -> Task:
    try:
        return get_service().mark_task_status(task_id=payload.task_id, status=payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/share", response_model=ShareCopy)
def create_share_copy(payload: RunRequest = Body(default_factory=RunRequest)) -> ShareCopy:
    try:
        return get_service().generate_share_copy(lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/share/pack", response_model=SharePack)
def create_share_pack(payload: RunRequest = Body(default_factory=RunRequest)) -> SharePack:
    try:
        return get_service().generate_share_pack(lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/demo/day0")
def run_demo_day0(payload: RunRequest = Body(default_factory=RunRequest)) -> Dict[str, str]:
    try:
        return get_service().run_demo_day0(lang=payload.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/demo/instant")
def run_instant_demo(payload: RunRequest = Body(default_factory=RunRequest)) -> Dict[str, object]:
    return get_service().run_instant_demo(lang=payload.lang)
