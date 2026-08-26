"""Deterministic, rule-based signals derived from a completed transcript + extraction.

Nothing here calls an LLM and nothing here is fabricated — every number is computed
from the real transcript timing/text and the real extraction result. Two things are
worth being explicit about because they're heuristics, not ground truth:

- Sentiment is a small lexicon scored per time bucket, not a trained model. PRD
  section 5 cut sentiment analysis as low-precision; it's kept here as unscored
  context only (never feeds a flag or the composite score), same framing the
  product itself uses.
- Behavior flags are threshold rules, not ML classification, by design — the whole
  point of PRD section 5's "behavior-level flags instead of a single score" is that
  a manager can see exactly why something fired and adjust the rule in Settings
  (RubricSettings.flags / weights) rather than trust an opaque number.
"""

import re

from app.schemas import BehaviorFlags, ConversationShape, ExtractionResult, RubricSettings, Speaker, TranscriptSegment

_POSITIVE_WORDS = {
    "great", "good", "perfect", "love", "like", "yes", "agree", "sounds good", "helpful",
    "interested", "works", "happy", "excited", "sure", "definitely", "appreciate", "thanks",
    "thank you", "let's do it", "moving ahead", "deciding factor", "better",
}
_NEGATIVE_WORDS = {
    "expensive", "too much", "too expensive", "not looking", "not really", "hesitant",
    "no", "cancel", "another agency", "elsewhere", "concerned", "worried", "over my budget",
    "above budget", "not buying", "not sure", "issue", "problem", "disappointed", "delay",
}
_DISCLOSURE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [r"this call (is|may be) recorded", r"recording this call", r"for quality (and|&) training"]
]
_DISCOUNT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [r"\bdiscount\b", r"lower (the )?price", r"reduce the price", r"knock off"]
]
_QUESTION_RE = re.compile(r"\?")

_SENTIMENT_BUCKETS = 12


def compute_duration(transcript: list[TranscriptSegment]) -> float:
    return max((seg.end for seg in transcript), default=0.0)


def _word_count(text: str) -> int:
    return len(text.split())


def _score_text(text: str) -> int:
    lowered = text.lower()
    score = 0
    for phrase in _POSITIVE_WORDS:
        if phrase in lowered:
            score += 1
    for phrase in _NEGATIVE_WORDS:
        if phrase in lowered:
            score -= 1
    return score


def _sentiment_label(curve: list[float]) -> str:
    if not curve:
        return "insufficient data"
    first_half = curve[: len(curve) // 2] or curve
    second_half = curve[len(curve) // 2 :] or curve
    start, end = sum(first_half) / len(first_half), sum(second_half) / len(second_half)
    if end - start > 0.25:
        return "recovered"
    if start - end > 0.25:
        return "cooled"
    if end > 0.2:
        return "positive throughout"
    if end < -0.2:
        return "negative throughout"
    if max(curve) - min(curve) < 0.15:
        return "flat"
    return "mixed"


def compute_conversation_shape(transcript: list[TranscriptSegment]) -> ConversationShape:
    duration = compute_duration(transcript)
    rep_segs = [s for s in transcript if s.speaker == Speaker.REP]
    customer_segs = [s for s in transcript if s.speaker == Speaker.CUSTOMER]
    known_segs = rep_segs + customer_segs

    rep_time = sum(s.end - s.start for s in rep_segs)
    known_time = sum(s.end - s.start for s in known_segs)
    talk_ratio_rep = (rep_time / known_time) if known_time > 0 else 0.0

    questions_asked_rep = sum(1 for s in rep_segs if _QUESTION_RE.search(s.text))
    longest_rep_turn = max((s.end - s.start for s in rep_segs), default=0.0)

    total_words = sum(_word_count(s.text) for s in transcript)
    words_per_minute = (total_words / (duration / 60)) if duration > 0 else 0.0

    if duration > 0 and transcript:
        bucket_width = duration / _SENTIMENT_BUCKETS
        curve = []
        for i in range(_SENTIMENT_BUCKETS):
            lo, hi = i * bucket_width, (i + 1) * bucket_width
            in_bucket = [s for s in transcript if s.start < hi and s.end >= lo]
            raw = sum(_score_text(s.text) for s in in_bucket)
            curve.append(max(-1.0, min(1.0, raw / 2)))
    else:
        curve = []

    label = _sentiment_label(curve)
    if not known_segs:
        label = "insufficient speaker data"

    return ConversationShape(
        talk_ratio_rep=talk_ratio_rep,
        questions_asked_rep=questions_asked_rep,
        longest_rep_turn=longest_rep_turn,
        words_per_minute=words_per_minute,
        sentiment_curve=curve,
        sentiment_label=label,
    )


def compute_behavior_flags(
    transcript: list[TranscriptSegment], extraction: ExtractionResult | None, rubric: RubricSettings
) -> BehaviorFlags:
    rep_segs = [s for s in transcript if s.speaker == Speaker.REP]

    monologue = any((s.end - s.start) > 45 for s in rep_segs)

    question_count = sum(1 for s in rep_segs if _QUESTION_RE.search(s.text))
    no_discovery_question = question_count < 2

    no_dated_next_step = True
    if extraction and extraction.next_steps:
        no_dated_next_step = not any(ns.due for ns in extraction.next_steps)

    early_segs = [s for s in transcript if s.start < 30]
    missing_disclosure = not any(
        pattern.search(s.text) for s in early_segs for pattern in _DISCLOSURE_PATTERNS
    )

    first_question_time = next((s.start for s in rep_segs if _QUESTION_RE.search(s.text)), None)
    discount_offered_first = any(
        pattern.search(s.text) and (first_question_time is None or s.start < first_question_time)
        for s in rep_segs
        for pattern in _DISCOUNT_PATTERNS
    )

    return BehaviorFlags(
        monologue=monologue if rubric.flags.monologue else False,
        no_discovery_question=no_discovery_question if rubric.flags.no_discovery_question else False,
        no_dated_next_step=no_dated_next_step if rubric.flags.no_dated_next_step else False,
        missing_disclosure=missing_disclosure if rubric.flags.missing_disclosure else False,
        discount_offered_first=discount_offered_first if rubric.flags.discount_offered_first else False,
    )
