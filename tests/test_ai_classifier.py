from app.adapters.ai_classifier import AIProviderConfig, ParagraphAIClassifier


def test_ai_classifier_parses_openai_json(monkeypatch):
    classifier = ParagraphAIClassifier(
        AIProviderConfig(
            provider="openai",
            openai_api_key="dummy-key",
            openai_model="gpt-4o-mini",
            gemini_api_key="",
            gemini_model="gemini-1.5-flash",
            timeout_sec=10.0,
            batch_size=10,
        )
    )

    def _fake_openai(_system: str, _user: str) -> str:
        return '{"labels":[{"index":0,"group":"chapter_title"},{"index":1,"group":"body"}]}'

    monkeypatch.setattr(classifier, "_call_openai", _fake_openai)

    labels, notes = classifier.classify(
        [
            {"index": 0, "text": "緒論", "heuristic": "body", "style_name": "", "alignment": "center", "is_numbered": False},
            {"index": 1, "text": "這是內文", "heuristic": "body", "style_name": "", "alignment": "justify", "is_numbered": False},
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
