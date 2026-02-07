"""
論文格式調整系統 - FastAPI 應用主程式
支援 PDF 和 Word 文件的範本學習和格式套用功能
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from database import get_db, init_db, engine, Base
from models.document import Document, DocumentStatus
from models.template import FormatTemplate
from services.pdf_parser import PDFParser
from services.format_analyzer import FormatAnalyzer, LearnedFormatRules
from services.pdf_generator import PDFGenerator
from services.docx_parser import DocxParser
from services.docx_generator import DocxGenerator

# 創建 FastAPI 應用
app = FastAPI(
    title="論文格式調整系統",
    description="自動學習範本格式並調整論文排版的 API 服務（支援 PDF 和 Word）",
    version="3.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 檔案存儲路徑
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 確保目錄存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# 格式分析器實例
format_analyzer = FormatAnalyzer()

# 支援的文件格式
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc'}


def get_file_type(filename: str) -> str:
    """判斷文件類型"""
    ext = os.path.splitext(filename.lower())[1]
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.docx', '.doc']:
        return 'docx'
    return 'unknown'


@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化資料庫"""
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "name": "論文格式調整系統 API",
        "version": "3.0.0",
        "status": "running",
        "features": ["範本學習", "格式套用", "PDF 支援", "Word 支援"],
        "supported_formats": ["PDF", "Word (.docx)"]
    }


@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ========== 範本管理 API ==========

@app.post("/api/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = "我的範本",
    db: Session = Depends(get_db)
):
    """
    上傳格式範本文件並自動學習格式
    
    - **file**: PDF 或 Word 格式範本文件
    - **name**: 範本名稱
    """
    # 驗證文件類型
    file_type = get_file_type(file.filename)
    if file_type == 'unknown':
        raise HTTPException(
            status_code=400,
            detail="只支援 PDF 和 Word (.docx) 格式的文件"
        )
    
    # 生成唯一的文件名
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    saved_filename = f"template_{file_id}{ext}"
    file_path = os.path.join(TEMPLATE_DIR, saved_filename)
    
    # 儲存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件儲存失敗: {str(e)}"
        )
    
    # 解析文件並學習格式
    try:
        page_count = 0
        learned_rules = LearnedFormatRules()
        
        if file_type == 'pdf':
            with PDFParser(file_path) as parser:
                doc_structure = parser.parse()
                page_count = parser.get_page_count()
            
            if doc_structure:
                learned_rules = format_analyzer.learn_format_from_pdf(doc_structure)
        else:  # docx
            with DocxParser(file_path) as parser:
                doc_structure = parser.parse()
                page_count = parser.get_paragraph_count()  # 用段落數代替頁數
            
            if doc_structure:
                # 從 Word 文件學習格式
                learned_rules = learn_format_from_docx(doc_structure)
        
    except Exception as e:
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"格式學習失敗: {str(e)}"
        )
    
    # 取得文件大小
    file_size = os.path.getsize(file_path)
    
    # 創建資料庫記錄
    template = FormatTemplate(
        name=name,
        description=f"從 {file.filename} 學習的格式範本",
        original_path=file_path,
        learned_rules=learned_rules.to_dict(),
        page_count=page_count,
        file_size=file_size
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "file_type": file_type,
        "page_count": template.page_count,
        "learned_rules": learned_rules.to_dict(),
        "message": "範本上傳並學習成功"
    }


def learn_format_from_docx(doc_structure) -> LearnedFormatRules:
    """從 Word 文件結構學習格式"""
    rules = LearnedFormatRules()
    
    if doc_structure.sections:
        section = doc_structure.sections[0]
        rules.margin_top = section.margin_top
        rules.margin_bottom = section.margin_bottom
        rules.margin_left = section.margin_left
        rules.margin_right = section.margin_right
        rules.page_width = section.page_width
        rules.page_height = section.page_height
    
    # 收集字型資訊
    font_sizes = []
    font_names = []
    
    for block in doc_structure.text_blocks:
        if block.font_size > 0:
            font_sizes.append(block.font_size)
        if block.font_name:
            font_names.append(block.font_name)
    
    if font_names:
        from collections import Counter
        rules.main_font_name = Counter(font_names).most_common(1)[0][0]
    
    if font_sizes:
        import statistics
        rules.paragraph_font_size = statistics.mode(font_sizes)
        
        # 識別標題字型大小
        large_sizes = [s for s in font_sizes if s > 14]
        if large_sizes:
            sorted_sizes = sorted(set(large_sizes), reverse=True)
            rules.title_font_size = sorted_sizes[0]
            if len(sorted_sizes) > 1:
                rules.chapter_font_size = sorted_sizes[1]
    
    return rules


@app.get("/api/templates")
async def get_templates(db: Session = Depends(get_db)):
    """取得所有已學習的範本列表"""
    templates = db.query(FormatTemplate).all()
    
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "page_count": t.page_count,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in templates
        ]
    }


