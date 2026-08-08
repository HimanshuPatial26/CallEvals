from datetime import date, datetime, timezone

from app.performance_metrics import compute_performance_metrics, distinct_leads, peer_benchmark, reached_stage_in_period
from app.schemas import FunnelStage, LeadStageEvent, LostReason
from tests.factories import OMAR, PERIOD_END, PERIOD_START, RAHUL, SARA, make_call, make_lead, stage_event


def test_distinct_leads_dedupes_and_ignores_unknown_ids():
    lead1 = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-1", 2),  # same lead again
        make_call("c3", "agent-rahul", "lead-missing", 3),  # not in leads_by_id
    ]
    leads = distinct_leads(records, {"lead-1": lead1})
    assert [lead.id for lead in leads] == ["lead-1"]


def test_reached_stage_in_period_respects_bounds():
    lead = make_lead("lead-1", stage=FunnelStage.WON, stage_events=[stage_event(FunnelStage.WON, 15)])
    assert reached_stage_in_period(lead, FunnelStage.WON, PERIOD_START, PERIOD_END) is True
    assert reached_stage_in_period(lead, FunnelStage.WON, date(2026, 9, 1), date(2026, 9, 30)) is False
    assert reached_stage_in_period(lead, FunnelStage.LOST, PERIOD_START, PERIOD_END) is False


