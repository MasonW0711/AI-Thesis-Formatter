from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import jobs_router, templates_router, ui_router
from app.core.config import ensure_directories, settings
from app.core.database import SessionLocal, init_db
from app.core.logging import configure_logging
from app.models.db_models import TemplateRecord
from app.services.template_service import TemplateService


logger = logging.getLogger(__name__)

# Rate limiter (in-memory, single-instance; use Redis for multi-instance)
from app.core.limiter import limiter

# API key auth (optional, enabled when API_AUTH_KEY is set in secrets)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def optional_api_key_auth(request: Request, key: str = Security(_api_key_header)) -> bool:
    """
    Authenticate requests to /api/* routes.
    Returns True if auth is disabled (no key configured) or key matches.
    Raises 401 if key is present but invalid.
    """
    auth_key = settings.api_auth_key
    if not auth_key:
        return True  # Auth disabled
    if not key:
        raise JSONResponse(status_code=401, content={"detail": "請提供 X-API-Key header。"})
    if key != auth_key:
        raise JSONResponse(status_code=403, content={"detail": "X-API-Key 無效。"})
    return True


def create_app() -> FastAPI:
    configure_logging(debug=settings.debug)

    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8501",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_upload_size_mb * 1024 * 1024 + 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "上傳內容過大，請縮小檔案後再試。"})
        return await call_next(request)

    @app.on_event("startup")
    async def startup() -> None:
        ensure_directories()
        init_db()

        with SessionLocal() as session:
            # Recover any jobs left in RUNNING state (process died mid-job)
            from app.services.job_service import JobService
            recovered = JobService().recover_stale_jobs(session)
            if recovered:
                logger.info("已恢復 %d 個停滯任務", recovered)

            has_default = session.query(TemplateRecord).filter(TemplateRecord.is_default.is_(True)).first()
            if not has_default:
                logger.info("找不到預設範本，系統將自動重建預設範本。")
                TemplateService().reset_default_template(session)

    app.mount(
        "/static",
        StaticFiles(directory=str(settings.base_dir / "app" / "ui" / "static")),
        name="static",
    )

    app.include_router(ui_router)
    app.include_router(templates_router)
    app.include_router(jobs_router)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "?")
        logger.exception("Unhandled exception [%s]: %s", request_id, exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "系統發生未預期錯誤，請稍後重試。",
                "request_id": request_id,
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "請求太頻繁，請稍後再試。"},
        )

    # Wire up rate limiter
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    return app


app = create_app()
