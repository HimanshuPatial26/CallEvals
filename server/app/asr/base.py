"""ASR provider interface.

Kept swappable on purpose: the PRD flags ASR provider as an open question (open
question #2 — dual-channel vs. diarization; open question #4 — when self-hosting
starts paying off). FasterWhisperProvider is the Phase 0 default because it's free
and needs no billing account, but nothing else in the pipeline should import it
directly — depend on this interface instead.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas import TranscriptSegment


class ASRProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, dual_channel: bool) -> list[TranscriptSegment]:
        """Return speaker-labeled, timestamped transcript segments in start-time order.

        When dual_channel is False, real diarization is out of scope for Phase 0 —
        implementations should label every segment Speaker.UNKNOWN rather than guess.
        """
        raise NotImplementedError
