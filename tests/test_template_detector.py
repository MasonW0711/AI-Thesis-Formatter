from app.core.config import settings
from app.engines.template_detector import TemplateDetector
from app.models.schemas import REQUIRED_FONT_NAME


def test_detect_default_template_rules():
    detector = TemplateDetector()
    rules = detector.detect(
        template_path=settings.default_template_source,
        template_id="test-default",
        template_name="default",
    )

    assert rules.template_id == "test-default"
    assert rules.page.margin_left_pt > 40
    assert rules.page.margin_right_pt > 40
    assert "body" in rules.groups
    assert "chapter_title" in rules.groups
    assert 8 <= rules.groups["body"].font_size_pt <= 18
    assert rules.groups["chapter_title"].bold is True
    assert all(group.font_name == REQUIRED_FONT_NAME for group in rules.groups.values())
    assert len(rules.detection_notes) > 0
