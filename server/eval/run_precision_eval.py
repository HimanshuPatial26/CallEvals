"""Phase 0 deliverable (PRD section 9): run extraction against scripted mock calls
with hand-labeled ground truth, and measure precision — this is how A1 ("is
extraction accurate enough to trust") gets tested before any customer is involved.

Deliberately transcript-only, not audio-in: A1 is about the LLM extraction step,
which is decoupled from ASR quality. Feeding it real audio would conflate two
different risks (ASR word-error-rate vs. extraction precision) in one number.
F1 (transcription) gets its own accuracy check separately, against real call
audio, once there's real audio to check it against (see PRD section 10, "Audio
quality").

Usage:
    cd server && python -m eval.run_precision_eval
Requires GEMINI_API_KEY in server/.env (free tier — see .env.example).
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.extraction.gemini_extractor import GeminiExtractor
from app.schemas import ExtractionResult, Speaker, TranscriptSegment

MOCK_CALLS_DIR = Path(__file__).parent / "mock_calls"
NEXT_STEP_PRECISION_TARGET = 0.85  # PRD section 6


@dataclass
class MatchResult:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    details: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else None


def _keyword_hit(text: str, keywords: list[str], min_fraction: float = 0.5) -> bool:
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return keywords and (hits / len(keywords)) >= min_fraction


def score_next_steps(extracted: ExtractionResult, ground_truth: list[dict]) -> MatchResult:
    result = MatchResult()
    matched_gt = set()
    for step in extracted.next_steps:
        match = None
        for i, gt in enumerate(ground_truth):
            if i in matched_gt:
                continue
            if step.owner.value == gt["owner"] and _keyword_hit(step.description, gt["keywords"]):
                match = i
                break
        if match is not None:
            matched_gt.add(match)
            result.true_positives += 1
        else:
            result.false_positives += 1
            result.details.append(f"FP next_step: {step.description!r}")
    result.false_negatives = len(ground_truth) - len(matched_gt)
    for i, gt in enumerate(ground_truth):
        if i not in matched_gt:
            result.details.append(f"FN next_step: {gt['description']!r}")
    return result


def score_objections(extracted: ExtractionResult, ground_truth: list[dict]) -> MatchResult:
    result = MatchResult()
    matched_gt = set()
    for obj in extracted.objections:
        match = None
        for i, gt in enumerate(ground_truth):
            if i in matched_gt:
                continue
            if obj.category.value == gt["category"] and _keyword_hit(obj.quote, gt["keywords"], min_fraction=0.01):
                match = i
                break
        if match is not None:
            matched_gt.add(match)
            result.true_positives += 1
        else:
            result.false_positives += 1
            result.details.append(f"FP objection: {obj.category.value} — {obj.quote!r}")
    result.false_negatives = len(ground_truth) - len(matched_gt)
    for i, gt in enumerate(ground_truth):
        if i not in matched_gt:
            result.details.append(f"FN objection: {gt['category']} — {gt['keywords']}")
    return result


def load_mock_call(path: Path) -> tuple[str, list[TranscriptSegment], dict]:
    data = json.loads(path.read_text())
    transcript = [
        TranscriptSegment(speaker=Speaker(seg["speaker"]), start=seg["start"], end=seg["end"], text=seg["text"])
        for seg in data["transcript"]
    ]
    return data["id"], transcript, data["ground_truth"]


def main() -> int:
    mock_call_paths = sorted(MOCK_CALLS_DIR.glob("*.json"))
    if not mock_call_paths:
        print(f"No mock calls found in {MOCK_CALLS_DIR}")
        return 1

    extractor = GeminiExtractor()

    total_next_steps = MatchResult()
    total_objections = MatchResult()
    rows = []

    for path in mock_call_paths:
        call_id, transcript, ground_truth = load_mock_call(path)
        extracted = extractor.extract(transcript)

        ns_result = score_next_steps(extracted, ground_truth["next_steps"])
        obj_result = score_objections(extracted, ground_truth["objections"])

        for r, total in ((ns_result, total_next_steps), (obj_result, total_objections)):
            total.true_positives += r.true_positives
            total.false_positives += r.false_positives
            total.false_negatives += r.false_negatives
            total.details.extend(f"[{call_id}] {d}" for d in r.details)

        rows.append((call_id, ns_result, obj_result))

    print(f"{'call':<32} {'next_step P/R':<18} {'objection P/R':<18}")
    for call_id, ns, obj in rows:
        ns_str = f"{fmt(ns.precision)}/{fmt(ns.recall)}"
        obj_str = f"{fmt(obj.precision)}/{fmt(obj.recall)}"
        print(f"{call_id:<32} {ns_str:<18} {obj_str:<18}")

    print()
    print(f"TOTAL next_steps  precision={fmt(total_next_steps.precision)}  recall={fmt(total_next_steps.recall)}")
    print(f"TOTAL objections  precision={fmt(total_objections.precision)}  recall={fmt(total_objections.recall)}")

    if total_next_steps.details or total_objections.details:
        print("\nMismatches:")
        for d in total_next_steps.details + total_objections.details:
            print(f"  {d}")

    print(f"\nPRD launch gate: next-step precision >= {NEXT_STEP_PRECISION_TARGET:.0%}")
    if total_next_steps.precision is not None and total_next_steps.precision < NEXT_STEP_PRECISION_TARGET:
        print("NOT MET — do not treat extraction as trustworthy yet.")
        return 1

    print("Met (on this mock set — re-run against real brokerage calls before trusting it in production).")
    return 0


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


if __name__ == "__main__":
    sys.exit(main())
