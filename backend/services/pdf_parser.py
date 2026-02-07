"""
論文格式調整系統 - PDF 解析服務
使用 pypdf 和 pdfplumber 進行 PDF 解析
"""
import pdfplumber
from pypdf import PdfReader
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import os


@dataclass
class TextBlock:
    """文字區塊"""
    text: str
    bbox: tuple  # (x0, y0, x1, y1)
    font_name: str = ""
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False


@dataclass
class PageContent:
    """頁面內容"""
    page_number: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)


@dataclass
class DocumentStructure:
    """文件結構"""
    filename: str
    page_count: int
    pages: List[PageContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFParser:
    """PDF 解析器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.pdf: Optional[pdfplumber.PDF] = None
    
    def open(self) -> bool:
        """開啟 PDF 文件"""
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"找不到文件: {self.file_path}")
            self.pdf = pdfplumber.open(self.file_path)
            return True
        except Exception as e:
            print(f"開啟 PDF 失敗: {e}")
            return False
    
    def close(self):
        """關閉 PDF 文件"""
        if self.pdf:
            self.pdf.close()
            self.pdf = None
    
    def parse(self) -> Optional[DocumentStructure]:
        """解析 PDF 文件"""
        if not self.pdf:
            if not self.open():
                return None
        
        # 使用 pypdf 取得 metadata
        metadata = {}
        try:
            reader = PdfReader(self.file_path)
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                }
        except Exception as e:
            print(f"讀取 metadata 失敗: {e}")
        
        structure = DocumentStructure(
            filename=os.path.basename(self.file_path),
            page_count=len(self.pdf.pages),
            metadata=metadata
        )
        
        for page_num, page in enumerate(self.pdf.pages):
            page_content = self._parse_page(page, page_num + 1)
            structure.pages.append(page_content)
        
        return structure
    
    def _parse_page(self, page, page_number: int) -> PageContent:
        """解析單一頁面"""
        page_content = PageContent(
            page_number=page_number,
            width=page.width,
            height=page.height
        )
        
        # 取得文字和字型資訊
        chars = page.chars
        
        # 將字元組合成文字區塊
        current_block = []
        current_font = ""
        current_size = 12.0
        current_bbox = None
        
        for char in chars:
            char_font = char.get("fontname", "")
            char_size = char.get("size", 12.0)
            char_text = char.get("text", "")
            char_bbox = (char.get("x0", 0), char.get("top", 0), 
                        char.get("x1", 0), char.get("bottom", 0))
            
            # 如果字型或大小改變，保存當前區塊
            if current_block and (char_font != current_font or abs(char_size - current_size) > 0.5):
                text = "".join(current_block)
                if text.strip():
                    text_block = TextBlock(
                        text=text,
                        bbox=current_bbox or (0, 0, 0, 0),
                        font_name=current_font,
                        font_size=current_size,
                        is_bold="bold" in current_font.lower() or "black" in current_font.lower(),
                        is_italic="italic" in current_font.lower() or "oblique" in current_font.lower()
                    )
                    page_content.text_blocks.append(text_block)
                current_block = []
                current_bbox = None
            
            current_block.append(char_text)
            current_font = char_font
            current_size = char_size
            
            if current_bbox is None:
                current_bbox = char_bbox
            else:
                current_bbox = (
                    min(current_bbox[0], char_bbox[0]),
                    min(current_bbox[1], char_bbox[1]),
                    max(current_bbox[2], char_bbox[2]),
                    max(current_bbox[3], char_bbox[3])
                )
        
        # 保存最後一個區塊
        if current_block:
            text = "".join(current_block)
            if text.strip():
                text_block = TextBlock(
                    text=text,
                    bbox=current_bbox or (0, 0, 0, 0),
                    font_name=current_font,
                    font_size=current_size,
                    is_bold="bold" in current_font.lower(),
                    is_italic="italic" in current_font.lower()
                )
                page_content.text_blocks.append(text_block)
        
        # 取得圖片資訊
        images = page.images
        for img in images:
            page_content.images.append({
                "bbox": (img.get("x0", 0), img.get("top", 0), 
                        img.get("x1", 0), img.get("bottom", 0)),
                "width": img.get("width", 0),
                "height": img.get("height", 0)
            })
        
        return page_content
    
    def extract_text(self) -> str:
        """提取全部文字"""
        if not self.pdf:
            if not self.open():
                return ""
        
        text_parts = []
        for page in self.pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def get_page_count(self) -> int:
        """取得頁數"""
        if not self.pdf:
            if not self.open():
                return 0
        return len(self.pdf.pages)
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
