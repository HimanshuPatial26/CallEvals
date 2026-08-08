from app.insights import compute_call_insights
from app.schemas import Speaker, TranscriptSegment


def seg(speaker, start, end, text=""):
    return TranscriptSegment(speaker=speaker, start=start, end=end, text=text)


def test_mono_unknown_only_returns_none():
    transcript = [seg(Speaker.UNKNOWN, 0.0, 1.0, "hello")]
    assert compute_call_insights(transcript) is None


def test_empty_transcript_returns_none():
    assert compute_call_insights([]) is None


def test_talk_time_ratio():
    transcript = [
        seg(Speaker.REP, 0.0, 8.0),  # 8s rep
        seg(Speaker.CUSTOMER, 8.0, 10.0),  # 2s customer
    ]
    insights = compute_call_insights(transcript)
    assert insights.rep_talk_time_ratio == 0.8


def test_longest_rep_monologue_breaks_on_customer_turn():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0),
        seg(Speaker.REP, 3.0, 5.0),  # contiguous with above -> 5s run
        seg(Speaker.CUSTOMER, 5.0, 6.0),  # breaks the run
        seg(Speaker.REP, 6.0, 8.0),  # new 2s run
    ]
    insights = compute_call_insights(transcript)
    assert insights.longest_rep_monologue_seconds == 5.0


def test_questions_asked_counts_per_speaker():
    transcript = [
        seg(Speaker.REP, 0.0, 1.0, "What's your budget?"),
        seg(Speaker.CUSTOMER, 1.0, 2.0, "Around 2 million."),
        seg(Speaker.REP, 2.0, 3.0, "Great, and your timeline?"),
        seg(Speaker.CUSTOMER, 3.0, 4.0, "Is there a payment plan available?"),
    ]
    insights = compute_call_insights(transcript)
    assert insights.rep_questions_asked == 2
    assert insights.customer_questions_asked == 1


def test_interruption_detected_when_next_segment_starts_before_previous_ends():
    transcript = [
        seg(Speaker.REP, 0.0, 5.0),
        seg(Speaker.CUSTOMER, 4.0, 6.0),  # starts before rep's segment ends at 5.0
        seg(Speaker.REP, 6.0, 8.0),  # clean handoff, no overlap
    ]
    insights = compute_call_insights(transcript)
    assert insights.interruption_count == 1


def test_no_interruptions_on_clean_handoffs():
    transcript = [
        seg(Speaker.REP, 0.0, 5.0),
        seg(Speaker.CUSTOMER, 5.0, 6.0),
        seg(Speaker.REP, 6.0, 8.0),
    ]
    insights = compute_call_insights(transcript)
    assert insights.interruption_count == 0
