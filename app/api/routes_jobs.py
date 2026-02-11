from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db_session
from app.models.db_models import JobStatus
from app.models.schemas import JobCreateResponse, JobStatusResponse, RuleSet
from app.services.job_service import JobService
from app.services.template_service import TemplateService


jobs_router = APIRouter(prefix="/api/jobs", tags=["jobs"])
job_service = JobService()
template_service = TemplateService()


def _upload_size(upload: UploadFile) -> int:
    position = upload.file.tell()
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(position)
    return size


@jobs_router.post("", response_model=JobCreateResponse)
def create_job(
    background_tasks: BackgroundTasks,
    template_id: str = Form(...),
    target_file: UploadFile = File(...),
    rules_override: str | None = Form(default=None),
    db: Session = Depends(get_db_session),
) -> JobCreateResponse:
    size_bytes = _upload_size(target_file)
    if size_bytes > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File size exceeds {settings.max_upload_size_mb} MB.")

    template = template_service.get_template(db, template_id)

    parsed_override: RuleSet | None = None
    if rules_override:
        try:
            payload = json.loads(rules_override)
            parsed_override = RuleSet.model_validate(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid rules_override payload: {exc}") from exc

    job = job_service.create_job(db, template=template, file=target_file, rules_override=parsed_override)
    background_tasks.add_task(job_service.process_job, job.id)

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
        raise HTTPException(status_code=400, detail="Job has not produced a downloadable file.")

    output_path = job.output_docx_path
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"formatted_{job.target_filename.rsplit('.', 1)[0]}.docx",
    )
