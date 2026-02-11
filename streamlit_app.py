from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import streamlit as st

# Streamlit Cloud 可寫入空間建議放在 /tmp。
if "THESIS_APP_DATA_DIR" not in os.environ:
    os.environ["THESIS_APP_DATA_DIR"] = str(Path(tempfile.gettempdir()) / "thesis_formatter_data")

from app.core.config import settings, ensure_directories
from app.core.database import SessionLocal, init_db
from app.models.db_models import TemplateRecord
from app.models.schemas import GROUP_DESCRIPTIONS, GROUP_KEYS, GROUP_LABELS, REQUIRED_FONT_NAME, RuleSet
from app.services.job_service import JobService
from app.services.template_service import TemplateService


PAGE_NUMBER_FORMAT_LABELS = {
    "decimal": "阿拉伯數字（1, 2, 3）",
    "upperRoman": "大寫羅馬數字（I, II, III）",
    "lowerRoman": "小寫羅馬數字（i, ii, iii）",
    "none": "不指定頁碼格式",
}

ALIGNMENT_LABELS = {
    "left": "靠左對齊",
    "center": "置中對齊",
    "right": "靠右對齊",
    "justify": "左右對齊",
}

AI_PROVIDER_LABELS = {
    "auto": "自動（優先 OpenAI，其次 Gemini）",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "off": "關閉 AI（僅規則判斷）",
}

JOB_STATUS_LABELS = {
    "queued": "排隊中",
    "running": "處理中",
    "success": "完成",
    "failed": "失敗",
}


@dataclass
class UploadAdapter:
    filename: str
    file: BytesIO


def make_upload_adapter(name: str, data: bytes) -> UploadAdapter:
    return UploadAdapter(filename=name, file=BytesIO(data))


@st.cache_resource
def bootstrap_services() -> tuple[TemplateService, JobService]:
    ensure_directories()
    init_db()

    template_service = TemplateService()
    job_service = JobService()

    with SessionLocal() as session:
        default_template = session.query(TemplateRecord).filter(TemplateRecord.is_default.is_(True)).first()
        if not default_template:
            template_service.reset_default_template(session)

    return template_service, job_service


def fetch_templates(template_service: TemplateService) -> list[TemplateRecord]:
    with SessionLocal() as session:
        return template_service.list_templates(session)


def load_rules_for_template(template_service: TemplateService, template_id: str) -> RuleSet:
    with SessionLocal() as session:
        template = template_service.get_template(session, template_id)
        return template_service.get_rules(template)


def save_rules_to_template(template_service: TemplateService, template_id: str, rules: RuleSet) -> RuleSet:
    with SessionLocal() as session:
        template = template_service.get_template(session, template_id)
        updated = template_service.update_rules(session, template, rules)
        return template_service.get_rules(updated)


def _read_streamlit_secret(key: str) -> str:
    try:
        value = st.secrets.get(key, "")
    except Exception:
        return ""
    return str(value or "").strip()


def ensure_state_keys() -> None:
    secret_provider = _read_streamlit_secret("THESIS_AI_PROVIDER").lower()
    secret_openai_model = _read_streamlit_secret("OPENAI_MODEL")
    secret_gemini_model = _read_streamlit_secret("GEMINI_MODEL")

    st.session_state.setdefault("selected_template_id", None)
    st.session_state.setdefault("loaded_template_id", None)
    st.session_state.setdefault("rules_state", None)
    st.session_state.setdefault("last_job_result", None)
    st.session_state.setdefault("ai_provider", secret_provider or settings.ai_provider or "auto")
    # UI 不預填 API Key，避免金鑰在介面上成為預設值。
    st.session_state.setdefault("openai_api_key", "")
    st.session_state.setdefault("openai_model", secret_openai_model or settings.openai_model)
    st.session_state.setdefault("gemini_api_key", "")
    st.session_state.setdefault("gemini_model", secret_gemini_model or settings.gemini_model)
    if st.session_state["ai_provider"] not in {"auto", "openai", "gemini", "off"}:
        st.session_state["ai_provider"] = "auto"