def test_compute_performance_metrics_is_population_agnostic():
    """The engine doesn't care whether records mix multiple agents/teams --
    it just aggregates whatever list it's handed."""
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 2, score_mult=0.5),
    ]
    metrics = compute_performance_metrics(records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the team")
    assert metrics.calls_analyzed == 2
    assert metrics.avg_call_score is not None


def test_compute_performance_metrics_subject_flows_into_coaching_text():
    lead1 = make_lead("lead-1", stage=FunnelStage.QUALIFIED)
    records = [make_call("c1", "agent-rahul", "lead-1", 1, with_next_step=False)]
    metrics = compute_performance_metrics(records, {"lead-1": lead1}, PERIOD_START, PERIOD_END, [], [], subject="the org")
    assert any("The org fails to log a next step" in c.problem for c in metrics.coaching_recommendations)


def test_peer_benchmark_empty_peer_records_yields_none_comparisons():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1)]
    metrics = compute_performance_metrics(records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the org")
    rows = peer_benchmark(
        metrics.avg_call_score, metrics.talk_time, metrics.conversion, metrics.compliance_score_pct,
        [], {"lead-1": lead}, PERIOD_START, PERIOD_END, comparison_label="Org average",
    )
    assert rows  # agent's own values still populate the rows
    assert all(row.comparison_value is None for row in rows)
    assert all(row.comparison_label == "Org average" for row in rows)


def test_peer_benchmark_uses_only_the_given_peer_population():
    lead = make_lead("lead-1")
    subject_records = [make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0)]
    peer_records = [make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5)]
    metrics = compute_performance_metrics(
        subject_records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], peer_records, subject="the team"
    )
    rows = peer_benchmark(
        metrics.avg_call_score, metrics.talk_time, metrics.conversion, metrics.compliance_score_pct,
        peer_records, {"lead-1": lead}, PERIOD_START, PERIOD_END, comparison_label="Team average",
    )
    overall_row = next(r for r in rows if r.label == "Overall score")
    peer_metrics = compute_performance_metrics(peer_records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    assert overall_row.comparison_value == peer_metrics.avg_call_score


def test_calls_to_close_excludes_calls_placed_after_the_won_date():
    # lead won on the 10th; a 3rd call on the 15th is a post-close courtesy
    # call and must not count toward "how many calls did it take."
    lead = make_lead(
        "lead-1",
        stage=FunnelStage.WON,
        stage_events=[LeadStageEvent(stage=FunnelStage.WON, changed_at=datetime(2026, 8, 10, tzinfo=timezone.utc))],
        created_day=1,
    )
    records = [
        make_call("c1", "agent-rahul", "lead-1", 5),
        make_call("c2", "agent-rahul", "lead-1", 8),
        make_call("c3", "agent-rahul", "lead-1", 15),  # after the won date
    ]
    metrics = compute_performance_metrics(records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    assert metrics.calls_to_close.avg_calls_to_close == 2.0
    assert metrics.calls_to_close.won_leads_measured == 1


def test_calls_to_close_avg_days_to_close_uses_lead_created_at_not_first_call():
    lead = make_lead(
        "lead-1",
        stage=FunnelStage.WON,
        stage_events=[LeadStageEvent(stage=FunnelStage.WON, changed_at=datetime(2026, 8, 10, tzinfo=timezone.utc))],
        created_day=1,  # July 1 -- created_at is the true clock start
    )
    records = [make_call("c1", "agent-rahul", "lead-1", 5)]
    metrics = compute_performance_metrics(records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    # July 1 -> Aug 10 == 40 days
    assert metrics.calls_to_close.avg_days_to_close == 40.0


def test_calls_to_close_distribution_covers_every_touched_lead_not_just_won():
    lead1 = make_lead("lead-1")  # untagged, 1 call
    lead2 = make_lead("lead-2")  # untagged, 3 calls
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-2", 1),
        make_call("c3", "agent-rahul", "lead-2", 2),
        make_call("c4", "agent-rahul", "lead-2", 3),
    ]
    metrics = compute_performance_metrics(
        records, {"lead-1": lead1, "lead-2": lead2}, PERIOD_START, PERIOD_END, [], [], subject="the agent"
    )
    dist = {b.range_label: b.count for b in metrics.calls_to_close.calls_per_lead_distribution}
    assert dist["1"] == 1
    assert dist["3-4"] == 1
    assert metrics.calls_to_close.avg_calls_to_close is None  # nothing won this period
    assert metrics.calls_to_close.won_leads_measured == 0


def test_lost_reasons_only_counts_lost_leads_with_a_reason_recorded():
    lead1 = make_lead("lead-1", stage=FunnelStage.LOST, lost_reason=LostReason.PRICE)
    lead2 = make_lead("lead-2", stage=FunnelStage.LOST, lost_reason=LostReason.PRICE)
    lead3 = make_lead("lead-3", stage=FunnelStage.LOST)  # lost, but no reason recorded
    lead4 = make_lead("lead-4", stage=FunnelStage.WON)  # not lost at all
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-2", 1),
        make_call("c3", "agent-rahul", "lead-3", 1),
        make_call("c4", "agent-rahul", "lead-4", 1),
    ]
    leads_by_id = {l.id: l for l in [lead1, lead2, lead3, lead4]}
    metrics = compute_performance_metrics(records, leads_by_id, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    assert metrics.lost_reasons.total_lost_with_reason == 2  # lead3 excluded, lead4 excluded
    assert len(metrics.lost_reasons.by_reason) == 1  # single row -- both leads share PRICE
    assert metrics.lost_reasons.by_reason[0].reason == LostReason.PRICE
    assert metrics.lost_reasons.by_reason[0].count == 2
    assert metrics.lost_reasons.by_reason[0].pct == 100.0


def test_lost_reasons_empty_when_nothing_lost():
    lead = make_lead("lead-1", stage=FunnelStage.WON)
    records = [make_call("c1", "agent-rahul", "lead-1", 1)]
    metrics = compute_performance_metrics(records, {"lead-1": lead}, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    assert metrics.lost_reasons.total_lost_with_reason == 0
    assert metrics.lost_reasons.by_reason == []


def test_source_breakdown_groups_by_source_and_buckets_missing_as_unknown():
    lead1 = make_lead("lead-1", source="website", stage=FunnelStage.WON, stage_events=[stage_event(FunnelStage.WON, 15)])
    lead2 = make_lead("lead-2", source="website")
    lead3 = make_lead("lead-3", source=None)
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-2", 1),
        make_call("c3", "agent-rahul", "lead-3", 1),
    ]
    leads_by_id = {l.id: l for l in [lead1, lead2, lead3]}
    metrics = compute_performance_metrics(records, leads_by_id, PERIOD_START, PERIOD_END, [], [], subject="the agent")
    by_source = {row.source: row for row in metrics.source_breakdown.by_source}
    assert by_source["website"].leads_touched == 2
    assert by_source["website"].conversion_rate_pct == 50.0  # 1 of 2 website leads won
    assert by_source["Unknown"].leads_touched == 1
    assert by_source["Unknown"].conversion_rate_pct == 0.0
