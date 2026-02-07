# 論文格式調整系統

自動將您的論文調整為符合學校規定的格式，節省手動編排的時間與精力。

## 功能特色

- 📤 **PDF 上傳**：支援拖放上傳，輕鬆上傳論文 PDF 檔案
- 🔍 **智能分析**：自動識別論文結構（標題、段落、引用等）
- ✨ **格式調整**：根據學校規定的格式範本自動調整排版
- 📥 **一鍵下載**：處理完成後即可下載調整後的論文

## 系統架構

```
論文格式調整/
├── frontend/          # Next.js 前端應用
│   ├── app/
│   │   ├── page.tsx          # 首頁
│   │   ├── upload/page.tsx   # 上傳頁面
│   │   ├── documents/page.tsx # 文件列表
│   │   ├── layout.tsx        # 根佈局
│   │   └── globals.css       # 全域樣式
│   └── package.json
│
└── backend/           # FastAPI 後端服務
    ├── main.py               # API 入口
    ├── database.py           # 資料庫配置
    ├── models/
    │   └── document.py       # 資料模型
    └── services/
        ├── pdf_parser.py     # PDF 解析
        ├── format_analyzer.py # 格式分析
        └── pdf_generator.py  # PDF 生成
```

## 快速開始

### 1. 安裝後端依賴

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 啟動後端服務

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

後端 API 將在 http://localhost:8000 啟動

### 3. 安裝前端依賴

```bash
cd frontend
npm install
```

### 4. 啟動前端開發服務器

```bash
cd frontend
npm run dev
```

前端應用將在 http://localhost:3000 啟動

## API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/upload` | 上傳 PDF 文件 |
| GET | `/api/documents` | 取得文件列表 |
| GET | `/api/documents/{id}` | 取得單一文件狀態 |
| POST | `/api/documents/{id}/process` | 開始格式處理 |
| GET | `/api/documents/{id}/download` | 下載處理後文件 |
| GET | `/api/formats` | 取得可用格式範本 |
| DELETE | `/api/documents/{id}` | 刪除文件 |

## 技術棧

- **前端**：Next.js 14、React 18、TypeScript
- **後端**：Python、FastAPI、SQLAlchemy
- **PDF 處理**：PyMuPDF (fitz)、ReportLab
- **資料庫**：SQLite

---

> 📎 論文格式調整系統 — Spec v1 — 2026.02.07