def render_page_editor(rules_state: dict) -> None:
    st.subheader("頁面格式設定")
    st.caption("此區設定整份論文頁面尺寸、邊界、頁首/頁尾與頁碼格式。")
    page = rules_state["page"]

    col1, col2, col3 = st.columns(3)
    with col1:
        page["page_width_pt"] = st.number_input("紙張寬度 (pt)", min_value=300.0, max_value=1200.0, value=float(page["page_width_pt"]), step=1.0)
        page["margin_top_pt"] = st.number_input("上邊界 (pt)", min_value=0.0, max_value=300.0, value=float(page["margin_top_pt"]), step=0.5)
        page["margin_left_pt"] = st.number_input("左邊界 (pt)", min_value=0.0, max_value=300.0, value=float(page["margin_left_pt"]), step=0.5)
        page["header_distance_pt"] = st.number_input("頁首距離 (pt)", min_value=0.0, max_value=200.0, value=float(page["header_distance_pt"]), step=0.5)
    with col2:
        page["page_height_pt"] = st.number_input("紙張高度 (pt)", min_value=300.0, max_value=1800.0, value=float(page["page_height_pt"]), step=1.0)
        page["margin_bottom_pt"] = st.number_input("下邊界 (pt)", min_value=0.0, max_value=300.0, value=float(page["margin_bottom_pt"]), step=0.5)
        page["margin_right_pt"] = st.number_input("右邊界 (pt)", min_value=0.0, max_value=300.0, value=float(page["margin_right_pt"]), step=0.5)
        page["footer_distance_pt"] = st.number_input("頁尾距離 (pt)", min_value=0.0, max_value=200.0, value=float(page["footer_distance_pt"]), step=0.5)
    with col3:
        page["gutter_pt"] = st.number_input("裝訂邊界 (pt)", min_value=0.0, max_value=100.0, value=float(page["gutter_pt"]), step=0.5)
        page["page_number_start"] = int(st.number_input("頁碼起始值", min_value=1, max_value=999, value=int(page["page_number_start"]), step=1))
        page["page_number_format"] = st.selectbox(
            "頁碼格式",
            options=["decimal", "upperRoman", "lowerRoman", "none"],
            index=["decimal", "upperRoman", "lowerRoman", "none"].index(page["page_number_format"]),
            format_func=lambda v: PAGE_NUMBER_FORMAT_LABELS.get(v, v),
        )


def render_group_editor(rules_state: dict) -> None:
    st.subheader("段落群組格式設定")
    st.caption("依學校規範，本系統會強制所有群組字型為「標楷體」。")

    for group_key in GROUP_KEYS:
        group = rules_state["groups"][group_key]
        group["font_name"] = REQUIRED_FONT_NAME

        with st.expander(GROUP_LABELS[group_key], expanded=group_key in {"chapter_title", "section_title", "body"}):
            st.write(GROUP_DESCRIPTIONS[group_key])
            st.text_input("字型（固定）", value=REQUIRED_FONT_NAME, disabled=True, key=f"{group_key}_font_fixed")

            c1, c2, c3 = st.columns(3)
            with c1:
                group["font_size_pt"] = st.number_input(
                    "字級 (pt)",
                    min_value=8.0,
                    max_value=36.0,
                    value=float(group["font_size_pt"]),
                    step=0.5,
                    key=f"{group_key}_font_size",
                )
                group["line_spacing"] = st.number_input(
                    "行距倍率",
                    min_value=1.0,
                    max_value=3.0,
                    value=float(group["line_spacing"]),
                    step=0.05,
                    key=f"{group_key}_line_spacing",
                )
            with c2:
                group["space_before_pt"] = st.number_input(
                    "段前間距 (pt)",
                    min_value=-24.0,
                    max_value=120.0,
                    value=float(group["space_before_pt"]),
                    step=0.5,
                    key=f"{group_key}_space_before",
                )
                group["space_after_pt"] = st.number_input(
                    "段後間距 (pt)",
                    min_value=-24.0,
                    max_value=120.0,
                    value=float(group["space_after_pt"]),
                    step=0.5,
                    key=f"{group_key}_space_after",
                )
            with c3:
                group["first_line_indent_pt"] = st.number_input(
                    "首行縮排 (pt)",
                    min_value=-36.0,
                    max_value=120.0,
                    value=float(group["first_line_indent_pt"]),
                    step=0.5,
                    key=f"{group_key}_first_indent",
                )
                group["alignment"] = st.selectbox(
                    "對齊方式",
                    options=["left", "center", "right", "justify"],
                    index=["left", "center", "right", "justify"].index(group["alignment"]),
                    format_func=lambda v: ALIGNMENT_LABELS.get(v, v),
                    key=f"{group_key}_alignment",
                )

            b1, b2 = st.columns(2)
            with b1:
                group["bold"] = st.checkbox("粗體", value=bool(group["bold"]), key=f"{group_key}_bold")
            with b2:
                group["italic"] = st.checkbox("斜體", value=bool(group["italic"]), key=f"{group_key}_italic")