@app.get("/api/templates/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """取得範本詳情和學習到的格式規則"""
    template = db.query(FormatTemplate).filter(FormatTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="找不到該範本")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "page_count": template.page_count,
        "learned_rules": template.learned_rules,
        "created_at": template.created_at.isoformat() if template.created_at else None
    }


@app.delete("/api/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """刪除範本"""
    template = db.query(FormatTemplate).filter(FormatTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="找不到該範本")
    
    # 刪除文件
    if template.original_path and os.path.exists(template.original_path):
        os.remove(template.original_path)
    
    db.delete(template)
    db.commit()
    
    return {"message": "範本已刪除"}


# ========== 論文處理 API ==========

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上傳待處理的論文（PDF 或 Word）
    
    - **file**: PDF 或 Word 文件
    """
    # 驗證文件類型
    file_type = get_file_type(file.filename)
    if file_type == 'unknown':
        raise HTTPException(
            status_code=400,
            detail="只支援 PDF 和 Word (.docx) 格式的文件"
        )
    
    # 生成唯一的文件名
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    # 儲存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件儲存失敗: {str(e)}"
        )
    
    # 取得文件大小和頁數
    file_size = os.path.getsize(file_path)
    page_count = 0
    
    try:
        if file_type == 'pdf':
            with PDFParser(file_path) as parser:
                page_count = parser.get_page_count()
        else:  # docx
            with DocxParser(file_path) as parser:
                page_count = parser.get_paragraph_count()
    except Exception as e:
        print(f"讀取文件頁數失敗: {e}")
    
    # 創建資料庫記錄
    document = Document(
        filename=original_filename,
        original_path=file_path,
        status=DocumentStatus.UPLOADED.value,
        file_size=file_size,
        page_count=page_count
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": file_type,
        "file_size": document.file_size,
        "page_count": document.page_count,
        "status": document.status,
        "message": "文件上傳成功"
    }


@app.get("/api/documents")
async def get_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """取得所有文件列表"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    total = db.query(Document).count()
    
    return {
        "total": total,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "file_size": doc.file_size,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ]
    }


@app.get("/api/documents/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """取得單一文件資訊"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到該文件")
    
    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "format_template": document.format_template,
        "file_size": document.file_size,
        "page_count": document.page_count,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None
    }


def process_document_with_template(
    document_id: int, 
    template_id: int, 
    db: Session
):
    """使用學習的範本處理文件（支援 PDF 和 Word）"""
    document = db.query(Document).filter(Document.id == document_id).first()
    template = db.query(FormatTemplate).filter(FormatTemplate.id == template_id).first()
    
    if not document or not template:
        return
    
    try:
        # 更新狀態為處理中
        document.status = DocumentStatus.PROCESSING.value
        document.format_template = template.name
        db.commit()
        
        # 判斷文件類型
        file_type = get_file_type(document.filename)
        
        # 從儲存的規則建立
        learned_rules = LearnedFormatRules.from_dict(template.learned_rules)
        
        if file_type == 'pdf':
            # PDF 處理
            with PDFParser(document.original_path) as parser:
                doc_structure = parser.parse()
            
            if not doc_structure:
                raise Exception("無法解析 PDF 文件")
            
            elements = format_analyzer.extract_document_structure(doc_structure)
            format_template = format_analyzer.create_template_from_rules(
                template.name, 
                learned_rules
            )
            
            output_filename = f"formatted_{document_id}_{uuid.uuid4().hex[:8]}.pdf"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            generator = PDFGenerator(output_path, format_template)
            generator.generate(elements)
            
        else:  # Word
            # Word 處理 - 直接套用格式
            output_filename = f"formatted_{document_id}_{uuid.uuid4().hex[:8]}.docx"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            generator = DocxGenerator(output_path, learned_rules)
            generator.apply_format_to_document(document.original_path)
        
        # 更新資料庫
        document.processed_path = output_path
        document.status = DocumentStatus.COMPLETED.value
        db.commit()
        
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(e)
        db.commit()


@app.post("/api/documents/{document_id}/apply-template/{template_id}")
async def apply_template_to_document(
    document_id: int,
    template_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    套用學習的範本格式到論文
    
    - **document_id**: 論文文件 ID
    - **template_id**: 範本 ID
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    template = db.query(FormatTemplate).filter(FormatTemplate.id == template_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到該論文")
    
    if not template:
        raise HTTPException(status_code=404, detail="找不到該範本")
    
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail="文件正在處理中")
    
    # 在背景執行處理任務
    background_tasks.add_task(
        process_document_with_template,
        document_id,
        template_id,
        db
    )
    
    return {
        "message": "開始套用範本格式",
        "document_id": document_id,
        "template_id": template_id,
        "template_name": template.name
    }


@app.get("/api/documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """下載處理後的文件"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到該文件")
    
    if document.status != DocumentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"文件尚未處理完成，當前狀態: {document.status}"
        )
    
    if not document.processed_path or not os.path.exists(document.processed_path):
        raise HTTPException(status_code=404, detail="找不到處理後的文件")
    
    # 判斷輸出文件類型
    ext = os.path.splitext(document.processed_path)[1]
    media_type = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    # 生成下載文件名
    original_ext = os.path.splitext(document.filename)[1]
    download_filename = f"格式調整_{os.path.splitext(document.filename)[0]}{ext}"
    
    return FileResponse(
        path=document.processed_path,
        filename=download_filename,
        media_type=media_type
    )


@app.get("/api/formats")
async def get_available_formats():
    """取得可用的預設格式範本列表"""
    templates = format_analyzer.get_available_templates()
    return {"templates": templates}


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """刪除文件"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="找不到該文件")
    
    # 刪除實體文件
    try:
        if document.original_path and os.path.exists(document.original_path):
            os.remove(document.original_path)
        if document.processed_path and os.path.exists(document.processed_path):
            os.remove(document.processed_path)
    except Exception as e:
        print(f"刪除文件時發生錯誤: {e}")
    
    # 刪除資料庫記錄
    db.delete(document)
    db.commit()
    
    return {"message": "文件已刪除"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
