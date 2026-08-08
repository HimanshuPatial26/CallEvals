from datetime import date

from app.performance_metrics import compute_performance_metrics, distinct_leads, peer_benchmark, reached_stage_in_period
from app.schemas import FunnelStage
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
