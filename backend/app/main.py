"""Nova backend – FastAPI application.

Run (from the ``backend`` folder):  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_assistant, routes_data, routes_tasks
from app.core.config import APP_VERSION, get_settings
from app.core.container import build_container
from app.core.logging import get_logger, setup_logging
from app.database.session import create_tables, init_engine
from app.services.scheduler import run_scheduler

settings = get_settings()
setup_logging(settings.log_level)
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s backend v%s (%s)", settings.app_name, APP_VERSION, settings.environment)
    init_engine(settings.database_url)
    create_tables()
    app.state.container = build_container(settings)
    stop = asyncio.Event()
    task = asyncio.create_task(run_scheduler(settings.scheduler_interval_seconds, stop))
    log.info("Nova is ready on http://%s:%s (API docs at /docs)", settings.host, settings.port)
    try:
        yield
    finally:
        stop.set()
        await task
        log.info("Nova backend stopped")


app = FastAPI(
    title="Nova API",
    version=APP_VERSION,
    description="Backend for Nova, an ML-powered smart voice assistant.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path
    if not (request.method == "GET" and path in ("/api/notifications", "/api/timers", "/api/focus", "/api/health")):
        log.info("%s %s → %s (%.0f ms)", request.method, path, response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(routes_assistant.router)
app.include_router(routes_tasks.router)
app.include_router(routes_data.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": "Nova API", "version": APP_VERSION, "docs": "/docs"}
