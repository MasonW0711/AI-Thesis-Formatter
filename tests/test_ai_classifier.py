import httpx

from app.adapters.ai_classifier import AIProviderConfig, ParagraphAIClassifier


def _build_classifier(provider: str = "openai") -> ParagraphAIClassifier:
    return ParagraphAIClassifier(
        AIProviderConfig(
            provider=provider,
            openai_api_key="dummy-openai-key",
            openai_model="gpt-4o-mini",
            gemini_api_key="dummy-gemini-key",
            gemini_model="gemini-1.5-flash",
            timeout_sec=10.0,
            batch_size=10,
        )
    )


def test_ai_classifier_parses_openai_json(monkeypatch):
    classifier = _build_classifier(provider="openai")

    def _fake_openai(_system: str, _user: str) -> str:
        return '{"labels":[{"index":0,"group":"chapter_title"},{"index":1,"group":"body"}]}'

    monkeypatch.setattr(classifier, "_call_openai", _fake_openai)

    labels, notes = classifier.classify(
        [
            {"index": 0, "text": "第一章 緒論", "heuristic": "body", "style_name": "", "alignment": "center", "is_numbered": False},
            {"index": 1, "text": "這是內文段落", "heuristic": "body", "style_name": "", "alignment": "justify", "is_numbered": False},
        ]
    )

    assert labels == {0: "chapter_title", 1: "body"}
    assert any("OpenAI" in note for note in notes)


def test_ai_classifier_returns_empty_without_keys():
    classifier = ParagraphAIClassifier(
        AIProviderConfig(
            provider="auto",
            openai_api_key="",
            openai_model="gpt-4o-mini",
            gemini_api_key="",
            gemini_model="gemini-1.5-flash",
            timeout_sec=10.0,
            batch_size=10,
        )
    )

    labels, notes = classifier.classify(
        [{"index": 0, "text": "測試段落", "heuristic": "body", "style_name": "", "alignment": "left", "is_numbered": False}]
    )
    assert labels == {}
    assert notes == []


def test_ai_classifier_403_has_friendly_message(monkeypatch):
    classifier = _build_classifier(provider="openai")

    def _raise_403(_system: str, _user: str) -> str:
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(status_code=403, request=request)
        raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    monkeypatch.setattr(classifier, "_call_openai", _raise_403)

    labels, notes = classifier.classify(
        [{"index": 0, "text": "第一章", "heuristic": "chapter_title", "style_name": "", "alignment": "center", "is_numbered": False}]
    )

    assert labels == {}
    assert notes
    assert "HTTP 403" in notes[0]
    assert "權限" in notes[0] or "驗證" in notes[0]
