"""Splitting a dual-channel recording into two mono tracks.

PRD section 5 (F1 design decision): prefer dual-channel recordings, where the dialer
already separates rep and customer onto separate tracks. Splitting channels gives
perfect speaker separation for free and avoids diarization entirely. Real diarization
for mono audio is a Phase 1 add (see app/asr/base.py) — deliberately not built here.
"""

from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings


class NotDualChannelError(ValueError):
    pass


def split_channels(audio_path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (rep_channel, customer_channel, sample_rate) as mono float32 arrays.

    Which physical channel is the rep track is a dialer/recorder export
    convention, not something the audio format tells you — settings.rep_channel_index
    (REP_CHANNEL_INDEX in .env) picks it, defaulting to channel 0. Confirm the
    convention with each brokerage's dialer during discovery (PRD open question #2).
    """
    data, sample_rate = sf.read(str(audio_path), always_2d=True, dtype="float32")
    if data.shape[1] < 2:
        raise NotDualChannelError(
            f"{audio_path} has {data.shape[1]} channel(s); dual-channel split needs 2"
        )
    rep_index = settings.rep_channel_index
    customer_index = 1 - rep_index
    return data[:, rep_index], data[:, customer_index], sample_rate


def is_dual_channel(audio_path: Path) -> bool:
    info = sf.info(str(audio_path))
    return info.channels >= 2
