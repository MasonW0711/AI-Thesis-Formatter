"""
論文格式調整系統 - 範本資料模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class FormatTemplate(Base):
    """格式範本資料模型"""
    __tablename__ = "format_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    original_path = Column(String(500), nullable=False)
    
    # 學習到的格式規則 (JSON)
    learned_rules = Column(JSON, nullable=True)
    
    # 統計資訊
    page_count = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<FormatTemplate(id={self.id}, name='{self.name}')>"
