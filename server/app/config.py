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

    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"

    data_dir: Path = Path("./data")

    cors_allow_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
