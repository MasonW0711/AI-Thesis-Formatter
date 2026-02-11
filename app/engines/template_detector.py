from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from app.models.schemas import GROUP_KEYS, GROUP_LABELS, REQUIRED_FONT_NAME, PageRule, ParagraphRule, RuleSet


CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千\d]+章")
SECTION_RE = re.compile(r"^第[一二三四五六七八九十百千\d]+節")
SUBSECTION_RE = re.compile(r"^\d+(?:\.\d+)+")
FIGURE_RE = re.compile(r"^(圖|Figure)\s*\d+", re.IGNORECASE)
TABLE_RE = re.compile(r"^(表|Table)\s*\d+", re.IGNORECASE)
TOC_RE = re.compile(r"^(目錄|table of contents)$", re.IGNORECASE)
ABSTRACT_RE = re.compile(r"^(摘要|abstract)$", re.IGNORECASE)
KEYWORDS_RE = re.compile(r"^(關鍵詞|keywords)\s*[:：]", re.IGNORECASE)


@dataclass
class ParagraphSnapshot:
    index: int
    text: str
    font_name: str
    font_size_pt: float
    bold: bool
    italic: bool
    alignment: str
    line_spacing: float
    space_before_pt: float
    space_after_pt: float
    first_line_indent_pt: float
    is_numbered: bool


