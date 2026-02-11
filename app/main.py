from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import jobs_router, templates_router, ui_router
from app.core.config import ensure_directories, settings
from app.core.database import SessionLocal, init_db
from app.core.logging import configure_logging
from app.models.db_models import TemplateRecord
from app.services.template_service import TemplateService


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging(debug=settings.debug)

    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "系統發生未預期錯誤，請稍後重試。"})

    return app


app = create_app()