def build_ai_options_from_state() -> dict[str, str]:
    openai_key_manual = str(st.session_state.get("openai_api_key", "")).strip()
    gemini_key_manual = str(st.session_state.get("gemini_api_key", "")).strip()
    openai_key_secret = _read_streamlit_secret("OPENAI_API_KEY")
    gemini_key_secret = _read_streamlit_secret("GEMINI_API_KEY")

    return {
        "provider": str(st.session_state.get("ai_provider", "auto")),
        "openai_api_key": openai_key_manual or openai_key_secret,
        "openai_model": str(st.session_state.get("openai_model", settings.openai_model)).strip(),
        "gemini_api_key": gemini_key_manual or gemini_key_secret,
        "gemini_model": str(st.session_state.get("gemini_model", settings.gemini_model)).strip(),
    }


def render_ai_settings() -> None:
    st.header("步驟 3：AI 內容判斷設定")
    st.caption("可導入 OpenAI 或 Gemini，強化段落語義判斷（標題/內文/前置頁分類）。")
    st.caption("若欄位留白，系統會自動使用 Streamlit Secrets 內的 API Key。")

    provider_options = ["auto", "openai", "gemini", "off"]
    current_provider = str(st.session_state.get("ai_provider", "auto"))
    if current_provider not in provider_options:
        current_provider = "auto"

    st.selectbox(
        "AI 判斷模式",
        options=provider_options,
        index=provider_options.index(current_provider),
        format_func=lambda v: AI_PROVIDER_LABELS.get(v, v),
        key="ai_provider",
    )

    openai_col, gemini_col = st.columns(2)
    with openai_col:
        st.text_input("OpenAI API Key", type="password", key="openai_api_key", help="建議透過 Streamlit Secrets 或環境變數設定。")
        st.text_input("OpenAI 模型名稱", key="openai_model")
    with gemini_col:
        st.text_input("Gemini API Key", type="password", key="gemini_api_key", help="建議透過 Streamlit Secrets 或環境變數設定。")
        st.text_input("Gemini 模型名稱", key="gemini_model")


