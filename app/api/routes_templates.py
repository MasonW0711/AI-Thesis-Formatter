from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.schemas import ApiMessage, RuleSet, TemplateRulesResponse, TemplateSummary
from app.services.template_service import TemplateService


templates_router = APIRouter(prefix="/api/templates", tags=["templates"])
template_service = TemplateService()


@templates_router.get("", response_model=list[TemplateSummary])
def list_templates(db: Session = Depends(get_db_session)) -> list[TemplateSummary]:
    records = template_service.list_templates(db)
    return [
        TemplateSummary(
            id=t.id,
            name=t.name,
            source_filename=t.source_filename,
            is_default=t.is_default,
            created_at=t.created_at.isoformat(),
        )
        for t in records
    ]


@templates_router.post("/default/reset", response_model=TemplateRulesResponse)
def reset_default_template(db: Session = Depends(get_db_session)) -> TemplateRulesResponse:
    record = template_service.reset_default_template(db)
    rules = template_service.get_rules(record)
    return TemplateRulesResponse(
        id=record.id,
        name=record.name,
        source_filename=record.source_filename,
        is_default=record.is_default,
        rules=rules,
    )


@templates_router.post("/upload", response_model=TemplateRulesResponse)
def upload_template(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db_session),
) -> TemplateRulesResponse:
    record = template_service.create_template_from_upload(db, file=file, name=name)
    rules = template_service.get_rules(record)
    return TemplateRulesResponse(
        id=record.id,
        name=record.name,
        source_filename=record.source_filename,
        is_default=record.is_default,
        rules=rules,
    )


@templates_router.get("/{template_id}/rules", response_model=TemplateRulesResponse)
def get_template_rules(template_id: str, db: Session = Depends(get_db_session)) -> TemplateRulesResponse:
    record = template_service.get_template(db, template_id)
    rules = template_service.get_rules(record)
    return TemplateRulesResponse(
        id=record.id,
        name=record.name,
        source_filename=record.source_filename,
        is_default=record.is_default,
        rules=rules,
    )


@templates_router.patch("/{template_id}/rules", response_model=TemplateRulesResponse)
def update_template_rules(template_id: str, rules: RuleSet, db: Session = Depends(get_db_session)) -> TemplateRulesResponse:
    record = template_service.get_template(db, template_id)
    updated = template_service.update_rules(db, record, rules)
    result_rules = template_service.get_rules(updated)
    return TemplateRulesResponse(
        id=updated.id,
        name=updated.name,
        source_filename=updated.source_filename,
        is_default=updated.is_default,
        rules=result_rules,
    )
