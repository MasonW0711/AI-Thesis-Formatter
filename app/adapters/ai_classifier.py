from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import GROUP_KEYS, GROUP_LABELS


_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass(frozen=True)
class AIProviderConfig:
    provider: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str
    timeout_sec: float
    batch_size: int


class ParagraphAIClassifier:
    """Use OpenAI/Gemini to classify paragraph semantic groups."""

    def __init__(self, config: AIProviderConfig) -> None:
        self.config = config

    @classmethod
    def from_settings(cls) -> "ParagraphAIClassifier":
        return cls(
            AIProviderConfig(
                provider=settings.ai_provider,
                openai_api_key=settings.openai_api_key,
                openai_model=settings.openai_model,
                gemini_api_key=settings.gemini_api_key,
                gemini_model=settings.gemini_model,
                timeout_sec=settings.ai_timeout_sec,
                batch_size=settings.ai_batch_size,
            )
        )

    @classmethod
    def from_overrides(cls, overrides: dict[str, Any] | None = None) -> "ParagraphAIClassifier":
        provider = settings.ai_provider
        openai_api_key = settings.openai_api_key
        openai_model = settings.openai_model
        gemini_api_key = settings.gemini_api_key
        gemini_model = settings.gemini_model
        timeout_sec = settings.ai_timeout_sec
        batch_size = settings.ai_batch_size

        if overrides:
            provider = str(overrides.get("provider", provider) or provider).strip().lower()
            openai_api_key = str(overrides.get("openai_api_key", openai_api_key) or "").strip()
            openai_model = str(overrides.get("openai_model", openai_model) or openai_model).strip()
            gemini_api_key = str(overrides.get("gemini_api_key", gemini_api_key) or "").strip()
            gemini_model = str(overrides.get("gemini_model", gemini_model) or gemini_model).strip()
            timeout_sec = float(overrides.get("timeout_sec", timeout_sec) or timeout_sec)
            batch_size = max(1, int(overrides.get("batch_size", batch_size) or batch_size))

        return cls(
            AIProviderConfig(
                provider=provider,
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                gemini_api_key=gemini_api_key,
                gemini_model=gemini_model,
                timeout_sec=timeout_sec,
                batch_size=batch_size,
            )
        )

    def classify(self, paragraphs: list[dict[str, Any]]) -> tuple[dict[int, str], list[str]]:
        if not paragraphs:
            return {}, []

        provider = self._resolve_provider()
        if not provider:
            return {}, [self._disabled_reason_note()]

        labels: dict[int, str] = {}
        notes: list[str] = []
        for batch in self._chunk(paragraphs, self.config.batch_size):
            system_prompt, user_prompt = self._build_prompt(batch)
            try:
                if provider == "openai":
                    raw_text = self._call_openai(system_prompt, user_prompt)
                else:
                    raw_text = self._call_gemini(system_prompt, user_prompt)

                batch_labels = self._collect_valid_labels(raw_text)
                labels.update(batch_labels)

                expected_indices = {int(item["index"]) for item in batch if isinstance(item.get("index"), int)}
                missing_indices = expected_indices - set(batch_labels.keys())
                if missing_indices:
                    retry_labels = self._retry_missing_labels(provider, batch, sorted(missing_indices))
                    labels.update(retry_labels)
                    missing_indices = expected_indices - set(labels.keys())
                    if missing_indices:
                        notes.append(f"AI 未完整回傳分類，{len(missing_indices)} 段改用規則判斷。")
            except Exception as exc:  # pragma: no cover - network defensive branch
                provider_name = self._provider_display(provider)
                reason = self._friendly_error_message(provider_name, exc)
                notes.append(f"AI 分類失敗，已回退規則判斷：{reason}")
                return {}, notes

        notes.append(f"已啟用 AI 語義判斷（{self._provider_display(provider)}）。")
        notes.append(f"AI 判讀完成 {len(labels)}/{len(paragraphs)} 段。")
        return labels, notes

    def _resolve_provider(self) -> str | None:
        provider = (self.config.provider or "auto").lower()
        if provider in {"off", "none", "disable", "disabled"}:
            return None

        if provider == "openai":
            return "openai" if self.config.openai_api_key else None
        if provider == "gemini":
            return "gemini" if self.config.gemini_api_key else None

        if self.config.openai_api_key:
            return "openai"
        if self.config.gemini_api_key:
            return "gemini"
        return None

    def _build_prompt(self, batch: list[dict[str, Any]]) -> tuple[str, str]:
        group_hint = "\n".join(f"- {key}: {GROUP_LABELS[key]}" for key in GROUP_KEYS)
        index_list = ", ".join(str(int(item["index"])) for item in batch if isinstance(item.get("index"), int))
        system_prompt = (
            "你是論文段落語義分類器。"
            "請依文字與排版線索，判斷每段應套用的格式群組。\n"
            "可用群組如下：\n"
            f"{group_hint}\n"
            f"你必須為以下每個 index 都回傳一筆分類，不可遺漏：{index_list}。\n"
            "如果不確定，請回傳 body。"
            "你只能回傳 JSON，格式必須是："
            '{"labels":[{"index":12,"group":"body"}]}。'
        )

        compact_rows = []
        for item in batch:
            compact_rows.append(
                {
                    "index": item["index"],
                    "text": item["text"][:240],
                    "prev_text": item.get("prev_text", "")[:120],
                    "next_text": item.get("next_text", "")[:120],
                    "heuristic": item.get("heuristic", "body"),
                    "style_name": item.get("style_name", ""),
                    "alignment": item.get("alignment", ""),
                    "is_numbered": bool(item.get("is_numbered", False)),
                }
            )

        user_prompt = "請分類以下段落：\n" + json.dumps(compact_rows, ensure_ascii=False)
        return system_prompt, user_prompt

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.openai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=self.config.timeout_sec) as client:
            response = client.post(_OPENAI_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenAI 沒有回傳可用內容。")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_items = [x.get("text", "") for x in content if isinstance(x, dict)]
            return "\n".join(item for item in text_items if item)
        raise ValueError("OpenAI 回應格式無法解析。")

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.gemini_api_key:
            raise ValueError("Gemini API Key 未設定。")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\n{user_prompt}",
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
            },
        }
        url = _GEMINI_URL.format(model=self.config.gemini_model)
        with httpx.Client(timeout=self.config.timeout_sec) as client:
            response = client.post(url, params={"key": self.config.gemini_api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini 沒有回傳可用內容。")
        parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
        text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text:
            raise ValueError("Gemini 回應內容為空。")
        return text

    def _parse_labels(self, text: str) -> list[dict[str, Any]]:
        payload = self._extract_json_payload(text)

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            labels = payload.get("labels")
            if isinstance(labels, list):
                return [item for item in labels if isinstance(item, dict)]
        return []

    def _collect_valid_labels(self, raw_text: str) -> dict[int, str]:
        output: dict[int, str] = {}
        for item in self._parse_labels(raw_text):
            idx = item.get("index")
            group = item.get("group")
            if isinstance(idx, int) and group in GROUP_KEYS:
                output[idx] = group
        return output

    def _retry_missing_labels(self, provider: str, batch: list[dict[str, Any]], missing_indices: list[int]) -> dict[int, str]:
        if not missing_indices:
            return {}

        target_set = set(missing_indices)
        missing_rows = [item for item in batch if int(item["index"]) in target_set and isinstance(item.get("index"), int)]
        if not missing_rows:
            return {}

        system_prompt, user_prompt = self._build_prompt(missing_rows)
        if provider == "openai":
            raw_text = self._call_openai(system_prompt, user_prompt)
        else:
            raw_text = self._call_gemini(system_prompt, user_prompt)

        return self._collect_valid_labels(raw_text)

    @staticmethod
    def _extract_json_payload(text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = re.sub(r"^json\s*", "", stripped, flags=re.IGNORECASE).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, stripped)
            if not match:
                continue
            candidate = match.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        raise ValueError("AI 回覆不是有效 JSON。")

    @staticmethod
    def _friendly_error_message(provider_name: str, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status in {401, 403}:
                return (
                    f"{provider_name} 驗證或權限失敗（HTTP {status}）。"
                    "請確認 API Key 是否有效、模型是否有權限、帳號計費是否啟用。"
                )
            if status == 429:
                return f"{provider_name} 已達速率或額度限制（HTTP 429），請稍後再試。"
            if status >= 500:
                return f"{provider_name} 服務暫時異常（HTTP {status}），請稍後重試。"
            return f"{provider_name} API 呼叫失敗（HTTP {status}）。"

        if isinstance(exc, httpx.TimeoutException):
            return f"{provider_name} 請求逾時，請確認網路或調整模型後重試。"
        if isinstance(exc, httpx.HTTPError):
            return f"{provider_name} 網路連線失敗，請確認網路與憑證設定。"

        return str(exc)

    def _disabled_reason_note(self) -> str:
        provider = (self.config.provider or "auto").lower()
        if provider in {"off", "none", "disable", "disabled"}:
            return "AI 判斷已關閉，使用規則判斷。"
        if provider == "openai":
            return "OpenAI API Key 未提供，使用規則判斷。"
        if provider == "gemini":
            return "Gemini API Key 未提供，使用規則判斷。"
        return "未設定可用 AI API Key，使用規則判斷。"

    @staticmethod
    def _chunk(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    @staticmethod
    def _provider_display(provider: str) -> str:
        if provider == "openai":
            return "OpenAI"
        if provider == "gemini":
            return "Gemini"
        return provider
