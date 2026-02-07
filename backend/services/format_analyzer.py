"""
論文格式調整系統 - 格式分析服務
支援從範本 PDF 學習格式規則
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
from collections import Counter
import statistics


class ElementType(str, Enum):
    """文件元素類型"""
    TITLE = "title"              # 論文標題
    CHAPTER = "chapter"          # 章節標題
    SECTION = "section"          # 小節標題
    SUBSECTION = "subsection"    # 小小節標題
    PARAGRAPH = "paragraph"      # 段落
    QUOTE = "quote"              # 引用
    FIGURE = "figure"            # 圖表
    TABLE = "table"              # 表格
    FOOTNOTE = "footnote"        # 註腳
    PAGE_NUMBER = "page_number"  # 頁碼
    HEADER = "header"            # 頁首
    FOOTER = "footer"            # 頁尾
    UNKNOWN = "unknown"          # 未知


@dataclass
class FormatRule:
    """格式規則"""
    element_type: ElementType
    font_name: str = "標楷體"
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    alignment: str = "left"  # left, center, right, justify
    line_spacing: float = 1.5
    paragraph_spacing_before: float = 0
    paragraph_spacing_after: float = 12
    first_line_indent: float = 24  # 首行縮排 (pt)
    margin_left: float = 0
    margin_right: float = 0


@dataclass
class LearnedFormatRules:
    """從範本學習到的格式規則"""
    # 頁面設定
    page_width: float = 595.276   # A4 寬度 (pt)
    page_height: float = 841.89   # A4 高度 (pt)
    margin_top: float = 72
    margin_bottom: float = 72
    margin_left: float = 72
    margin_right: float = 72
    
    # 主要字型
    main_font_name: str = ""
    main_font_size: float = 12.0
    
    # 標題格式
    title_font_size: float = 18.0
    title_is_bold: bool = True
    
    chapter_font_size: float = 16.0
    chapter_is_bold: bool = True
    
    section_font_size: float = 14.0
    section_is_bold: bool = True
    
    # 段落格式
    paragraph_font_size: float = 12.0
    line_spacing: float = 1.5
    first_line_indent: float = 24.0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnedFormatRules":
        """從字典建立"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class FormatTemplateData:
    """格式範本資料"""
    name: str
    description: str
    page_width: float = 595.276  # A4 寬度 (pt)
    page_height: float = 841.89  # A4 高度 (pt)
    margin_top: float = 72       # 上邊距 (1 inch = 72pt)
    margin_bottom: float = 72
    margin_left: float = 90      # 左邊距 (約 3.17cm)
    margin_right: float = 72
    rules: Dict[ElementType, FormatRule] = field(default_factory=dict)


# 預設的論文格式範本（基於常見台灣學術論文規範）
DEFAULT_THESIS_TEMPLATE = FormatTemplateData(
    name="台灣學術論文標準格式",
    description="適用於大多數台灣大專院校的論文格式",
    margin_top=72,
    margin_bottom=72,
    margin_left=90,
    margin_right=72,
    rules={
        ElementType.TITLE: FormatRule(
            element_type=ElementType.TITLE,
            font_name="標楷體",
            font_size=18,
            is_bold=True,
            alignment="center",
            paragraph_spacing_after=24
        ),
        ElementType.CHAPTER: FormatRule(
            element_type=ElementType.CHAPTER,
            font_name="標楷體",
            font_size=16,
            is_bold=True,
            alignment="center",
            paragraph_spacing_before=24,
            paragraph_spacing_after=18
        ),
        ElementType.SECTION: FormatRule(
            element_type=ElementType.SECTION,
            font_name="標楷體",
            font_size=14,
            is_bold=True,
            alignment="left",
            paragraph_spacing_before=18,
            paragraph_spacing_after=12
        ),
        ElementType.SUBSECTION: FormatRule(
            element_type=ElementType.SUBSECTION,
            font_name="標楷體",
            font_size=12,
            is_bold=True,
            alignment="left",
            paragraph_spacing_before=12,
            paragraph_spacing_after=6
        ),
        ElementType.PARAGRAPH: FormatRule(
            element_type=ElementType.PARAGRAPH,
            font_name="標楷體",
            font_size=12,
            alignment="justify",
            line_spacing=1.5,
            first_line_indent=24
        ),
        ElementType.QUOTE: FormatRule(
            element_type=ElementType.QUOTE,
            font_name="標楷體",
            font_size=10,
            alignment="left",
            margin_left=36,
            margin_right=36,
            line_spacing=1.0
        ),
        ElementType.FOOTNOTE: FormatRule(
            element_type=ElementType.FOOTNOTE,
            font_name="標楷體",
            font_size=9,
            alignment="left"
        ),
        ElementType.PAGE_NUMBER: FormatRule(
            element_type=ElementType.PAGE_NUMBER,
            font_name="Times New Roman",
            font_size=12,
            alignment="center"
        ),
    }
)


