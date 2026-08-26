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


def test_mono_without_diarization_info_labels_unknown(deepgram_key, monkeypatch, tmp_path):
    """No 'speaker' field on the utterance (Deepgram couldn't diarize this
    audio) still degrades to unknown rather than guessing a role."""
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(monkeypatch, [{"start": 0.0, "end": 1.0, "channel": 0, "transcript": "hello"}])

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert segments[0].speaker == Speaker.UNKNOWN


def test_mono_uses_diarization_to_identify_rep_and_customer(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(
        monkeypatch,
        [
            {"start": 0.0, "end": 1.0, "transcript": "hi there, thanks for calling", "speaker": 0},
            {"start": 1.5, "end": 2.5, "transcript": "hi, I have a question", "speaker": 1},
            {"start": 3.0, "end": 4.0, "transcript": "sure, go ahead", "speaker": 0},
        ],
    )

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert segments[0].speaker == Speaker.REP  # speaker 0 talked first
    assert segments[1].speaker == Speaker.CUSTOMER
    assert segments[2].speaker == Speaker.REP


def test_mono_request_asks_for_diarization_not_multichannel(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": {"utterances": []}}

    def fake_post(url, *, params=None, headers=None, content=None, timeout=None):
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert captured["params"]["diarize"] == "true"
    assert "multichannel" not in captured["params"]


def test_empty_transcript_utterances_are_skipped(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(monkeypatch, [{"start": 0.0, "end": 1.0, "channel": 0, "transcript": "   "}])

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=False)

    assert segments == []


def test_dual_channel_falls_back_to_diarization_when_channels_not_separated(deepgram_key, monkeypatch, tmp_path):
    """Reproduces the real failure found in production: a 2-channel container
    where both speakers ended up mixed onto one channel, so Deepgram's
    multichannel processing only returns content on a single channel index.
    """
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(
        monkeypatch,
        [
            {"start": 0.0, "end": 1.0, "channel": 1, "transcript": "hello this is steven", "speaker": 1},
            {"start": 1.5, "end": 2.5, "channel": 1, "transcript": "yes speaking", "speaker": 0},
            {"start": 3.0, "end": 4.0, "channel": 1, "transcript": "okay great", "speaker": 1},
        ],
    )

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=True)

    assert segments[0].speaker == Speaker.REP  # speaker 1 talked first
    assert segments[1].speaker == Speaker.CUSTOMER  # speaker 0 is anyone-but-first
    assert segments[2].speaker == Speaker.REP  # speaker 1 again


def test_diarization_fallback_collapses_third_speaker_into_customer(deepgram_key, monkeypatch, tmp_path):
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(
        monkeypatch,
        [
            {"start": 0.0, "end": 1.0, "channel": 1, "transcript": "hi", "speaker": 2},
            {"start": 1.5, "end": 2.5, "channel": 1, "transcript": "hey", "speaker": 0},
            {"start": 3.0, "end": 4.0, "channel": 1, "transcript": "who's there", "speaker": 1},
        ],
    )

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=True)

    assert segments[0].speaker == Speaker.REP
    assert segments[1].speaker == Speaker.CUSTOMER
    assert segments[2].speaker == Speaker.CUSTOMER


def test_dual_channel_with_real_separation_ignores_diarization_fallback(deepgram_key, monkeypatch, tmp_path):
    """When both channels genuinely carry content, the channel-based mapping
    wins even though diarize=true is also requested and speaker fields exist.
    """
    from app.asr.deepgram_provider import DeepgramProvider

    _mock_response(
        monkeypatch,
        [
            {"start": 0.0, "end": 1.0, "channel": 0, "transcript": "hello there", "speaker": 0},
            {"start": 1.5, "end": 2.5, "channel": 1, "transcript": "too expensive", "speaker": 1},
        ],
    )

    audio_path = tmp_path / "call.wav"
    audio_path.write_bytes(b"fake-audio")

    segments = DeepgramProvider().transcribe(audio_path, dual_channel=True)

    assert segments[0].speaker == Speaker.REP
    assert segments[1].speaker == Speaker.CUSTOMER
