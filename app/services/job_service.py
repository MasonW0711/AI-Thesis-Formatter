from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.adapters.pdf_to_docx import PdfToDocxAdapter
from app.core.config import settings
from app.core.database import session_scope
from app.engines.format_applier import FormatApplier
from app.models.db_models import JobRecord, JobStatus, TemplateRecord
from app.models.schemas import RuleSet


def _sanitize_filename(name: str) -> str:
    """剝離路徑成分，只保留安全的檔名。"""
    name = Path(name).name
    name = re.sub(r"[^\w\-_.]", "_", name)
    return name or "unnamed"


def _sanitize_error(message: str) -> str:
    """
    移除錯誤訊息中可能的路徑、作業系統、內部變數等敏感資訊，
    避免在使用者面前暴露系統內部細節。
    """
    sanitized = re.sub(r"(/[^/\s]+)+", "[路徑]", message)
    sanitized = re.sub(r"[A-Za-z]:\\[^\\]+", "[路徑]", sanitized)
    sanitized = re.sub(r"\bTHESIS_[A-Z_]+=[^\s]*", "[設定]", sanitized)
    sanitized = re.sub(r"\bOPENAI_[A-Z_]+=[^\s]*", "[設定]", sanitized)
    sanitized = re.sub(r"\bGEMINI_[A-Z_]+=[^\s]*", "[設定]", sanitized)
    sanitized = re.sub(r"\bAIzaSy[A-Za-z0-9_-]+", "[API_KEY]", sanitized)
    sanitized = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[API_KEY]", sanitized)
    sanitized = re.sub(r"ghp_[A-Za-z0-9]+", "[TOKEN]", sanitized)
    sanitized = re.sub(r"sqlalchemy.*?", "[DB]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"Traceback \(most recent call last\):.*", "[系統錯誤]", sanitized, flags=re.DOTALL)
    return sanitized.strip() or "處理失敗，請稍後重試。"


class JobService:
    # Jobs running longer than this are considered stale (process died mid-job)
    STALE_JOB_TIMEOUT_SEC = 3600  # 1 hour

    def __init__(self) -> None:
        self.pdf_adapter = PdfToDocxAdapter()
        self.format_applier = FormatApplier()

    def delete_job(self, session: Session, job_id: str) -> None:
        """Delete a job and all its associated files from disk."""
        job = session.get(JobRecord, job_id)
        if job:
            self._cleanup_job_files(job)
            session.query(JobRecord).filter(JobRecord.id == job_id).delete()
            session.commit()

    def recover_stale_jobs(self, session: Session) -> int:
        """
        Reset any job stuck in RUNNING state (process died mid-job).
        Returns number of jobs recovered.
        """
        from datetime import datetime, timedelta, timezone
        from app.models.db_models import JobStatus

        threshold = datetime.now(timezone.utc) - timedelta(seconds=self.STALE_JOB_TIMEOUT_SEC)
        stale = (
            session.query(JobRecord)
            .filter(
                JobRecord.status == JobStatus.RUNNING.value,
                JobRecord.updated_at < threshold,
            )
            .all()
        )
        for job in stale:
            job.status = JobStatus.QUEUED.value
            job.progress = 0
            job.error_message = "任務處理超時，已自動重置。請重新嘗試。"
        session.commit()
        return len(stale)

    def create_job(
        self,
        session: Session,
        template: TemplateRecord,
        file: UploadFile,
        rules_override: RuleSet | None = None,
    ) -> JobRecord:
        safe_name = _sanitize_filename(file.filename or "target.docx")
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".docx", ".pdf"}:
            raise HTTPException(status_code=400, detail="目標論文僅支援 DOCX 或 PDF 檔案。")

        file_id = str(uuid.uuid4())
        stored_name = f"target_{file_id}{suffix}"
        target_path = settings.uploads_dir / stored_name

        with target_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)

        record = JobRecord(
            id=str(uuid.uuid4()),
            template_id=template.id,
            target_filename=safe_name,
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
            raise HTTPException(status_code=404, detail="找不到指定任務。")
        return record

    def process_job(self, job_id: str, ai_options: dict[str, Any] | None = None) -> None:
        intermediate_docx: Path | None = None
        with session_scope() as session:
            job = session.get(JobRecord, job_id)
            if not job:
                return

            template = session.get(TemplateRecord, job.template_id)
            if not template:
                job.status = JobStatus.FAILED.value
                job.progress = 100
                job.error_message = "找不到對應的格式範本。"
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
                        job.warning_message = _sanitize_error(conversion.warning_message or "")
                    job.progress = 40
                    session.flush()

                output_path = settings.outputs_dir / f"formatted_{job.id}.docx"
                warnings = self.format_applier.apply(
                    source_docx_path,
                    output_path,
                    rules,
                    ai_options=ai_options,
                )
                if warnings:
                    combined = "；".join(_sanitize_error(w) for w in warnings)
                    if job.warning_message:
                        job.warning_message = f"{job.warning_message}；{combined}"
                    else:
                        job.warning_message = combined

                job.output_docx_path = str(output_path)
                job.progress = 100
                job.status = JobStatus.SUCCESS.value
                job.error_message = None
                session.flush()

                # 成功後刪除 input file（Spec: 資料生命週期，處理完成後自動刪除原始檔案）
                self._cleanup_job_files(job, keep_output=True)

            except Exception as exc:  # pragma: no cover - defensive branch
                job.status = JobStatus.FAILED.value
                job.progress = 100
                job.error_message = _sanitize_error(str(exc))
                session.flush()
                self._cleanup_job_files(job)

        # 成功時只清 intermediate PDF 檔；失敗時在 session scope 內已呼叫 _cleanup_job_files
        if intermediate_docx and intermediate_docx.exists():
            try:
                intermediate_docx.unlink(missing_ok=True)
            except OSError:
                pass

    def _cleanup_job_files(self, job: JobRecord, keep_output: bool = False) -> None:
        """清除 Job 的上傳檔案與產出檔案。

        Args:
            job: Job record
            keep_output: True 則保留 output_docx_path（使用者還需要下載）
        """
        paths = [job.target_file_path, job.working_docx_path]
        if not keep_output:
            paths.append(job.output_docx_path)
        for p in paths:
            if p:
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    pass
