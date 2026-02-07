"""
論文格式調整系統 - PDF 生成服務
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import List, Dict, Any, Optional
import os

from services.format_analyzer import FormatTemplateData, FormatRule, ElementType


class PDFGenerator:
    """PDF 生成器"""
    
    def __init__(self, output_path: str, template: Optional[FormatTemplateData] = None):
        self.output_path = output_path
        self.template = template
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._create_custom_styles()
    
    def _register_fonts(self):
        """註冊中文字型"""
        # 嘗試註冊系統中的中文字型
        font_paths = [
            # macOS
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            # 通用路徑
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]
        
        self.chinese_font = "Helvetica"  # 預設字型
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    if font_path.endswith('.ttc'):
                        # TTC 字型集需要特殊處理
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    self.chinese_font = "ChineseFont"
                    break
                except Exception as e:
                    print(f"無法註冊字型 {font_path}: {e}")
                    continue
    
    def _create_custom_styles(self):
        """創建自訂樣式"""
        # 標題樣式
        self.styles.add(ParagraphStyle(
            name='ThesisTitle',
            fontName=self.chinese_font,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=24,
            spaceBefore=12
        ))
        
        # 章節標題樣式
        self.styles.add(ParagraphStyle(
            name='ChapterTitle',
            fontName=self.chinese_font,
            fontSize=16,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=18,
            spaceBefore=24
        ))
        
        # 節標題樣式
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontName=self.chinese_font,
            fontSize=14,
            leading=20,
            alignment=TA_LEFT,
            spaceAfter=12,
            spaceBefore=18
        ))
        
        # 小節標題樣式
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            fontName=self.chinese_font,
            fontSize=12,
            leading=18,
            alignment=TA_LEFT,
            spaceAfter=6,
            spaceBefore=12
        ))
        
        # 段落樣式
        self.styles.add(ParagraphStyle(
            name='ThesisParagraph',
            fontName=self.chinese_font,
            fontSize=12,
            leading=18,  # 1.5 倍行距
            alignment=TA_JUSTIFY,
            firstLineIndent=24,
            spaceAfter=6
        ))
        
        # 引用樣式
        self.styles.add(ParagraphStyle(
            name='Quote',
            fontName=self.chinese_font,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            leftIndent=36,
            rightIndent=36,
            spaceAfter=12,
            spaceBefore=12
        ))
    
    def _get_style_for_element(self, element_type: ElementType) -> ParagraphStyle:
        """根據元素類型取得對應的樣式"""
        style_mapping = {
            ElementType.TITLE: 'ThesisTitle',
            ElementType.CHAPTER: 'ChapterTitle',
            ElementType.SECTION: 'SectionTitle',
            ElementType.SUBSECTION: 'SubsectionTitle',
            ElementType.PARAGRAPH: 'ThesisParagraph',
            ElementType.QUOTE: 'Quote',
        }
        
        style_name = style_mapping.get(element_type, 'ThesisParagraph')
        return self.styles[style_name]
    
    def generate(self, elements: List[Dict[str, Any]], watermark: Optional[str] = None) -> str:
        """
        生成 PDF 文件
        
        Args:
            elements: 文件元素列表
            watermark: 浮水印文字（可選）
        
        Returns:
            生成的 PDF 文件路徑
        """
        # 設定頁面尺寸和邊距
        margin_top = 2.5 * cm
        margin_bottom = 2.5 * cm
        margin_left = 3.17 * cm
        margin_right = 2.5 * cm
        
        if self.template:
            margin_top = self.template.margin_top
            margin_bottom = self.template.margin_bottom
            margin_left = self.template.margin_left
            margin_right = self.template.margin_right
        
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
            leftMargin=margin_left,
            rightMargin=margin_right
        )
        
        # 建立文件內容
        story = []
        current_page = 1
        
        for element in elements:
            element_type = element.get("type", ElementType.PARAGRAPH)
            text = element.get("text", "").strip()
            page = element.get("page", 1)
            
            if not text:
                continue
            
            # 處理換頁
            if page > current_page:
                story.append(PageBreak())
                current_page = page
            
            # 取得對應樣式
            if isinstance(element_type, str):
                try:
                    element_type = ElementType(element_type)
                except ValueError:
                    element_type = ElementType.PARAGRAPH
            
            style = self._get_style_for_element(element_type)
            
            # 處理特殊字元
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # 添加段落
            para = Paragraph(text, style)
            story.append(para)
        
        # 生成 PDF
        doc.build(story)
        
        return self.output_path
    
    def add_watermark(self, input_path: str, output_path: str, watermark_text: str):
        """
        為現有 PDF 添加浮水印（使用 pypdf）
        
        Args:
            input_path: 輸入 PDF 路徑
            output_path: 輸出 PDF 路徑
            watermark_text: 浮水印文字
        """
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        # 創建浮水印 PDF
        watermark_buffer = BytesIO()
        c = canvas.Canvas(watermark_buffer, pagesize=A4)
        c.setFillColorRGB(0.8, 0.8, 0.8)  # 淺灰色
        c.setFont("Helvetica", 40)
        c.saveState()
        c.translate(300, 400)
        c.rotate(45)
        c.drawCentredString(0, 0, watermark_text)
        c.restoreState()
        c.save()
        watermark_buffer.seek(0)
        
        # 合併浮水印
        watermark_pdf = PdfReader(watermark_buffer)
        watermark_page = watermark_pdf.pages[0]
        
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)
        
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
