from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db_session
from app.models.db_models import TemplateRecord


templates = Jinja2Templates(directory=str(settings.base_dir / "app" / "ui" / "templates"))
ui_router = APIRouter()


@ui_router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db_session)) -> HTMLResponse:
    template_records = (
        db.query(TemplateRecord)
        .order_by(TemplateRecord.is_default.desc(), TemplateRecord.created_at.desc())
        .all()
    )
    payload = [
        {
            "id": item.id,
            "name": item.name,
            "source_filename": item.source_filename,
            "is_default": item.is_default,
            "created_at": item.created_at.isoformat(),
        }
        for item in template_records
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "templates": payload,
        },
    )


@ui_router.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "app": settings.app_name, "version": settings.app_version})
