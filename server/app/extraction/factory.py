"""Selects the extraction provider from config. Gemini is the default so
existing behavior/deployments are unaffected; Groq is opt-in via
EXTRACTION_PROVIDER=groq in .env — see README's "Groq extraction" section
for why you'd want to (Gemini's free tier caps at 20 requests/day; Groq's
free tier supports far more volume). Mirrors app/asr/factory.py.
"""

from app.config import settings
from app.extraction.base import ExtractionProvider


def get_extraction_provider() -> ExtractionProvider:
    if settings.extraction_provider == "groq":
        from app.extraction.groq_extractor import GroqExtractor

        return GroqExtractor()

    from app.extraction.gemini_extractor import GeminiExtractor

    return GeminiExtractor()
