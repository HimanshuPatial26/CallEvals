from app.analysis import compute_behavior_flags, compute_conversation_shape, compute_duration
from app.schemas import ExtractionResult, NextStep, RubricSettings, Speaker, TranscriptSegment


def _seg(speaker: Speaker, start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(speaker=speaker, start=start, end=end, text=text)


def test_compute_duration_uses_last_segment_end():
    transcript = [_seg(Speaker.REP, 0, 5, "hi"), _seg(Speaker.CUSTOMER, 5, 12.5, "hello")]
    assert compute_duration(transcript) == 12.5


def test_compute_duration_empty_transcript():
    assert compute_duration([]) == 0.0


def test_talk_ratio_and_questions():
    transcript = [
        _seg(Speaker.REP, 0, 10, "Can I ask what your budget is?"),
        _seg(Speaker.CUSTOMER, 10, 15, "Around 2 million."),
        _seg(Speaker.REP, 15, 20, "Understood, thanks."),
    ]
    shape = compute_conversation_shape(transcript)
    assert shape.talk_ratio_rep == 15 / 20
    assert shape.questions_asked_rep == 1
    assert shape.longest_rep_turn == 10


def test_conversation_shape_handles_no_known_speakers():
    transcript = [_seg(Speaker.UNKNOWN, 0, 10, "something")]
    shape = compute_conversation_shape(transcript)
    assert shape.talk_ratio_rep == 0.0
    assert shape.sentiment_label == "insufficient speaker data"


def test_monologue_flag_fires_over_45_seconds():
    transcript = [_seg(Speaker.REP, 0, 50, "a very long uninterrupted turn " * 5)]
    flags = compute_behavior_flags(transcript, None, RubricSettings())
    assert flags.monologue is True


def test_monologue_flag_disabled_via_rubric_toggle():
    transcript = [_seg(Speaker.REP, 0, 50, "long turn")]
    rubric = RubricSettings()
    rubric.flags.monologue = False
    flags = compute_behavior_flags(transcript, None, rubric)
    assert flags.monologue is False


def test_no_discovery_question_flag():
    transcript = [_seg(Speaker.REP, 0, 5, "Here is the pitch, no questions asked.")]
    flags = compute_behavior_flags(transcript, None, RubricSettings())
    assert flags.no_discovery_question is True


def test_dated_next_step_clears_flag():
    transcript = [_seg(Speaker.REP, 0, 5, "hi")]
    extraction = ExtractionResult(
        summary="s", next_steps=[NextStep(description="send offer", owner=Speaker.REP, due="tomorrow", confidence=0.9)]
    )
    flags = compute_behavior_flags(transcript, extraction, RubricSettings())
    assert flags.no_dated_next_step is False


def test_missing_disclosure_when_absent_in_first_30s():
    transcript = [_seg(Speaker.REP, 0, 5, "Hi, thanks for your time today.")]
    flags = compute_behavior_flags(transcript, None, RubricSettings())
    assert flags.missing_disclosure is True


def test_disclosure_detected_clears_flag():
    transcript = [_seg(Speaker.REP, 0, 5, "Just to note, this call is recorded for quality and training.")]
    flags = compute_behavior_flags(transcript, None, RubricSettings())
    assert flags.missing_disclosure is False


def test_discount_offered_before_first_question_flags():
    transcript = [
        _seg(Speaker.REP, 0, 5, "I can offer you a discount right away."),
        _seg(Speaker.REP, 5, 10, "What is your budget?"),
    ]
    rubric = RubricSettings()
    rubric.flags.discount_offered_first = True
    flags = compute_behavior_flags(transcript, None, rubric)
    assert flags.discount_offered_first is True
