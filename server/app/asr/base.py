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
    def transcribe(self, audio_path: Path, dual_channel: bool) -> tuple[list[TranscriptSegment], str]:
        """Return (speaker-labeled timestamped transcript segments in start-time
        order, how speakers were actually identified).

        The second element is one of "channel_split" (hard separation from
        distinct audio channels — as certain as this pipeline gets),
        "diarization" (voice-clustering heuristic — first speaker to talk is
        assumed to be the rep; can be wrong, see app/asr/deepgram_provider.py),
        or "unknown" (every segment is Speaker.UNKNOWN — no real diarization
        available for this path). This is real, reportable ground truth for
        why a transcript's speaker labels deserve more or less trust, not
        something to reconstruct after the fact from dual_channel alone — a
        dual-channel container that didn't actually separate still ends up on
        the "diarization" heuristic, same as a mono call.

        When neither channel separation nor diarization is available, label
        every segment Speaker.UNKNOWN rather than guess.
        """
        raise NotImplementedError
