from datetime import datetime, timedelta, timezone

from app import rollups
from app.schemas import BehaviorFlags, CallRecord, ExtractionResult, NextStep, Objection, ReviewFeedback


def _flags(**overrides) -> BehaviorFlags:
    base = dict(
        monologue=False, no_discovery_question=False, no_dated_next_step=False,
        missing_disclosure=False, discount_offered_first=False,
    )
    base.update(overrides)
    return BehaviorFlags(**base)


def _call(status="done", created_at=None, flags=None, feedback=None, objections=None, next_steps=None) -> CallRecord:
    return CallRecord(
        id="c" + str(id(object())),
        filename="f.wav",
        dual_channel=True,
        created_at=created_at or datetime.now(timezone.utc),
        status=status,
        flags=flags,
        feedback=feedback or [],
        extraction=ExtractionResult(summary="s", next_steps=next_steps or [], objections=objections or []) if status == "done" else None,
    )


def test_coverage_counts_done_vs_attempted():
    calls = [_call(status="done"), _call(status="done"), _call(status="failed"), _call(status="processing")]
    assert rollups.coverage(calls) == 66.7


def test_coverage_empty():
    assert rollups.coverage([]) == 0.0


def test_extraction_precision_from_next_step_feedback_only():
    calls = [
        _call(feedback=[ReviewFeedback(item_type="next_step", item_index=0, confirmed=True)]),
        _call(feedback=[ReviewFeedback(item_type="next_step", item_index=0, confirmed=False)]),
        _call(feedback=[ReviewFeedback(item_type="objection", item_index=0, confirmed=False)]),
    ]
    assert rollups.extraction_precision(calls) == 50.0


def test_manager_engagement_checks_24h_window():
    now = datetime.now(timezone.utc)
    fast = _call(created_at=now - timedelta(hours=2))
    fast.first_viewed_at = now - timedelta(hours=1)
    slow = _call(created_at=now - timedelta(days=3))
    slow.first_viewed_at = now
    assert rollups.manager_engagement([fast, slow]) == 50.0


def test_objection_mix_counts_by_category():
    calls = [
        _call(objections=[Objection(category="price", quote="q", confidence=0.9)]),
        _call(objections=[Objection(category="price", quote="q2", confidence=0.9)]),
        _call(objections=[Objection(category="timing", quote="q3", confidence=0.9)]),
    ]
    mix = rollups.objection_mix(calls)
    assert mix[0] == {"category": "price", "raised": 2, "pct": 66.7}


def test_behavior_improvement_rate_detects_cleared_flag():
    now = datetime.now(timezone.utc)
    calls = [
        _call(created_at=now - timedelta(days=5), flags=_flags(monologue=True)),
        _call(created_at=now - timedelta(days=4), flags=_flags(monologue=False)),
        _call(created_at=now - timedelta(days=3), flags=_flags(monologue=False)),
    ]
    rate, rows = rollups.behavior_improvement_rate(calls)
    monologue_row = next(r for r in rows if r["name"] == "Monologue")
    assert monologue_row["dots"] == [1, 1]
    assert monologue_row["status"] == "improved"


def test_lead_open_next_step_picks_latest_call():
    calls = [
        CallRecord(
            id="a", filename="a.wav", dual_channel=True, created_at=datetime.now(timezone.utc) - timedelta(days=1),
            status="done", lead_id="lead-1",
            extraction=ExtractionResult(summary="s", next_steps=[NextStep(description="old", owner="rep", confidence=0.9)]),
        ),
        CallRecord(
            id="b", filename="b.wav", dual_channel=True, created_at=datetime.now(timezone.utc),
            status="done", lead_id="lead-1",
            extraction=ExtractionResult(summary="s", next_steps=[NextStep(description="new", owner="rep", confidence=0.9)]),
        ),
    ]
    step = rollups.lead_open_next_step(calls, "lead-1")
    assert step["description"] == "new"
