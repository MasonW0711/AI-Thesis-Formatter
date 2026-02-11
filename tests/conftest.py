import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_ROOT = Path(tempfile.mkdtemp(prefix="thesis_formatter_tests_"))
os.environ["THESIS_APP_DATA_DIR"] = str(TEST_ROOT / "data")
os.environ["THESIS_APP_DEBUG"] = "true"
os.environ["THESIS_AI_PROVIDER"] = "off"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)


@pytest.fixture(scope="session")
def client():
    from app.core.config import ensure_directories
    from app.core.database import Base, engine, init_db
    from app.main import create_app
    from app.services.template_service import TemplateService
    from app.core.database import SessionLocal

    ensure_directories()
    Base.metadata.drop_all(bind=engine)
    init_db()

    with SessionLocal() as session:
        TemplateService().reset_default_template(session)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_tmp():
    yield
    shutil.rmtree(TEST_ROOT, ignore_errors=True)
