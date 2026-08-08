"""Selects the ASR provider from config. faster-whisper is the default so Phase
0 stays free-by-default; Deepgram is opt-in via ASR_PROVIDER=deepgram in .env.
"""

from app.asr.base import ASRProvider
from app.config import settings


def get_asr_provider() -> ASRProvider:
    if settings.asr_provider == "deepgram":
        from app.asr.deepgram_provider import DeepgramProvider

        return DeepgramProvider()

    from app.asr.faster_whisper_provider import FasterWhisperProvider

    return FasterWhisperProvider()
