"""Selects the extraction provider from config. Gemini is the default so Phase 0
stays on the free tier with no GCP billing account; Groq is opt-in via
EXTRACTION_PROVIDER=groq in .env.
"""

from app.config import settings
from app.extraction.base import ExtractionProvider


def get_extraction_provider() -> ExtractionProvider:
    if settings.extraction_provider == "groq":
        from app.extraction.groq_extractor import GroqExtractor

        return GroqExtractor()

    from app.extraction.gemini_extractor import GeminiExtractor

    return GeminiExtractor()