def run_streamlit_app() -> None:
    st.set_page_config(page_title="自動調整論文格式（Streamlit 雲端版）", page_icon="📘", layout="wide")

    template_service, job_service = bootstrap_services()
    ensure_state_keys()

    st.title("📘 自動調整論文格式（雲端分享版）")
    st.markdown(
        """
        本系統可上傳論文範本（DOCX）與目標論文（DOCX / PDF），
        以台灣論文常用規格進行格式統一，並輸出可編輯 DOCX 檔案。
        """
    )
    st.info("字型規則：依你指定的台灣規範，系統所有段落群組皆固定使用「標楷體」。")

    templates = fetch_templates(template_service)
    if not templates:
        st.error("目前沒有可用範本，請先重置預設範本。")
        if st.button("建立預設範本（AI-THESIS MODEL）"):
            with SessionLocal() as session:
                template_service.reset_default_template(session)
            st.success("已建立預設範本。")
            st.rerun()
        return

    st.header("步驟 1：範本管理")
    toolbar1, toolbar2, toolbar3 = st.columns([1, 1, 2])
    with toolbar1:
        if st.button("🔄 重新整理範本列表"):
            st.rerun()
    with toolbar2:
        if st.button("♻️ 重置為預設範本"):
            with SessionLocal() as session:
                template_service.reset_default_template(session)
            st.success("已重置為預設範本。")
            st.rerun()

    with st.form("upload_template_form"):
        st.subheader("上傳新 DOCX 範本")
        new_template_name = st.text_input("範本名稱（可空白）", placeholder="例如：系所格式 2026")
        new_template_file = st.file_uploader("選擇 DOCX 範本檔案", type=["docx"], key="new_template_file")
        upload_template_submit = st.form_submit_button("上傳並偵測範本規則")

    if upload_template_submit:
        if not new_template_file:
            st.error("請先選擇 DOCX 範本檔案。")
        else:
            try:
                data = new_template_file.getvalue()
                adapter = make_upload_adapter(new_template_file.name, data)
                with SessionLocal() as session:
                    template_service.create_template_from_upload(session, adapter, new_template_name)
                st.success("範本上傳與偵測完成。")
                st.rerun()
            except Exception as exc:
                st.error(f"範本上傳失敗：{exc}")

    options = {f"{item.name}（{'預設' if item.is_default else '自訂'}）": item.id for item in templates}
    labels = list(options.keys())

    default_index = 0
    if st.session_state["selected_template_id"]:
        for idx, label in enumerate(labels):
            if options[label] == st.session_state["selected_template_id"]:
                default_index = idx
                break

    selected_label = st.selectbox("目前套用範本", labels, index=default_index)
    selected_template_id = options[selected_label]
    st.session_state["selected_template_id"] = selected_template_id

    if st.session_state["loaded_template_id"] != selected_template_id:
        rules = load_rules_for_template(template_service, selected_template_id)
        st.session_state["rules_state"] = rules.model_dump(mode="json")
        st.session_state["loaded_template_id"] = selected_template_id

    rules_state = st.session_state["rules_state"]

    st.header("步驟 2：規則檢視與微調")
    render_page_editor(rules_state)
    render_group_editor(rules_state)

    if st.button("💾 儲存目前規則到範本", type="primary"):
        try:
            rules_model = RuleSet.model_validate(rules_state)
            saved_rules = save_rules_to_template(template_service, selected_template_id, rules_model)
            st.session_state["rules_state"] = saved_rules.model_dump(mode="json")
            st.success("規則已儲存。")
            st.rerun()
        except Exception as exc:
            st.error(f"儲存規則失敗：{exc}")

    with st.expander("查看偵測備註（繁體中文）"):
        notes = rules_state.get("detection_notes", [])
        if notes:
            for note in notes:
                st.write(f"- {note}")
        else:
            st.write("目前無偵測備註。")

    render_ai_settings()

    st.header("步驟 4：上傳目標論文並執行格式化")
    with st.form("run_job_form"):
        target_file = st.file_uploader("目標論文（DOCX 或 PDF）", type=["docx", "pdf"], key="target_file")
        run_job_submit = st.form_submit_button("開始格式化")

    if run_job_submit:
        if not target_file:
            st.error("請先上傳目標論文檔案。")
        else:
            try:
                content = target_file.getvalue()
                if len(content) > settings.max_upload_size_mb * 1024 * 1024:
                    st.error(f"目標檔案超過 {settings.max_upload_size_mb} MB 上限。")
                else:
                    with st.spinner("系統正在進行格式化，請稍候..."):
                        adapter = make_upload_adapter(target_file.name, content)
                        rules_model = RuleSet.model_validate(st.session_state["rules_state"])
                        ai_options = build_ai_options_from_state()

                        with SessionLocal() as session:
                            template = template_service.get_template(session, selected_template_id)
                            job = job_service.create_job(session, template, adapter, rules_override=rules_model)

                        job_service.process_job(job.id, ai_options=ai_options)

                        with SessionLocal() as session:
                            final_job = job_service.get_job(session, job.id)
                            st.session_state["last_job_result"] = {
                                "id": final_job.id,
                                "status": final_job.status,
                                "progress": final_job.progress,
                                "warning": final_job.warning_message,
                                "error": final_job.error_message,
                                "confidence": final_job.conversion_confidence,
                                "output_path": final_job.output_docx_path,
                                "target_filename": final_job.target_filename,
                            }

                    st.success("任務執行完成。")
            except Exception as exc:
                st.error(f"任務執行失敗：{exc}")

    st.header("步驟 5：結果下載")
    result = st.session_state.get("last_job_result")
    if not result:
        st.caption("尚未產生任務結果。")
    else:
        st.write(f"任務編號：`{result['id']}`")
        status_label = JOB_STATUS_LABELS.get(result["status"], result["status"])
        st.write(f"任務狀態：`{status_label}`，進度：`{result['progress']}%`")

        if result.get("confidence") is not None:
            st.write(f"PDF 轉換信心分數：`{result['confidence']:.3f}`")
        if result.get("warning"):
            st.warning(result["warning"])
        if result.get("error"):
            st.error(result["error"])

        if result["status"] == "success" and result.get("output_path"):
            output_path = Path(result["output_path"])
            if output_path.exists():
                data = output_path.read_bytes()
                download_name = f"格式化完成_{Path(result['target_filename']).stem}.docx"
                st.download_button(
                    label="⬇️ 下載格式化 DOCX 檔案",
                    data=data,
                    file_name=download_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            else:
                st.error("找不到輸出檔案，請重新執行任務。")

    st.divider()
    st.subheader("部署到 Streamlit Cloud（分享給同學）")
    st.markdown(
        """
        1. 將此專案推送到 GitHub（公開或可授權的私有倉庫）。  
        2. 到 [Streamlit Cloud](https://share.streamlit.io/) 建立新 App。  
        3. Main file path 設定為 `streamlit_app.py`。  
        4. 部署完成後，使用公開 URL 直接分享給同學。  
        """
    )


if __name__ == "__main__":
    run_streamlit_app()
