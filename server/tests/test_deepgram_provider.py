import httpx
import pytest

from app.config import settings
from app.schemas import Speaker


@pytest.fixture
def deepgram_key(monkeypatch):
    monkeypatch.setattr(settings, "deepgram_api_key", "test-key")


def _mock_response(monkeypatch, utterances):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": {"utterances": utterances}}

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "deepgram_api_key", "")
    from app.asr.deepgram_provider import DeepgramProvider

    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        DeepgramProvider()


def test_dual_channel_maps_channels_to_speakers(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(
        monkeypatch,
        [
            {"start": 0.0, "end": 1.0, "channel": 0, "transcript": "hello there"},
            {"start": 1.5, "end": 2.5, "channel": 1, "transcript": "too expensive"},
        ],
    )

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=True)

    assert segments[0].speaker == Speaker.REP
    assert segments[0].text == "hello there"
    assert segments[1].speaker == Speaker.CUSTOMER
    assert segments[1].text == "too expensive"


def test_mono_labels_everything_unknown(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(monkeypatch, [{"start": 0.0, "end": 1.0, "channel": 0, "transcript": "hello"}])

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert segments[0].speaker == Speaker.UNKNOWN


def test_empty_transcript_utterances_are_skipped(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(monkeypatch, [{"start": 0.0, "end": 1.0, "channel": 0, "transcript": "   "}])

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert segments == []
