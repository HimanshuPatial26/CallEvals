import pytest

from app.config import settings
from app.extraction.factory import get_extraction_provider


def test_defaults_to_gemini(monkeypatch):
    monkeypatch.setattr(settings, "extraction_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    from app.extraction.gemini_extractor import GeminiExtractor

    assert isinstance(get_extraction_provider(), GeminiExtractor)


def test_selects_groq_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "extraction_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    from app.extraction.groq_extractor import GroqExtractor

    assert isinstance(get_extraction_provider(), GroqExtractor)


def test_groq_without_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "extraction_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        get_extraction_provider()
