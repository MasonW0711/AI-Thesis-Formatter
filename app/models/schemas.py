from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Alignment = Literal["left", "center", "right", "justify"]
PageNumberFormat = Literal["decimal", "upperRoman", "lowerRoman", "none"]
REQUIRED_FONT_NAME = "標楷體"

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

GROUP_LABELS = {
    "cover": "封面與書名頁",
    "front_matter": "前置頁（摘要、關鍵詞）",
    "chapter_title": "章標題（第 X 章）",
    "section_title": "節標題（第 X 節）",
    "subsection_title": "小節標題（數字編號）",
    "body": "一般內文段落",
    "figure_caption": "圖標題說明",
    "table_caption": "表標題說明",
    "toc": "索引頁標題（目錄／圖目錄／表目錄）",
}

GROUP_DESCRIPTIONS = {
    "cover": "套用於論文封面與題名頁。建議使用較大字級、置中對齊、段前後間距適中，讓校名、系所、論文題目與作者資訊有清楚視覺層次。",
    "front_matter": "套用於摘要、關鍵詞、致謝等前置頁內文。重點是段落可讀性與一致性，通常使用固定行距、左右對齊與適量首行縮排。",
    "chapter_title": "套用於章層級標題（如：第一章 緒論）。建議採置中、較大字級，必要時加粗，與內文形成明確主層級區隔。",
    "section_title": "套用於節層級標題（如：第一節 研究背景）。建議字級略小於章標題，維持規律段前段後間距，避免與章標題混淆。",
    "subsection_title": "套用於小節標題（如：1.1.1 問題定義）。建議靠左對齊、字級與內文接近但可加粗，強化章節細部分層。",
    "body": "套用於論文主要內文段落。通常設定為左右對齊、固定行距與首行縮排，確保長篇內容閱讀節奏一致且正式。",
    "figure_caption": "套用於圖說明文字（如：圖 1-1 系統架構）。建議置中或依校規靠左，並使用較內文略小或相同字級以保持版面平衡。",
    "table_caption": "套用於表說明文字（如：表 1-1 樣本分布）。建議與圖標題規則一致，維持固定間距與對齊，提升整體專業一致性。",
    "toc": "套用於目錄、圖目錄、表目錄的標題段落。建議置中、字級略大，並與章節標題風格一致，方便讀者辨識索引區塊。",
}


class ParagraphRule(BaseModel):
    font_name: str = REQUIRED_FONT_NAME
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

    @field_validator("font_name", mode="before")
    @classmethod
    def enforce_required_font(cls, _value: str) -> str:
        # 依台灣論文格式需求，統一強制使用標楷體。
        return REQUIRED_FONT_NAME


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
