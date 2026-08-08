import pytest

from app.asr.factory import get_asr_provider
from app.asr.faster_whisper_provider import FasterWhisperProvider
from app.config import settings


def test_defaults_to_faster_whisper(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "faster_whisper")
    assert isinstance(get_asr_provider(), FasterWhisperProvider)


def test_selects_deepgram_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "deepgram")
    monkeypatch.setattr(settings, "deepgram_api_key", "test-key")
    from app.asr.deepgram_provider import DeepgramProvider

    assert isinstance(get_asr_provider(), DeepgramProvider)


def test_deepgram_without_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "deepgram")
    monkeypatch.setattr(settings, "deepgram_api_key", "")

    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        get_asr_provider()
