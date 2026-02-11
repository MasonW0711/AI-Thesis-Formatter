# 自動調整論文格式 v1（Single Python Web）

本專案已重建為單一 Python 應用（FastAPI + Jinja2），不再依賴 Next.js。

- 預設範本：`defaults/AI-THESIS MODEL.docx`
- 支援目標檔：`DOCX`、`PDF`
- PDF 目標流程：`PDF -> 中介 DOCX -> 套用規則 -> 輸出 DOCX`
- 輸出位置：`data/outputs/`

## 專案結構

```text
app/
  api/
  adapters/
  core/
  engines/
  models/
  services/
  ui/
    templates/
    static/
defaults/
  AI-THESIS MODEL.docx
scripts/
  build_exe.ps1
tests/
launcher.py
requirements.txt
```

> 舊架構已改為 `_legacy_frontend/`、`_legacy_backend/`，不再參與執行。

## 開發啟動

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python launcher.py
```

預設網址：`http://127.0.0.1:8765`

## 功能流程

1. 重置或上傳 DOCX 範本（自動偵測規則）
2. 在 UI 調整規則（頁面 + 段落群組）
3. 上傳目標檔（DOCX/PDF）建立任務
4. 輪詢任務狀態並下載格式化後 DOCX

## Public APIs

- `POST /api/templates/default/reset`
- `POST /api/templates/upload`
- `GET /api/templates`
- `GET /api/templates/{id}/rules`
- `PATCH /api/templates/{id}/rules`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download`

## 測試

```powershell
pytest -q
```

## 打包 EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

輸出資料夾：`dist/ThesisFormatter/`
