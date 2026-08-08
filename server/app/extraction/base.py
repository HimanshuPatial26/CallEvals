"""Extraction provider interface — turns a transcript into F2/F3/F4 (summary,
next steps, objections). This is where A1, the PRD's riskiest assumption, actually
gets tested; keep it swappable so the Phase 0 precision eval can run against a fake
implementation in tests without spending API calls.
"""

from abc import ABC, abstractmethod

from app.schemas import ExtractionResult, TranscriptSegment


class ExtractionProvider(ABC):
    @abstractmethod
    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        raise NotImplementedError
