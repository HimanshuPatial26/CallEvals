"""The LLM extraction wire format — shared between extraction providers because
it's the same F2/F3/F4 target shape regardless of which model produces it, not
provider-specific logic. Source timestamps are never trusted from the model
directly — it points at a transcript segment *index*, and resolve_timestamp looks
up the real start time locally. LLMs are unreliable at reproducing numeric
timestamps verbatim; segment indices are a closed, checkable set the model can't
hallucinate its way around as easily, and it keeps the "click through to the
transcript" trust mechanism (PRD section 10) actually accurate.
"""

from pydantic import BaseModel

from app.schemas import ObjectionCategory, Speaker, TranscriptSegment


class WireNextStep(BaseModel):
    description: str
    owner: Speaker
    due: str | None = None
    source_segment_index: int | None = None
    confidence: float


class WireObjection(BaseModel):
    category: ObjectionCategory
    quote: str
    source_segment_index: int | None = None
    confidence: float


class WireExtractionResult(BaseModel):
    summary: str
    next_steps: list[WireNextStep]
    objections: list[WireObjection]


def format_transcript(transcript: list[TranscriptSegment]) -> str:
    lines = [
        f"[{i}] {seg.speaker.value} ({seg.start:.1f}s-{seg.end:.1f}s): {seg.text}"
        for i, seg in enumerate(transcript)
    ]
    return "\n".join(lines)


def resolve_timestamp(index: int | None, transcript: list[TranscriptSegment]) -> float | None:
    if index is None or index < 0 or index >= len(transcript):
        return None
    return transcript[index].start
