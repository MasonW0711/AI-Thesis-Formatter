from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engines.template_detector import TemplateDetector
from app.models.db_models import TemplateRecord
from app.models.schemas import RuleSet


class TemplateService:
    def __init__(self) -> None:
        self.detector = TemplateDetector()

    def list_templates(self, session: Session) -> list[TemplateRecord]:
        return session.query(TemplateRecord).order_by(TemplateRecord.created_at.desc()).all()

    def get_template(self, session: Session, template_id: str) -> TemplateRecord:
        template = session.get(TemplateRecord, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found.")
        return template

    def reset_default_template(self, session: Session) -> TemplateRecord:
        source = settings.default_template_source
        if not source.exists():
            raise HTTPException(status_code=500, detail="Default template file is missing.")

        target_path = settings.templates_dir / "default_AI-THESIS_MODEL.docx"
        shutil.copyfile(source, target_path)

        existing_default = (
            session.query(TemplateRecord)
            .filter(TemplateRecord.is_default.is_(True))
            .order_by(TemplateRecord.created_at.desc())
            .first()
        )

        if existing_default:
            existing_default.name = "Default AI Thesis Template"
            existing_default.source_filename = source.name
            existing_default.file_path = str(target_path)
            detected = self.detector.detect(target_path, template_id=existing_default.id, template_name=existing_default.name)
            existing_default.rules_json = json.dumps(detected.model_dump(), ensure_ascii=False)
            template = existing_default
        else:
            template = TemplateRecord(
                id=str(uuid.uuid4()),
                name="Default AI Thesis Template",
                source_filename=source.name,
                file_path=str(target_path),
                rules_json="{}",
                is_default=True,
            )
            detected = self.detector.detect(target_path, template_id=template.id, template_name=template.name)
            template.rules_json = json.dumps(detected.model_dump(), ensure_ascii=False)
            session.add(template)

        # Ensure only one default template.
        session.query(TemplateRecord).filter(TemplateRecord.id != template.id).update({TemplateRecord.is_default: False})

        session.commit()
        session.refresh(template)
        return template

    def create_template_from_upload(self, session: Session, file: UploadFile, name: str | None = None) -> TemplateRecord:
        suffix = Path(file.filename or "template.docx").suffix.lower()
        if suffix != ".docx":
            raise HTTPException(status_code=400, detail="Only DOCX template files are supported.")

        template_id = str(uuid.uuid4())
        filename = f"template_{template_id}.docx"
        file_path = settings.templates_dir / filename

        with file_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)

        template_name = name.strip() if name and name.strip() else f"Uploaded Template {template_id[:8]}"
        detected = self.detector.detect(file_path, template_id=template_id, template_name=template_name)

        record = TemplateRecord(
            id=template_id,
            name=template_name,
            source_filename=file.filename or filename,
            file_path=str(file_path),
            rules_json=json.dumps(detected.model_dump(), ensure_ascii=False),
            is_default=False,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def get_rules(self, template: TemplateRecord) -> RuleSet:
        return RuleSet.model_validate_json(template.rules_json)

    def update_rules(self, session: Session, template: TemplateRecord, rules: RuleSet) -> TemplateRecord:
        payload = rules.model_copy(update={"template_id": template.id, "template_name": template.name})
        template.rules_json = json.dumps(payload.model_dump(), ensure_ascii=False)
        session.commit()
        session.refresh(template)
        return template
