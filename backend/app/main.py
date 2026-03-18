from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    attendance,
    calendar,
    cohorts,
    courses,
    dashboard,
    exams,
    grades,
    intake,
    planner,
    profile,
    transcripts,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.albert.client import AlbertClient
from app.services.google.calendar_service import GoogleCalendarService
from app.utils.errors import AppError, UpstreamServiceError


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.albert_client = AlbertClient(settings)
    app.state.calendar_service = GoogleCalendarService(settings)
    yield
    await app.state.albert_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    payload = {"detail": exc.detail}
    if isinstance(exc, UpstreamServiceError):
        payload["service"] = exc.service
        payload["path"] = exc.path
        payload["upstream_status_code"] = exc.upstream_status_code
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


for router in (
    profile.router,
    cohorts.router,
    intake.router,
    courses.router,
    exams.router,
    attendance.router,
    transcripts.router,
    grades.router,
    calendar.router,
    dashboard.router,
    planner.router,
):
    app.include_router(router, prefix=settings.api_prefix)
