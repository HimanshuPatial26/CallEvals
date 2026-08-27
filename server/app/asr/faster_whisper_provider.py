"""Self-hosted ASR via faster-whisper (CTranslate2). Free — no API key, no billing
account, runs on CPU at Phase 0's call volume. Requires ffmpeg on PATH.

This is the provider the PRD's architecture diagram names ("ASR (Whisper)"), and
it's the same engine the PRD proposes moving to at scale (section 7) — so Phase 0
is already on the target long-term path instead of a throwaway spike.
"""

import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from app.asr.base import ASRProvider
from app.audio.channel_split import split_channels
from app.config import settings
from app.schemas import Speaker, TranscriptSegment

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def _transcribe_track(audio: np.ndarray, sample_rate: int, speaker: Speaker) -> list[TranscriptSegment]:
    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        sf.write(tmp.name, audio, sample_rate)
        segments, _info = model.transcribe(tmp.name, vad_filter=True)
        return [
            TranscriptSegment(speaker=speaker, start=seg.start, end=seg.end, text=seg.text.strip())
            for seg in segments
            if seg.text.strip()
        ]


class FasterWhisperProvider(ASRProvider):
    def transcribe(self, audio_path: Path, dual_channel: bool) -> tuple[list[TranscriptSegment], str]:
        if dual_channel:
            rep_audio, customer_audio, sample_rate = split_channels(audio_path)
            rep_segments = _transcribe_track(rep_audio, sample_rate, Speaker.REP)
            customer_segments = _transcribe_track(customer_audio, sample_rate, Speaker.CUSTOMER)
            merged = rep_segments + customer_segments
            source = "channel_split"
        else:
            audio, sample_rate = sf.read(str(audio_path), always_2d=False, dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            merged = _transcribe_track(audio, sample_rate, Speaker.UNKNOWN)
            source = "unknown"

        return sorted(merged, key=lambda s: s.start), source
