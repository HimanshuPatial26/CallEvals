from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    extraction_provider: str = "gemini"  # "gemini" | "groq"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    asr_provider: str = "faster_whisper"  # "faster_whisper" | "deepgram"

    # Which physical channel of a dual-channel recording is the rep. This is a
    # dialer/recorder export convention — nothing in the audio file itself says
    # which channel is which — so it's configurable rather than assumed. Affects
    # both app/audio/channel_split.py (faster-whisper path) and
    # app/asr/deepgram_provider.py (Deepgram path) identically.
    rep_channel_index: int = 0  # 0 | 1

    # Diarization (used when channel separation isn't available — a mono call, or
    # a dual-channel container that didn't actually separate) has no channel to
    # key off of, so it falls back to a different, separate assumption: which
    # party's voice is clustered first. This is independent of rep_channel_index
    # and only applies on that fallback path — see app/asr/deepgram_provider.py.
    first_diarized_speaker_is_rep: bool = True

    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"

    data_dir: Path = Path("./data")

    cors_allow_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