class FormatAnalyzer:
    """格式分析器"""
    
    def __init__(self):
        self.templates: Dict[str, FormatTemplateData] = {
            "default": DEFAULT_THESIS_TEMPLATE
        }
    
    def get_template(self, template_name: str = "default") -> Optional[FormatTemplateData]:
        """取得格式範本"""
        return self.templates.get(template_name)
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """取得所有可用的格式範本"""
        return [
            {"name": name, "description": template.description}
            for name, template in self.templates.items()
        ]
    
    def learn_format_from_pdf(self, document_structure: Any) -> LearnedFormatRules:
        """
        從 PDF 文件結構學習格式規則
        
        Args:
            document_structure: 從 PDFParser 解析得到的文件結構
        
        Returns:
            LearnedFormatRules: 學習到的格式規則
        """
        rules = LearnedFormatRules()
        
        if not document_structure or not document_structure.pages:
            return rules
        
        # 收集所有文字區塊的格式資訊
        all_font_sizes: List[float] = []
        all_font_names: List[str] = []
        all_left_positions: List[float] = []
        all_right_positions: List[float] = []
        all_top_positions: List[float] = []
        large_font_sizes: List[float] = []  # 用於識別標題
        
        for page in document_structure.pages:
            rules.page_width = page.width
            rules.page_height = page.height
            
            for block in page.text_blocks:
                if block.font_size > 0:
                    all_font_sizes.append(block.font_size)
                if block.font_name:
                    all_font_names.append(block.font_name)
                
                # 收集位置資訊以推算邊距
                if block.bbox:
                    all_left_positions.append(block.bbox[0])
                    all_right_positions.append(block.bbox[2])
                    all_top_positions.append(block.bbox[1])
                
                # 識別大字型（可能是標題）
                if block.font_size > 14:
                    large_font_sizes.append(block.font_size)
        
        # 分析主要字型
        if all_font_names:
            font_counter = Counter(all_font_names)
            rules.main_font_name = font_counter.most_common(1)[0][0]
        
        # 分析主要字型大小
        if all_font_sizes:
            rules.main_font_size = statistics.mode(all_font_sizes) if all_font_sizes else 12.0
            rules.paragraph_font_size = rules.main_font_size
        
        # 推算邊距
        if all_left_positions:
            rules.margin_left = min(all_left_positions)
        if all_right_positions and rules.page_width:
            rules.margin_right = rules.page_width - max(all_right_positions)
        if all_top_positions:
            rules.margin_top = min(all_top_positions)
        
        # 分析標題格式
        if large_font_sizes:
            sorted_sizes = sorted(set(large_font_sizes), reverse=True)
            if len(sorted_sizes) >= 1:
                rules.title_font_size = sorted_sizes[0]
            if len(sorted_sizes) >= 2:
                rules.chapter_font_size = sorted_sizes[1] if sorted_sizes[1] != sorted_sizes[0] else sorted_sizes[0] - 2
            if len(sorted_sizes) >= 3:
                rules.section_font_size = sorted_sizes[2]
        
        # 估算行距（基於連續文字區塊的間距）
        # 這是一個簡化的估算
        rules.line_spacing = 1.5  # 預設值
        
        # 估算首行縮排
        if all_left_positions and rules.margin_left:
            indent_offsets = [pos - rules.margin_left for pos in all_left_positions if pos > rules.margin_left + 10]
            if indent_offsets:
                rules.first_line_indent = statistics.mode(indent_offsets) if indent_offsets else 24
        
        return rules
    
    def create_template_from_rules(
        self, 
        name: str, 
        rules: LearnedFormatRules
    ) -> FormatTemplateData:
        """
        從學習到的規則建立格式範本
        """
        return FormatTemplateData(
            name=name,
            description=f"從 PDF 學習的格式範本",
            page_width=rules.page_width,
            page_height=rules.page_height,
            margin_top=rules.margin_top,
            margin_bottom=rules.margin_bottom,
            margin_left=rules.margin_left,
            margin_right=rules.margin_right,
            rules={
                ElementType.TITLE: FormatRule(
                    element_type=ElementType.TITLE,
                    font_name=rules.main_font_name or "標楷體",
                    font_size=rules.title_font_size,
                    is_bold=rules.title_is_bold,
                    alignment="center"
                ),
                ElementType.CHAPTER: FormatRule(
                    element_type=ElementType.CHAPTER,
                    font_name=rules.main_font_name or "標楷體",
                    font_size=rules.chapter_font_size,
                    is_bold=rules.chapter_is_bold,
                    alignment="center"
                ),
                ElementType.SECTION: FormatRule(
                    element_type=ElementType.SECTION,
                    font_name=rules.main_font_name or "標楷體",
                    font_size=rules.section_font_size,
                    is_bold=rules.section_is_bold,
                    alignment="left"
                ),
                ElementType.PARAGRAPH: FormatRule(
                    element_type=ElementType.PARAGRAPH,
                    font_name=rules.main_font_name or "標楷體",
                    font_size=rules.paragraph_font_size,
                    alignment="justify",
                    line_spacing=rules.line_spacing,
                    first_line_indent=rules.first_line_indent
                ),
            }
        )
    
    def analyze_element_type(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        position_y: float,
        page_height: float
    ) -> ElementType:
        """分析文字區塊的元素類型"""
        text_stripped = text.strip()
        
        # 空白文字
        if not text_stripped:
            return ElementType.UNKNOWN
        
        # 檢查是否為頁碼（通常在頁面底部，且是純數字）
        if position_y > page_height * 0.9 and text_stripped.isdigit():
            return ElementType.PAGE_NUMBER
        
        # 檢查是否為章節標題（根據字型大小和粗體）
        if is_bold:
            if font_size >= 16:
                # 檢查是否包含章節關鍵字
                if any(keyword in text_stripped for keyword in ["第", "章", "Chapter"]):
                    return ElementType.CHAPTER
                return ElementType.TITLE
            elif font_size >= 14:
                return ElementType.SECTION
            elif font_size >= 12:
                return ElementType.SUBSECTION
        
        # 檢查是否為引用（通常縮排較多或字型較小）
        if font_size < 11:
            return ElementType.QUOTE
        
        # 預設為段落
        return ElementType.PARAGRAPH
    
    def extract_document_structure(
        self,
        document_structure: Any
    ) -> List[Dict[str, Any]]:
        """從文件結構中提取並分類各元素"""
        elements = []
        
        for page in document_structure.pages:
            for block in page.text_blocks:
                element_type = self.analyze_element_type(
                    text=block.text,
                    font_size=block.font_size,
                    is_bold=block.is_bold,
                    position_y=block.bbox[1],
                    page_height=page.height
                )
                
                elements.append({
                    "type": element_type,
                    "text": block.text,
                    "page": page.page_number,
                    "original_format": {
                        "font_name": block.font_name,
                        "font_size": block.font_size,
                        "is_bold": block.is_bold,
                        "is_italic": block.is_italic,
                        "bbox": block.bbox
                    }
                })
        
        return elements
