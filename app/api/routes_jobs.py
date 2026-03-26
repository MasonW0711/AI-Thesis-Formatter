from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.csrf import CSRFDependency
from app.core.database import get_db_session
from app.models.db_models import JobStatus
from app.models.schemas import JobCreateResponse, JobStatusResponse, RuleSet
from app.services.job_service import JobService
from app.services.template_service import TemplateService


jobs_router = APIRouter(prefix="/api/jobs", tags=["jobs"])
job_service = JobService()
template_service = TemplateService()


@jobs_router.get("/csrf-token", response_model=dict)
def get_csrf_token(request: Request) -> dict:
    """取得 CSRF token。所有 POST/PUT/DELETE 請求都必須在 Header 包含 X-CSRF-Token。"""
    client_ip = request.client.host if request.client else "unknown"
    from app.core.csrf import generate_csrf_token
    token = generate_csrf_token(client_ip)
    return {"csrf_token": token}


def _upload_size(upload: UploadFile, limit_bytes: int) -> int:
    """Stream-read file in chunks, check size limit without buffering entire file in RAM."""
    size = 0
    upload.file.seek(0)
    while True:
        chunk = upload.file.read(1024 * 1024)  # 1 MB at a time
        if not chunk:
            break
        size += len(chunk)
        if size > limit_bytes:
            upload.file.seek(0)
            raise HTTPException(
                status_code=413,
                detail=f"檔案大小超過 {settings.max_upload_size_mb} MB 上限。",
            )
    upload.file.seek(0)
    return size


@jobs_router.post("", response_model=JobCreateResponse)
@CSRFDependency(methods=["POST"])
def create_job(
    background_tasks: BackgroundTasks,
    template_id: str = Form(...),
    target_file: UploadFile = File(...),
    rules_override: str | None = Form(default=None),
    ai_provider: str | None = Form(default=None),
    openai_api_key: str | None = Form(default=None),
    openai_model: str | None = Form(default=None),
    gemini_api_key: str | None = Form(default=None),
    gemini_model: str | None = Form(default=None),
    db: Session = Depends(get_db_session),
) -> JobCreateResponse:
    size_bytes = _upload_size(target_file, settings.max_upload_size_mb * 1024 * 1024)

    template = template_service.get_template(db, template_id)

    parsed_override: RuleSet | None = None
    if rules_override:
        try:
            payload = json.loads(rules_override)
            parsed_override = RuleSet.model_validate(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"規則資料格式錯誤：{exc}") from exc

    ai_options = {
        "provider": (ai_provider or "").strip().lower() or None,
        "openai_api_key": (openai_api_key or "").strip() or None,
        "openai_model": (openai_model or "").strip() or None,
        "gemini_api_key": (gemini_api_key or "").strip() or None,
        "gemini_model": (gemini_model or "").strip() or None,
    }
    ai_options = {key: value for key, value in ai_options.items() if value is not None}

    job = job_service.create_job(db, template=template, file=target_file, rules_override=parsed_override)
    background_tasks.add_task(job_service.process_job, job.id, ai_options if ai_options else None)

    return JobCreateResponse(job_id=job.id, status=job.status, progress=job.progress)


@jobs_router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db_session)) -> JobStatusResponse:
    job = job_service.get_job(db, job_id)

    download_url = None
    if job.status == JobStatus.SUCCESS.value and job.output_docx_path:
        download_url = f"/api/jobs/{job.id}/download"

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        template_id=job.template_id,
        target_filename=job.target_filename,
        warning_message=job.warning_message,
        error_message=job.error_message,
        conversion_confidence=job.conversion_confidence,
        download_url=download_url,
    )


@jobs_router.get("/{job_id}/download")
def download_job_output(job_id: str, db: Session = Depends(get_db_session)) -> FileResponse:
    job = job_service.get_job(db, job_id)
    if job.status != JobStatus.SUCCESS.value or not job.output_docx_path:
        raise HTTPException(status_code=400, detail="任務尚未完成，暫時無法下載檔案。")

    output_path = Path(job.output_docx_path).resolve()
    allowed_dir = settings.outputs_dir.resolve()
    if not output_path.is_relative_to(allowed_dir):
        raise HTTPException(status_code=403, detail="無效的檔案路徑。")

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"formatted_{job.target_filename.rsplit('.', 1)[0]}.docx",
    )


@jobs_router.delete("/{job_id}")
@CSRFDependency(methods=["DELETE"])
def delete_job(job_id: str, db: Session = Depends(get_db_session)) -> JSONResponse:
    """刪除任務及其所有相關檔案（input、intermediate、output）。"""
    job_service.delete_job(db, job_id)
    return JSONResponse(content={"detail": "任務已刪除。"})