class TemplateDetector:
    """從 DOCX 範本偵測版面與段落格式規則。"""

    def detect(self, template_path: Path, template_id: str | None = None, template_name: str = "") -> RuleSet:
        document = Document(str(template_path))

        page_rule = self._extract_page_rule(document)
        grouped_samples: dict[str, list[ParagraphSnapshot]] = defaultdict(list)
        notes: list[str] = []

        for idx, paragraph in enumerate(document.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue

            snapshot = self._snapshot_paragraph(paragraph, idx)
            group = self._classify(snapshot)
            grouped_samples[group].append(snapshot)

        # 若未偵測到內文，使用保守預設值避免後續流程失敗。
        if not grouped_samples.get("body"):
            fallback = ParagraphSnapshot(
                index=0,
                text="",
                font_name=REQUIRED_FONT_NAME,
                font_size_pt=12,
                bold=False,
                italic=False,
                alignment="justify",
                line_spacing=1.5,
                space_before_pt=0,
                space_after_pt=0,
                first_line_indent_pt=24,
                is_numbered=False,
            )
            grouped_samples["body"].append(fallback)
            notes.append("未偵測到可用內文段落，系統已套用預設內文規則。")

        rules: dict[str, ParagraphRule] = {}
        for key in GROUP_KEYS:
            samples = grouped_samples.get(key) or grouped_samples.get("body")
            rules[key] = self._aggregate_rule(samples)
            notes.append(f"「{GROUP_LABELS[key]}」共偵測 {len(grouped_samples.get(key, []))} 筆樣本。")

        return RuleSet(
            template_id=template_id,
            template_name=template_name,
            page=page_rule,
            groups=rules,
            detection_notes=notes,
        )

    def _extract_page_rule(self, document: Document) -> PageRule:
        section = document.sections[0]
        page_number_format = "decimal"
        page_number_start = 1

        sect_pr = section._sectPr
        pg_num_nodes = sect_pr.xpath("./w:pgNumType")
        pg_num_type = pg_num_nodes[0] if pg_num_nodes else None
        if pg_num_type is not None:
            fmt = pg_num_type.get(qn("w:fmt"))
            start = pg_num_type.get(qn("w:start"))
            if fmt in {"decimal", "upperRoman", "lowerRoman"}:
                page_number_format = fmt
            elif fmt:
                page_number_format = "decimal"
            if start and start.isdigit():
                page_number_start = int(start)

        return PageRule(
            page_width_pt=self._length_to_pt(section.page_width, 595.3),
            page_height_pt=self._length_to_pt(section.page_height, 841.9),
            margin_top_pt=self._length_to_pt(section.top_margin, 72.0),
            margin_bottom_pt=self._length_to_pt(section.bottom_margin, 72.0),
            margin_left_pt=self._length_to_pt(section.left_margin, 72.0),
            margin_right_pt=self._length_to_pt(section.right_margin, 72.0),
            header_distance_pt=self._length_to_pt(section.header_distance, 36.0),
            footer_distance_pt=self._length_to_pt(section.footer_distance, 36.0),
            gutter_pt=self._length_to_pt(section.gutter, 0.0),
            page_number_format=page_number_format,
            page_number_start=page_number_start,
        )

    def _snapshot_paragraph(self, paragraph, index: int) -> ParagraphSnapshot:
        run = self._first_meaningful_run(paragraph)
        style = paragraph.style

        font_name = ""
        font_size_pt = 12.0
        bold = False
        italic = False

        if run is not None:
            font_name = self._extract_font_name(run) or ""
            if run.font.size is not None:
                font_size_pt = float(run.font.size.pt)
            bold = bool(run.font.bold)
            italic = bool(run.font.italic)

        if not font_name and style is not None and style.font is not None and style.font.name:
            font_name = style.font.name
        if style is not None and style.font is not None and style.font.size is not None and (run is None or run.font.size is None):
            font_size_pt = float(style.font.size.pt)
        if style is not None and style.font is not None and run is None:
            bold = bool(style.font.bold)
            italic = bool(style.font.italic)

        paragraph_format = paragraph.paragraph_format

        alignment = self._alignment_name(paragraph.alignment)
        line_spacing = self._line_spacing_value(paragraph, font_size_pt)
        space_before_pt = self._length_to_pt(paragraph_format.space_before, 0.0)
        space_after_pt = self._length_to_pt(paragraph_format.space_after, 0.0)
        first_line_indent_pt = self._length_to_pt(paragraph_format.first_line_indent, 0.0)

        is_numbered = False
        p_pr = paragraph._p.pPr
        if p_pr is not None and p_pr.numPr is not None:
            is_numbered = True

        return ParagraphSnapshot(
            index=index,
            text=paragraph.text.strip(),
            font_name=font_name or REQUIRED_FONT_NAME,
            font_size_pt=max(8.0, min(font_size_pt, 36.0)),
            bold=bold,
            italic=italic,
            alignment=alignment,
            line_spacing=max(1.0, min(line_spacing, 3.0)),
            space_before_pt=max(-24.0, min(space_before_pt, 120.0)),
            space_after_pt=max(-24.0, min(space_after_pt, 120.0)),
            first_line_indent_pt=max(-36.0, min(first_line_indent_pt, 72.0)),
            is_numbered=is_numbered,
        )

    def _classify(self, snapshot: ParagraphSnapshot) -> str:
        text = snapshot.text

        if TOC_RE.match(text) or text in {"圖目錄", "表目錄"}:
            return "toc"
        if FIGURE_RE.match(text):
            return "figure_caption"
        if TABLE_RE.match(text):
            return "table_caption"
        if CHAPTER_RE.match(text):
            return "chapter_title"
        if SECTION_RE.match(text):
            return "section_title"
        if SUBSECTION_RE.match(text) or (snapshot.is_numbered and len(text) < 80):
            return "subsection_title"
        if ABSTRACT_RE.match(text) or KEYWORDS_RE.match(text):
            return "front_matter"

        # Centered, bold content in the early pages usually belongs to cover/front matter.
        if snapshot.index < 25 and snapshot.alignment == "center" and (snapshot.bold or snapshot.font_size_pt >= 14):
            return "cover"
        if snapshot.index < 35 and snapshot.alignment == "center":
            return "front_matter"

        # Fallback body paragraph.
        return "body"

    def _aggregate_rule(self, samples: list[ParagraphSnapshot]) -> ParagraphRule:
        # 依需求統一使用標楷體，不隨範本自動切換字型名稱。
        font_name = REQUIRED_FONT_NAME
        alignment = self._mode([s.alignment for s in samples], default="justify")

        font_size = self._median([s.font_size_pt for s in samples], default=12.0)
        line_spacing = self._median([s.line_spacing for s in samples], default=1.5)
        space_before = self._median([s.space_before_pt for s in samples], default=0.0)
        space_after = self._median([s.space_after_pt for s in samples], default=0.0)
        first_indent = self._median([s.first_line_indent_pt for s in samples], default=0.0)

        bold_ratio = sum(1 for s in samples if s.bold) / len(samples)
        italic_ratio = sum(1 for s in samples if s.italic) / len(samples)

        return ParagraphRule(
            font_name=font_name,
            font_size_pt=float(round(font_size, 1)),
            bold=bold_ratio >= 0.5,
            italic=italic_ratio >= 0.5,
            alignment=alignment,
            line_spacing=float(round(line_spacing, 2)),
            space_before_pt=float(round(space_before, 1)),
            space_after_pt=float(round(space_after, 1)),
            first_line_indent_pt=float(round(first_indent, 1)),
        )

    @staticmethod
    def _first_meaningful_run(paragraph):
        for run in paragraph.runs:
            if run.text and run.text.strip():
                return run
        return None

    @staticmethod
    def _extract_font_name(run) -> str | None:
        if run.font is not None and run.font.name:
            return run.font.name

        r_pr = run._element.rPr
        if r_pr is None or r_pr.rFonts is None:
            return None

        fonts = r_pr.rFonts
        east_asia = fonts.get(qn("w:eastAsia"))
        ascii_font = fonts.get(qn("w:ascii"))
        return east_asia or ascii_font

    @staticmethod
    def _alignment_name(alignment) -> str:
        if alignment in (WD_ALIGN_PARAGRAPH.CENTER,):
            return "center"
        if alignment in (WD_ALIGN_PARAGRAPH.RIGHT,):
            return "right"
        if alignment in (WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.DISTRIBUTE):
            return "justify"
        return "left"

    @staticmethod
    def _line_spacing_value(paragraph, font_size_pt: float) -> float:
        value = paragraph.paragraph_format.line_spacing
        if value is None:
            return 1.5

        if isinstance(value, float):
            return float(value)

        if isinstance(value, int):
            # Word sometimes stores exact spacing in twips-like integer points.
            if value <= 10:
                return float(value)
            baseline = font_size_pt if font_size_pt > 0 else 12.0
            return max(1.0, min(3.0, float(value) / baseline))

        if hasattr(value, "pt"):
            baseline = font_size_pt if font_size_pt > 0 else 12.0
            return max(1.0, min(3.0, float(value.pt) / baseline))

        return 1.5

    @staticmethod
    def _length_to_pt(length_obj, default: float) -> float:
        if length_obj is None:
            return default
        if hasattr(length_obj, "pt"):
            return float(length_obj.pt)
        try:
            return float(length_obj)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _mode(values: list[str], default: str) -> str:
        filtered = [v for v in values if v]
        if not filtered:
            return default
        counter = Counter(filtered)
        return counter.most_common(1)[0][0]

    @staticmethod
    def _median(values: list[float], default: float) -> float:
        if not values:
            return default
        try:
            return float(statistics.median(values))
        except statistics.StatisticsError:
            return default
