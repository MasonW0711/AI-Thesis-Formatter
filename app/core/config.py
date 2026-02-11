from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    host: str
    port: int
    debug: bool
    max_upload_size_mb: int
    base_dir: Path
    data_dir: Path
    templates_dir: Path
    uploads_dir: Path
    work_dir: Path
    outputs_dir: Path
    database_path: Path
    database_url: str
    defaults_dir: Path
    default_template_source: Path


def build_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("THESIS_APP_DATA_DIR", base_dir / "data"))

    templates_dir = data_dir / "templates"
    uploads_dir = data_dir / "uploads"
    work_dir = data_dir / "work"
    outputs_dir = data_dir / "outputs"
    database_path = data_dir / "app.db"

    defaults_dir = base_dir / "defaults"
    default_template_source = defaults_dir / "AI-THESIS MODEL.docx"

    return Settings(
        app_name="自動調整論文格式",
        app_version="1.0.0",
        host=os.getenv("THESIS_APP_HOST", "127.0.0.1"),
        port=int(os.getenv("THESIS_APP_PORT", "8765")),
        debug=os.getenv("THESIS_APP_DEBUG", "false").lower() in {"1", "true", "yes"},
        max_upload_size_mb=int(os.getenv("THESIS_MAX_UPLOAD_MB", "50")),
        base_dir=base_dir,
        data_dir=data_dir,
        templates_dir=templates_dir,
        uploads_dir=uploads_dir,
        work_dir=work_dir,
        outputs_dir=outputs_dir,
        database_path=database_path,
        database_url=f"sqlite:///{database_path.as_posix()}",
        defaults_dir=defaults_dir,
        default_template_source=default_template_source,
    )


settings = build_settings()


def ensure_directories() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.templates_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.work_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
