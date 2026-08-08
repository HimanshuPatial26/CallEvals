"""Computes CallInsights directly from transcript timestamps and text — no LLM
call, no added cost, no new "low precision" surface. Deliberately kept to
factual per-call readouts rather than a combined score; see schemas.CallInsights
for why.
"""

from app.schemas import CallInsights, Speaker, TranscriptSegment


def compute_call_insights(transcript: list[TranscriptSegment]) -> CallInsights | None:
    if not any(s.speaker in (Speaker.REP, Speaker.CUSTOMER) for s in transcript):
        return None

    ordered = sorted(transcript, key=lambda s: s.start)
    rep_segments = [s for s in ordered if s.speaker == Speaker.REP]
    customer_segments = [s for s in ordered if s.speaker == Speaker.CUSTOMER]

    rep_time = sum(s.end - s.start for s in rep_segments)
    customer_time = sum(s.end - s.start for s in customer_segments)
    total_time = rep_time + customer_time

    return CallInsights(
        rep_talk_time_ratio=(rep_time / total_time) if total_time > 0 else 0.0,
        longest_rep_monologue_seconds=_longest_monologue(ordered, Speaker.REP),
        rep_questions_asked=sum(1 for s in rep_segments if "?" in s.text),
        customer_questions_asked=sum(1 for s in customer_segments if "?" in s.text),
        interruption_count=_count_overlaps(ordered),
    )


def _longest_monologue(ordered: list[TranscriptSegment], speaker: Speaker) -> float:
    """Longest total duration of a contiguous run of `speaker` segments,
    where "contiguous" means no other speaker's turn falls in between."""
    longest = 0.0
    run_start: float | None = None
    run_end: float | None = None
    for seg in ordered:
        if seg.speaker == speaker:
            if run_start is None:
                run_start = seg.start
            run_end = seg.end
        elif run_start is not None:
            longest = max(longest, run_end - run_start)
            run_start = None
    if run_start is not None:
        longest = max(longest, run_end - run_start)
    return longest


def _count_overlaps(ordered: list[TranscriptSegment]) -> int:
    """Counts adjacent segment pairs from different speakers where the second
    started before the first ended — an approximation (only checks neighboring
    pairs, not all pairs), good enough for a per-call directional signal."""
    overlaps = 0
    for prev, curr in zip(ordered, ordered[1:]):
        if curr.speaker != prev.speaker and curr.start < prev.end:
            overlaps += 1
    return overlaps
