"""Hosted ASR via Deepgram's prerecorded API. Opt-in (ASR_PROVIDER=deepgram in
.env) — faster-whisper stays the default so Phase 0 stays $0 by default.

Two things Deepgram gives for free that the self-hosted path doesn't:
- `multichannel=true` transcribes each channel in one call, so dual-channel
  calls skip the local soundfile split + two separate whisper passes.
- Real diarization is available via `diarize=true` for mono calls, which would
  close the gap the PRD's F1 design decision explicitly punts to Phase 1 — but
  that's a scope decision, not just a technical one, so it's deliberately NOT
  turned on here. Mono calls are transcribed plain and labeled Speaker.UNKNOWN,
  same as the faster-whisper path, so switching providers doesn't silently
  change what Phase 0 promises.

Not free forever: unlike faster-whisper this bills per minute after the
account's free credit runs out (see PRD section 7 for the self-host breakeven
this was always going to hit at scale).
"""

import mimetypes
from pathlib import Path

import httpx

from app.asr.base import ASRProvider
from app.config import settings
from app.schemas import Speaker, TranscriptSegment

_API_URL = "https://api.deepgram.com/v1/listen"

# Dual-channel convention: channel 0 is the rep track, channel 1 is the
# customer track. Same assumption app/audio/channel_split.py documents —
# confirm it against each dialer's actual export during discovery.
_CHANNEL_SPEAKER = {0: Speaker.REP, 1: Speaker.CUSTOMER}


class DeepgramProvider(ASRProvider):
    def __init__(self) -> None:
        if not settings.deepgram_api_key:
            raise RuntimeError(
                "ASR_PROVIDER=deepgram but DEEPGRAM_API_KEY is not set. Get a free-credit "
                "key at https://console.deepgram.com and put it in server/.env."
            )

    def transcribe(self, audio_path: Path, dual_channel: bool) -> list[TranscriptSegment]:
        params = {
            "model": settings.deepgram_model,
            "smart_format": "true",
            "punctuate": "true",
            "utterances": "true",
        }
        if dual_channel:
            params["multichannel"] = "true"

        content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/wav"
        response = httpx.post(
            _API_URL,
            params=params,
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": content_type,
            },
            content=audio_path.read_bytes(),
            timeout=120.0,
        )
        response.raise_for_status()
        utterances = response.json()["results"]["utterances"]

        segments = [
            TranscriptSegment(
                speaker=_CHANNEL_SPEAKER.get(u.get("channel", 0), Speaker.UNKNOWN) if dual_channel else Speaker.UNKNOWN,
                start=u["start"],
                end=u["end"],
                text=u["transcript"].strip(),
            )
            for u in utterances
            if u["transcript"].strip()
        ]
        return sorted(segments, key=lambda s: s.start)
