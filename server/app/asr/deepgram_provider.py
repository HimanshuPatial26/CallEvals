"""Hosted ASR via Deepgram's prerecorded API. Opt-in (ASR_PROVIDER=deepgram in
.env) — faster-whisper stays the default so Phase 0 stays $0 by default.

Two things Deepgram gives for free that the self-hosted path doesn't:
- `multichannel=true` transcribes each channel in one call, so dual-channel
  calls skip the local soundfile split + two separate whisper passes.
- Real diarization is available via `diarize=true` and is always requested —
  used directly to label speakers on mono calls, and as a fallback for
  dual-channel calls where the channels didn't actually separate (see below).
  This reverses the original Phase 0 plan to punt diarization to Phase 1 —
  a deliberate, explicit call, not a silent scope change, made once real
  testing showed most calls in practice are mono. faster-whisper has no
  equivalent: Whisper itself has no diarization, so mono calls through that
  provider still come back Speaker.UNKNOWN.

Channel-based separation still wins whenever it's actually available — it's
free (channels are a container property, not a model call) and more
reliable than diarization (see _segments_from_diarization for why). Real
failure mode found in production: a file can be a 2-channel container
without the two speakers actually being on separate channels — e.g. a
recorder that mixes both parties onto one track and leaves the other
silent. `multichannel=true` can't split audio that was never separated in
the first place; when that happens, only one channel comes back with real
content, and we fall back to diarization the same way mono calls use it.

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
            "diarize": "true",
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
        utterances = [u for u in response.json()["results"]["utterances"] if u["transcript"].strip()]

        if dual_channel and len({u.get("channel", 0) for u in utterances}) >= 2:
            segments = self._segments_from_channels(utterances)
        else:
            segments = self._segments_from_diarization(utterances)

        return sorted(segments, key=lambda s: s.start)

    def _segments_from_channels(self, utterances: list[dict]) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                speaker=_CHANNEL_SPEAKER.get(u.get("channel", 0), Speaker.UNKNOWN),
                start=u["start"],
                end=u["end"],
                text=u["transcript"].strip(),
            )
            for u in utterances
        ]

    def _segments_from_diarization(self, utterances: list[dict]) -> list[TranscriptSegment]:
        """Used directly for mono calls, and as a fallback when a 2-channel
        file didn't actually separate the speakers.

        Heuristic: the diarized speaker with the most total transcript length
        across the call is labeled the rep, every other speaker ID is labeled
        the customer (multi-party calls beyond two voices collapse into
        "customer" — Phase 0 only models two roles).

        NOT "whoever talks first" — that was the original heuristic here and
        it was backwards in practice. In a real phone call, whoever answers
        speaks first (a bare "hello"), before the caller says anything; on an
        outbound call that means the *customer* is almost always the first
        voice, not the rep. Total talk time doesn't have that problem: reps
        pitch, explain, and walk customers through steps, so they consistently
        talk more than a customer mostly giving short replies ("yes", "okay").
        Still a heuristic, not a guarantee — wrong if the customer is
        unusually talkative (a long complaint, a lot of questions) or the call
        is short enough that talk time alone can't distinguish the two sides.
        Deepgram's diarization confidence is also noticeably lower than
        channel-based separation in practice — expect occasional misattributed
        short turns even when the rep/customer split itself is correct.
        """
        text_length_by_speaker: dict[int, int] = {}
        for u in utterances:
            speaker_id = u.get("speaker")
            if speaker_id is not None:
                text_length_by_speaker[speaker_id] = text_length_by_speaker.get(speaker_id, 0) + len(u["transcript"])
        rep_speaker_id = max(text_length_by_speaker, key=text_length_by_speaker.get, default=None)

        segments = []
        for u in utterances:
            speaker_id = u.get("speaker")
            if speaker_id is None:
                speaker = Speaker.UNKNOWN
            else:
                speaker = Speaker.REP if speaker_id == rep_speaker_id else Speaker.CUSTOMER
            segments.append(
                TranscriptSegment(speaker=speaker, start=u["start"], end=u["end"], text=u["transcript"].strip())
            )
        return segments
