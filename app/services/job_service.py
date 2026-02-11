from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.adapters.pdf_to_docx import PdfToDocxAdapter
from app.core.config import settings
from app.core.database import session_scope
from app.engines.format_applier import FormatApplier
from app.models.db_models import JobRecord, JobStatus, TemplateRecord
from app.models.schemas import RuleSet


class JobService:
    def __init__(self) -> None:
        self.pdf_adapter = PdfToDocxAdapter()
        self.format_applier = FormatApplier()

    def create_job(
        self,
        session: Session,
        template: TemplateRecord,
        file: UploadFile,
        rules_override: RuleSet | None = None,
    ) -> JobRecord:
        suffix = Path(file.filename or "target.docx").suffix.lower()
        if suffix not in {".docx", ".pdf"}:
            raise HTTPException(status_code=400, detail="Target file must be DOCX or PDF.")

        file_id = str(uuid.uuid4())
        stored_name = f"target_{file_id}{suffix}"
        target_path = settings.uploads_dir / stored_name

        with target_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)

        record = JobRecord(
            id=str(uuid.uuid4()),
            template_id=template.id,
            target_filename=file.filename or stored_name,
            target_file_path=str(target_path),
            target_kind="pdf" if suffix == ".pdf" else "docx",
            status=JobStatus.QUEUED.value,
            progress=0,
            rules_override_json=json.dumps(rules_override.model_dump(), ensure_ascii=False) if rules_override else None,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def get_job(self, session: Session, job_id: str) -> JobRecord:
        record = session.get(JobRecord, job_id)
        if not record:
            raise HTTPException(status_code=404, detail="Job not found.")
        return record

    def process_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(JobRecord, job_id)
            if not job:
                return

            template = session.get(TemplateRecord, job.template_id)
            if not template:
                job.status = JobStatus.FAILED.value
                job.progress = 100
                job.error_message = "Template not found."
                return

            try:
                job.status = JobStatus.RUNNING.value
                job.progress = 5
                session.flush()

                if job.rules_override_json:
                    rules = RuleSet.model_validate_json(job.rules_override_json)
                else:
                    rules = RuleSet.model_validate_json(template.rules_json)

                rules = rules.model_copy(update={"template_id": template.id, "template_name": template.name})

                source_docx_path = Path(job.target_file_path)
                if job.target_kind == "pdf":
                    intermediate_docx = settings.work_dir / f"intermediate_{job.id}.docx"
                    conversion = self.pdf_adapter.convert(source_docx_path, intermediate_docx)
                    source_docx_path = conversion.output_docx
                    job.working_docx_path = str(intermediate_docx)
                    job.conversion_confidence = conversion.confidence
                    if conversion.warning_message:
                        job.warning_message = conversion.warning_message
                    job.progress = 40
                    session.flush()

                output_path = settings.outputs_dir / f"formatted_{job.id}.docx"
                self.format_applier.apply(source_docx_path, output_path, rules)

                job.output_docx_path = str(output_path)
                job.progress = 100
                job.status = JobStatus.SUCCESS.value
                job.error_message = None
                session.flush()
            except Exception as exc:  # pragma: no cover - defensive branch
                job.status = JobStatus.FAILED.value
                job.progress = 100
                job.error_message = str(exc)
                session.flush()
