import os

import numpy as np

from app.asr import faster_whisper_provider
from app.schemas import Speaker


class _FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class _FakeModel:
    """Records the path it was asked to transcribe so the test can confirm the
    temp wav file actually exists and is readable at that point — the exact
    thing that broke on Windows with tempfile.NamedTemporaryFile (see the
    comment in faster_whisper_provider.py)."""

    def __init__(self):
        self.seen_path = None
        self.path_existed_and_had_content = False

    def transcribe(self, path, vad_filter=True):
        self.seen_path = path
        self.path_existed_and_had_content = os.path.exists(path) and os.path.getsize(path) > 0
        return [_FakeSegment(0.0, 1.0, "hello")], None


def test_transcribe_track_writes_a_real_readable_wav_file(monkeypatch):
    fake_model = _FakeModel()
    monkeypatch.setattr(faster_whisper_provider, "_get_model", lambda: fake_model)

    audio = np.zeros(1600, dtype="float32")
    segments = faster_whisper_provider._transcribe_track(audio, 16000, Speaker.REP)

    assert fake_model.path_existed_and_had_content
    assert segments[0].speaker == Speaker.REP
    assert segments[0].text == "hello"
    # the temp directory (and the wav inside it) is cleaned up once the
    # context manager exits, not left behind
    assert not os.path.exists(fake_model.seen_path)
