from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Alignment = Literal["left", "center", "right", "justify"]
PageNumberFormat = Literal["decimal", "upperRoman", "lowerRoman", "none"]

GROUP_KEYS = [
    "cover",
    "front_matter",
    "chapter_title",
    "section_title",
    "subsection_title",
    "body",
    "figure_caption",
    "table_caption",
    "toc",
]


class ParagraphRule(BaseModel):
    font_name: str = "Times New Roman"
    font_size_pt: float = 12.0
    bold: bool = False
    italic: bool = False
    alignment: Alignment = "justify"
    line_spacing: float = 1.5
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    first_line_indent_pt: float = 0.0

    @field_validator("font_size_pt")
    @classmethod
    def clamp_font_size(cls, value: float) -> float:
        return float(max(8.0, min(36.0, value)))

    @field_validator("line_spacing")
    @classmethod
    def clamp_line_spacing(cls, value: float) -> float:
        return float(max(1.0, min(3.0, value)))


class PageRule(BaseModel):
    page_width_pt: float = 595.3
    page_height_pt: float = 841.9
    margin_top_pt: float = 72.0
    margin_bottom_pt: float = 72.0
    margin_left_pt: float = 72.0
    margin_right_pt: float = 72.0
    header_distance_pt: float = 36.0
    footer_distance_pt: float = 36.0
    gutter_pt: float = 0.0
    page_number_format: PageNumberFormat = "decimal"
    page_number_start: int = 1


class RuleSet(BaseModel):
    version: str = "1.0"
    template_id: str | None = None
    template_name: str = ""
    page: PageRule = Field(default_factory=PageRule)
    groups: dict[str, ParagraphRule] = Field(
        default_factory=lambda: {
            "cover": ParagraphRule(alignment="center", font_size_pt=16, bold=True, line_spacing=1.0),
            "front_matter": ParagraphRule(alignment="justify", font_size_pt=12, line_spacing=1.5, first_line_indent_pt=24),
            "chapter_title": ParagraphRule(alignment="center", font_size_pt=16, bold=True, line_spacing=1.5),
            "section_title": ParagraphRule(alignment="center", font_size_pt=14, bold=True, line_spacing=1.5),
            "subsection_title": ParagraphRule(alignment="left", font_size_pt=12, bold=True, line_spacing=1.5),
            "body": ParagraphRule(alignment="justify", font_size_pt=12, line_spacing=1.5, first_line_indent_pt=24),
            "figure_caption": ParagraphRule(alignment="center", font_size_pt=11, line_spacing=1.2),
            "table_caption": ParagraphRule(alignment="center", font_size_pt=11, line_spacing=1.2),
            "toc": ParagraphRule(alignment="center", font_size_pt=14, bold=True, line_spacing=1.0),
        }
    )
    detection_notes: list[str] = Field(default_factory=list)

    @field_validator("groups")
    @classmethod
    def ensure_group_keys(cls, groups: dict[str, ParagraphRule]) -> dict[str, ParagraphRule]:
        for key in GROUP_KEYS:
            groups.setdefault(key, ParagraphRule())
        return groups


class TemplateSummary(BaseModel):
    id: str
    name: str
    source_filename: str
    is_default: bool
    created_at: str


class TemplateRulesResponse(BaseModel):
    id: str
    name: str
    source_filename: str
    is_default: bool
    rules: RuleSet


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    template_id: str
    target_filename: str
    warning_message: str | None = None
    error_message: str | None = None
    conversion_confidence: float | None = None
    download_url: str | None = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    progress: int


class ApiMessage(BaseModel):
    message: str
