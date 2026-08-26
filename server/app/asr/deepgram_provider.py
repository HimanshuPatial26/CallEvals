"""Hosted ASR via Deepgram's prerecorded API. Opt-in (ASR_PROVIDER=deepgram in
.env) — faster-whisper stays the default so Phase 0 stays $0 by default.

Two things Deepgram gives for free that the self-hosted path doesn't:
- `multichannel=true` transcribes each channel in one call, so dual-channel
  calls skip the local soundfile split + two separate whisper passes.
- Real diarization is available via `diarize=true`.

Diarization is requested on every call now and used whenever channel-based
separation isn't available or didn't actually happen — two cases, one
mechanism (see _segments_from_diarization):

1. Genuinely mono calls (dual_channel is False here iff
   app.audio.channel_split.is_dual_channel found one channel in the
   container). faster-whisper still can't do this (no diarization model
   wired into that path — see faster_whisper_provider.py), so this only
   applies when ASR_PROVIDER=deepgram.
2. A real failure mode found in production: a file can be a 2-channel
   container (dual_channel=True) without the two speakers actually being on
   separate channels — e.g. a recorder that mixes both parties onto one
   track and leaves the other silent. `multichannel=true` can't split audio
   that was never separated in the first place; when that happens, only one
   channel comes back with real content.

Either way it's a heuristic (first speaker to talk = rep), not a guarantee —
see the docstring below for its failure modes. Worth surfacing to a manager
as lower-confidence than real channel separation, not presented as equally
certain.

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


def _channel_speaker_map() -> dict[int, Speaker]:
    """Which physical channel is the rep track — settings.rep_channel_index
    (REP_CHANNEL_INDEX in .env), same dialer/recorder convention
    app/audio/channel_split.py uses, kept in sync so both ASR paths agree.
    Read live rather than cached at import time so a settings change takes
    effect without re-importing this module.
    """
    rep_index = settings.rep_channel_index
    return {rep_index: Speaker.REP, 1 - rep_index: Speaker.CUSTOMER}


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
            # Requested unconditionally — free to ask for, and it's the only
            # signal available for a genuinely mono call, plus the fallback for
            # a dual-channel container that didn't actually separate. See the
            # module docstring for both cases.
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
        channel_speaker = _channel_speaker_map()
        return [
            TranscriptSegment(
                speaker=channel_speaker.get(u.get("channel", 0), Speaker.UNKNOWN),
                start=u["start"],
                end=u["end"],
                text=u["transcript"].strip(),
            )
            for u in utterances
        ]

    def _segments_from_diarization(self, utterances: list[dict]) -> list[TranscriptSegment]:
        """Used for genuinely mono calls, and as a fallback when a 2-channel
        file didn't actually separate the speakers.

        Heuristic: the first distinct diarized speaker to talk is labeled the
        rep, every other speaker ID is labeled the customer (multi-party calls
        beyond two voices collapse into "customer" — Phase 0 only models two
        roles). This is right when the rep opens the call, which is the norm
        for outbound sales calls, and wrong when the customer calls in first
        or the call opens with hold music / an IVR segment that gets diarized
        as its own "speaker." Deepgram's diarization confidence is also
        noticeably lower than channel-based separation — expect occasional
        misattributed short turns ("okay", "yeah").
        """
        first_speaker_id: int | None = None
        segments = []
        for u in utterances:
            speaker_id = u.get("speaker")
            if speaker_id is None:
                speaker = Speaker.UNKNOWN
            else:
                if first_speaker_id is None:
                    first_speaker_id = speaker_id
                speaker = Speaker.REP if speaker_id == first_speaker_id else Speaker.CUSTOMER
            segments.append(
                TranscriptSegment(speaker=speaker, start=u["start"], end=u["end"], text=u["transcript"].strip())
            )
        return segments
