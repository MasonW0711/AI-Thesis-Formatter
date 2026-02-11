# 自動調整論文格式（Streamlit Cloud + 單一 Python）

本專案已支援直接部署到 **Streamlit Cloud**，可分享連結給同學使用。

## 核心規範

- 預設範本：`defaults/AI-THESIS MODEL.docx`
- 目標檔案：`DOCX`、`PDF`
- PDF 流程：`PDF -> 中介 DOCX -> 套用格式 -> 輸出 DOCX`
- **字型強制規則：所有段落群組一律使用「標楷體」**（符合你指定的台灣論文規範）
- 所有格式說明與介面文案皆為繁體中文
- 可選擇導入 **OpenAI / Gemini** 強化段落語義判斷（標題、內文、前置頁）

## 主要檔案

```text
streamlit_app.py                 # Streamlit Cloud 入口
app/
  engines/template_detector.py   # 範本規則偵測
  engines/format_applier.py      # 格式套用（含 AI 語義分類 + 索引頁欄位）
  adapters/ai_classifier.py      # OpenAI / Gemini 段落分類整合
  adapters/pdf_to_docx.py        # PDF 轉中介 DOCX
  services/template_service.py   # 範本管理
  services/job_service.py        # 任務處理
  models/schemas.py              # 規則模型（含標楷體強制）
defaults/AI-THESIS MODEL.docx
scripts/build_exe.ps1            # 本地 EXE 打包
```

## 本機啟動（Streamlit 版）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 部署到 Streamlit Cloud（分享同學）

1. 將專案推送到 GitHub。
2. 進入 https://share.streamlit.io/ 後建立新 App。
3. Repository 指向此專案，Main file path 設 `streamlit_app.py`。
4. 部署完成後，取得公開 URL，直接分享給同學。

## OpenAI / Gemini API Key 外接方式

### 方式 A：Streamlit Cloud Secrets（建議）

在 Streamlit Cloud 的 App Settings -> Secrets 加入：

```toml
OPENAI_API_KEY = "你的_openai_api_key"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_API_KEY = "你的_gemini_api_key"
GEMINI_MODEL = "gemini-1.5-flash"
THESIS_AI_PROVIDER = "auto" # auto/openai/gemini/off
```

### 方式 B：本機環境變數

```powershell
$env:OPENAI_API_KEY="你的_openai_api_key"
$env:GEMINI_API_KEY="你的_gemini_api_key"
$env:THESIS_AI_PROVIDER="auto"
streamlit run streamlit_app.py
```

### UI 內切換

- Streamlit 頁面「步驟 3：AI 內容判斷設定」可切換 `auto / OpenAI / Gemini / 關閉 AI`
- 可在 UI 臨時輸入 API Key（遮罩欄位）與模型名稱
- 若未提供可用 API Key，系統會自動回退到規則分類，不會中斷任務

## 測試

```powershell
pytest -q
```

## 可選：本地 EXE 打包

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

輸出資料夾：`dist/ThesisFormatter/`

> 註：`requirements.txt` 已以 Streamlit Cloud 部署為主；EXE 打包所需 `PyInstaller` 由 `build_exe.ps1` 自動安裝。
