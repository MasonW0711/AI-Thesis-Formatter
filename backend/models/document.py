"""
論文格式調整系統 - 文件資料模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.sql import func
from database import Base
import enum


class DocumentStatus(str, enum.Enum):
    """文件處理狀態"""
    UPLOADED = "uploaded"       # 已上傳
    PROCESSING = "processing"   # 處理中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 處理失敗


class Document(Base):
    """文件資料模型"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=False)
    processed_path = Column(String(500), nullable=True)
    status = Column(String(20), default=DocumentStatus.UPLOADED.value)
    format_template = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"
