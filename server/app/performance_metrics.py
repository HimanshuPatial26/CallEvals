"""Shared aggregation engine behind every level of the CALL -> AGENT -> TEAM
-> ORGANIZATION rollup (ROADMAP.md Phase B). Population-agnostic: every
function here takes an already-filtered list[CallRecord] and has no idea
whether that population is "one agent's calls," "one team's calls," or
"every call in the org" — that filtering is each level's own module's job
(app/agent_performance.py, app/team_performance.py, app/org_performance.py).

This is a straight extraction, not a rewrite — the math is identical to
what app/agent_performance.py computed before Phase B, just with "team"-
specific naming (teammate_records, _team_benchmark) generalized to
"peer"-specific naming (peer_records, comparison_label) so the same code
serves an agent's teammates, a team's peer teams, or (passing an empty
peer population) an org with no peer to compare against.

Two things the source doc asked for are deliberately NOT computed here —
see the notes this returns for why, spelled out at the point each would
get built rather than silently skipped:

1. Dialer-level call volume (assigned/attempted/connected/missed). This app
   only ever sees a call once someone uploads a recording — there's no data
   source for "attempted but never connected."
2. Itemized discovery-field percentages (need/budget/timeline/decision-maker
   identified individually). The per-call extraction only produces one
   aggregate discovery score + evidence string; adding seven new boolean
   fields there is a schema change out of scope for this pass.

Conversion/funnel/revenue metrics (ROADMAP.md C1) depend entirely on
Lead.stage / stage_history, set manually via POST /api/leads/{id}/stage —
there is no CRM integration (PRD section 8 defers that to Phase 2). A lead
counts as "converted" only in the period its stage_history shows it
transitioning to won — see ConversionAgg's docstring in schemas.py.
"""

import statistics
from datetime import date, timedelta

from app.schemas import (
    AgentScoreBreakdown,
    BenchmarkRow,
    CallRecord,
    CallVolumeBucket,
    CallsToCloseAgg,
    ClosingAgg,
    CoachingRecommendation,
    ConversionAgg,
    FunnelStage,
    IntentDistribution,
    IntentLevel,
    Lead,
    LostReasonAgg,
    LostReasonBreakdownRow,
    ObjectionAgg,
    ObjectionCategoryAgg,
    PerformanceMetrics,
    QualityBucket,
    QualityOutcomeQuadrant,
    ScoreDimensionAgg,
    SentimentAgg,
    SentimentLabel,
    SourceAgg,
    SourceBreakdownRow,
    StrengthWeakness,
    TalkTimeAgg,
    TrendPoint,
)

SENTIMENT_SCORE = {SentimentLabel.POSITIVE: 100.0, SentimentLabel.NEUTRAL: 60.0, SentimentLabel.NEGATIVE: 20.0}

# Doc section 2's 8-dim weighting (Discovery 20 / Objection 15 / Pitch 15 /
# Closing 15 / Communication 10 / Sentiment 10 / Compliance 10 / Call
# Discipline 5) with Call Discipline excluded (no defined scoring method)
# and the remaining 95 points renormalized to sum to 100.
_RAW_WEIGHTS = {
    "discovery_qualification": 20.0,
    "objection_handling": 15.0,
    "pitch_value_prop": 15.0,
    "closing_next_steps": 15.0,
    "communication": 10.0,
    "sentiment": 10.0,
    "compliance": 10.0,
}
_WEIGHT_TOTAL = sum(_RAW_WEIGHTS.values())  # 95
_WEIGHTS = {k: v / _WEIGHT_TOTAL * 100.0 for k, v in _RAW_WEIGHTS.items()}

_COACHING_TEXT = {
    "discovery_qualification": "Train on qualification checklists — confirm budget, timeline, and decision-maker before pitching.",
    "objection_handling": "Role-play the most common objection category with value-based responses instead of default discounting.",
    "pitch_value_prop": "Tie every feature mentioned back to a stated customer need before moving on.",
    "closing_next_steps": "Always propose a specific, time-bound next step rather than ending the call open-ended.",
    "communication": "Slow down and check for understanding more often; avoid talking past customer responses.",
    "sentiment": "Investigate calls where sentiment declines — customers may be feeling rushed or unheard.",
    "compliance": "Review the required-disclosure and prohibited-claim checklist before the next call block.",
}

DIM_LABELS = {
    "discovery_qualification": "Discovery & qualification",
    "objection_handling": "Objection handling",
    "pitch_value_prop": "Pitch & value proposition",
    "closing_next_steps": "Closing & next steps",
    "communication": "Communication & active listening",
    "sentiment": "Customer sentiment",
    "compliance": "Compliance & process",
}

UNIVERSAL_NOTES = [
    "Call volume (assigned/attempted/connected/missed) needs dialer telemetry this app doesn't have — "
    "only calls_analyzed (successfully uploaded and processed) is shown.",
    "Discovery is one aggregate score; itemized need/budget/timeline/decision-maker-identified percentages "
    "would need a per-call extraction schema change not made in this pass.",
]


def distinct_leads(records: list[CallRecord], leads_by_id: dict[str, Lead]) -> list[Lead]:
    seen: dict[str, Lead] = {}
    for r in records:
        if r.lead_id not in seen and r.lead_id in leads_by_id:
            seen[r.lead_id] = leads_by_id[r.lead_id]
    return list(seen.values())


def reached_stage_in_period(lead: Lead, stage: FunnelStage, start: date, end: date) -> bool:
    return any(event.stage == stage and start <= event.changed_at.date() <= end for event in lead.stage_history)


def _communication_call_score(record: CallRecord) -> float | None:
    breakdown = record.extraction.score_breakdown if record.extraction else None
    if breakdown is None:
        return None
    parts = [
        breakdown.opening_rapport.score / breakdown.opening_rapport.max_score,
        breakdown.active_listening.score / breakdown.active_listening.max_score,
        breakdown.communication_professionalism.score / breakdown.communication_professionalism.max_score,
    ]
    return sum(parts) / len(parts) * 100.0


def dim_call_score(record: CallRecord, key: str) -> float | None:
    if key == "communication":
        return _communication_call_score(record)
    if key == "sentiment":
        sentiment = record.extraction.sentiment if record.extraction else None
        return SENTIMENT_SCORE[sentiment.overall] if sentiment else None
    if key == "compliance":
        return record.compliance.adherence_pct if record.compliance else None
    breakdown = record.extraction.score_breakdown if record.extraction else None
    if breakdown is None:
        return None
    dim = getattr(breakdown, key)
    return dim.score / dim.max_score * 100.0


def _dim_agg(key: str, records: list[CallRecord], peer_records: list[CallRecord]) -> ScoreDimensionAgg:
    values = [v for r in records if (v := dim_call_score(r, key)) is not None]
    peer_values = [v for r in peer_records if (v := dim_call_score(r, key)) is not None]
    return ScoreDimensionAgg(
        label=DIM_LABELS[key],
        agent_score=round(statistics.fmean(values), 1) if values else 0.0,
        team_benchmark=round(statistics.fmean(peer_values), 1) if peer_values else None,
        calls_scored=len(values),
    )


def _score_breakdown(records: list[CallRecord], peer_records: list[CallRecord]) -> AgentScoreBreakdown | None:
    scored = [r for r in records if r.extraction and r.extraction.score_breakdown]
    if not scored:
        return None

    dims = {key: _dim_agg(key, records, peer_records) for key in _RAW_WEIGHTS}
    overall = sum(dims[key].agent_score * _WEIGHTS[key] / 100.0 for key in _RAW_WEIGHTS)

    return AgentScoreBreakdown(
        discovery_qualification=dims["discovery_qualification"],
        objection_handling=dims["objection_handling"],
        pitch_value_prop=dims["pitch_value_prop"],
        closing_next_steps=dims["closing_next_steps"],
        communication=dims["communication"],
        sentiment=dims["sentiment"],
        compliance=dims["compliance"],
        overall_score=round(overall, 1),
    )


def _talk_time(records: list[CallRecord], peer_records: list[CallRecord]) -> TalkTimeAgg | None:
    with_insights = [r for r in records if r.insights]
    if not with_insights:
        return None

    rep_pct = [r.insights.rep_talk_time_ratio * 100.0 for r in with_insights]
    peer_rep_pct = [r.insights.rep_talk_time_ratio * 100.0 for r in peer_records if r.insights]

    return TalkTimeAgg(
        avg_rep_talk_pct=round(statistics.fmean(rep_pct), 1),
        avg_customer_talk_pct=round(100.0 - statistics.fmean(rep_pct), 1),
        avg_interruptions=round(statistics.fmean(r.insights.interruption_count for r in with_insights), 1),
        avg_questions_per_call=round(statistics.fmean(r.insights.rep_questions_asked for r in with_insights), 1),
        avg_longest_monologue_seconds=round(
            statistics.fmean(r.insights.longest_rep_monologue_seconds for r in with_insights), 1
        ),
        team_avg_rep_talk_pct=round(statistics.fmean(peer_rep_pct), 1) if peer_rep_pct else None,
    )


def _objections(records: list[CallRecord]) -> ObjectionAgg:
    all_objections = [obj for r in records if r.extraction for obj in r.extraction.objections]
    total = len(all_objections)
    if total == 0:
        return ObjectionAgg(total_objections=0, by_category=[], overall_handling_effectiveness_pct=None)

    by_category: dict[str, list] = {}
    for obj in all_objections:
        by_category.setdefault(obj.category, []).append(obj)

    rows = []
    for category, objs in by_category.items():
        addressed = sum(1 for o in objs if o.addressed)
        rows.append(
            ObjectionCategoryAgg(
                category=category,
                count=len(objs),
                frequency_pct=round(len(objs) / total * 100.0, 1),
                addressed_rate_pct=round(addressed / len(objs) * 100.0, 1),
            )
        )
    rows.sort(key=lambda r: r.count, reverse=True)
    weakest = min(rows, key=lambda r: (r.addressed_rate_pct, -r.count)).category

    total_addressed = sum(1 for o in all_objections if o.addressed)
    return ObjectionAgg(
        total_objections=total,
        by_category=rows,
        overall_handling_effectiveness_pct=round(total_addressed / total * 100.0, 1),
        weakest_category=weakest,
    )


def _closing(records: list[CallRecord], leads_by_id: dict[str, Lead]) -> ClosingAgg:
    touched_leads = distinct_leads(records, leads_by_id)
    tagged = [lead for lead in touched_leads if lead.stage != FunnelStage.UNTAGGED]
    demo_or_later = {FunnelStage.DEMO_BOOKED, FunnelStage.PROPOSAL_SENT, FunnelStage.WON}
    proposal_or_later = {FunnelStage.PROPOSAL_SENT, FunnelStage.WON}

    calls_by_lead: dict[str, list[CallRecord]] = {}
    for r in records:
        calls_by_lead.setdefault(r.lead_id, []).append(r)

    qualified_without_next_step = sum(
        1
        for lead in tagged
        if not any(r.extraction and r.extraction.next_steps for r in calls_by_lead.get(lead.id, []))
    )

    return ClosingAgg(
        calls_with_next_step=sum(1 for r in records if r.extraction and r.extraction.next_steps),
        calls_with_due_date=sum(1 for r in records if r.extraction and any(ns.due for ns in r.extraction.next_steps)),
        qualified_leads=len(tagged),
        demo_booked_leads=sum(1 for lead in tagged if lead.stage in demo_or_later),
        proposals_sent_leads=sum(1 for lead in tagged if lead.stage in proposal_or_later),
        won_leads=sum(1 for lead in tagged if lead.stage == FunnelStage.WON),
        lost_leads=sum(1 for lead in tagged if lead.stage == FunnelStage.LOST),
        qualified_leads_without_next_step=qualified_without_next_step,
    )


_SENTIMENT_ORDER = {SentimentLabel.NEGATIVE: 0, SentimentLabel.NEUTRAL: 1, SentimentLabel.POSITIVE: 2}


def _sentiment_agg(records: list[CallRecord]) -> SentimentAgg | None:
    with_sentiment = [r.extraction.sentiment for r in records if r.extraction and r.extraction.sentiment]
    if not with_sentiment:
        return None

    beginning = [SENTIMENT_SCORE[s.beginning] for s in with_sentiment]
    end = [SENTIMENT_SCORE[s.end] for s in with_sentiment]
    improved = sum(1 for s in with_sentiment if _SENTIMENT_ORDER[s.end] > _SENTIMENT_ORDER[s.beginning])
    deteriorated = sum(1 for s in with_sentiment if _SENTIMENT_ORDER[s.end] < _SENTIMENT_ORDER[s.beginning])
    positive = sum(1 for s in with_sentiment if s.overall == SentimentLabel.POSITIVE)
    negative = sum(1 for s in with_sentiment if s.overall == SentimentLabel.NEGATIVE)

    return SentimentAgg(
        avg_beginning_score=round(statistics.fmean(beginning), 1),
        avg_end_score=round(statistics.fmean(end), 1),
        sentiment_improvement=round(statistics.fmean(end) - statistics.fmean(beginning), 1),
        calls_improved=improved,
        calls_deteriorated=deteriorated,
        positive_pct=round(positive / len(with_sentiment) * 100.0, 1),
        negative_pct=round(negative / len(with_sentiment) * 100.0, 1),
    )


def _conversion(
    records: list[CallRecord], leads_by_id: dict[str, Lead], period_start: date, period_end: date
) -> ConversionAgg:
    touched_leads = distinct_leads(records, leads_by_id)
    leads_touched = len(touched_leads)
    tagged = [lead for lead in touched_leads if lead.stage != FunnelStage.UNTAGGED]
    won_in_period = [lead for lead in touched_leads if reached_stage_in_period(lead, FunnelStage.WON, period_start, period_end)]
    lost_in_period = [lead for lead in touched_leads if reached_stage_in_period(lead, FunnelStage.LOST, period_start, period_end)]
    deal_sizes = [lead.deal_size_aed for lead in won_in_period if lead.deal_size_aed is not None]

    with_intent_records = [r for r in records if r.extraction and r.extraction.buying_intent]
    intent_rows = []
    for level in IntentLevel:
        level_records = [r for r in with_intent_records if r.extraction.buying_intent.level == level]
        if not level_records:
            continue
        level_leads = distinct_leads(level_records, leads_by_id)
        level_won = [lead for lead in level_leads if reached_stage_in_period(lead, FunnelStage.WON, period_start, period_end)]
        intent_rows.append(
            IntentDistribution(
                level=level,
                count=len(level_records),
                pct=round(len(level_records) / len(with_intent_records) * 100.0, 1) if with_intent_records else 0.0,
                conversion_rate_pct=round(len(level_won) / len(level_leads) * 100.0, 1) if level_leads else None,
            )
        )

    return ConversionAgg(
        leads_touched=leads_touched,
        leads_tagged=len(tagged),
        qualified_rate_pct=round(len(tagged) / leads_touched * 100.0, 1) if leads_touched else None,
        conversion_rate_pct=round(len(won_in_period) / leads_touched * 100.0, 1) if leads_touched else None,
        lost_rate_pct=round(len(lost_in_period) / len(tagged) * 100.0, 1) if tagged else None,
        revenue_aed=round(sum(deal_sizes), 2) if deal_sizes else None,
        avg_deal_size_aed=round(sum(deal_sizes) / len(deal_sizes), 2) if deal_sizes else None,
        intent_breakdown=intent_rows,
    )


_CALLS_TO_CLOSE_BUCKETS = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, float("inf"), "5+")]


def _calls_to_close(
    records: list[CallRecord], leads_by_id: dict[str, Lead], period_start: date, period_end: date
) -> CallsToCloseAgg:
    touched_leads = distinct_leads(records, leads_by_id)
    calls_by_lead: dict[str, list[CallRecord]] = {}
    for r in records:
        calls_by_lead.setdefault(r.lead_id, []).append(r)

    counts = [len(calls_by_lead.get(lead.id, [])) for lead in touched_leads]
    buckets = []
    if counts:
        for low, high, label in _CALLS_TO_CLOSE_BUCKETS:
            bucket_count = sum(1 for c in counts if low <= c <= high)
            buckets.append(CallVolumeBucket(range_label=label, count=bucket_count, pct=round(bucket_count / len(counts) * 100.0, 1)))

    won_in_period = [lead for lead in touched_leads if reached_stage_in_period(lead, FunnelStage.WON, period_start, period_end)]
    calls_counts = []
    days_counts = []
    for lead in won_in_period:
        won_event = next(
            (e for e in lead.stage_history if e.stage == FunnelStage.WON and period_start <= e.changed_at.date() <= period_end),
            None,
        )
        if won_event is None:
            continue
        won_date = won_event.changed_at.date()
        calls_up_to_close = [r for r in calls_by_lead.get(lead.id, []) if r.created_at.date() <= won_date]
        calls_counts.append(len(calls_up_to_close))
        days_counts.append((won_date - lead.created_at.date()).days)

    return CallsToCloseAgg(
        calls_per_lead_distribution=buckets,
        avg_calls_to_close=round(statistics.fmean(calls_counts), 1) if calls_counts else None,
        avg_days_to_close=round(statistics.fmean(days_counts), 1) if days_counts else None,
        won_leads_measured=len(calls_counts),
    )


def _lost_reasons(records: list[CallRecord], leads_by_id: dict[str, Lead]) -> LostReasonAgg:
    touched_leads = distinct_leads(records, leads_by_id)
    lost_with_reason = [lead for lead in touched_leads if lead.stage == FunnelStage.LOST and lead.lost_reason is not None]
    if not lost_with_reason:
        return LostReasonAgg(total_lost_with_reason=0, by_reason=[])

    counts: dict = {}
    for lead in lost_with_reason:
        counts[lead.lost_reason] = counts.get(lead.lost_reason, 0) + 1

    rows = [
        LostReasonBreakdownRow(reason=reason, count=count, pct=round(count / len(lost_with_reason) * 100.0, 1))
        for reason, count in counts.items()
    ]
    rows.sort(key=lambda row: row.count, reverse=True)
    return LostReasonAgg(total_lost_with_reason=len(lost_with_reason), by_reason=rows)


def _source_breakdown(
    records: list[CallRecord], leads_by_id: dict[str, Lead], period_start: date, period_end: date
) -> SourceAgg:
    touched_leads = distinct_leads(records, leads_by_id)
    if not touched_leads:
        return SourceAgg(by_source=[])

    by_source: dict[str, list[Lead]] = {}
    for lead in touched_leads:
        by_source.setdefault(lead.source or "Unknown", []).append(lead)

    rows = []
    for source, leads in by_source.items():
        won = sum(1 for lead in leads if reached_stage_in_period(lead, FunnelStage.WON, period_start, period_end))
        rows.append(
            SourceBreakdownRow(
                source=source, leads_touched=len(leads), conversion_rate_pct=round(won / len(leads) * 100.0, 1)
            )
        )
    rows.sort(key=lambda row: row.leads_touched, reverse=True)
    return SourceAgg(by_source=rows)


_QUALITY_BUCKETS = [(90, 100, "90-100"), (80, 89.999, "80-89"), (70, 79.999, "70-79"), (60, 69.999, "60-69"), (0, 59.999, "<60")]


def _quality_distribution(records: list[CallRecord]) -> list[QualityBucket]:
    scores = [r.overall_score for r in records if r.overall_score is not None]
    if not scores:
        return []
    buckets = []
    for low, high, label in _QUALITY_BUCKETS:
        count = sum(1 for s in scores if low <= s <= high)
        buckets.append(QualityBucket(range_label=label, count=count, pct=round(count / len(scores) * 100.0, 1)))
    return buckets


def _consistency_score(records: list[CallRecord]) -> float | None:
    scores = [r.overall_score for r in records if r.overall_score is not None]
    if len(scores) < 2:
        return None
    return round(max(0.0, 100.0 - statistics.pstdev(scores)), 1)


def _trend(records: list[CallRecord], leads_by_id: dict[str, Lead], period_start: date, period_end: date) -> list[TrendPoint]:
    span_days = (period_end - period_start).days + 1
    num_weeks = max(1, -(-span_days // 7))  # ceil division
    points = []
    for week in range(num_weeks):
        week_start = period_start + timedelta(days=week * 7)
        week_end = min(period_end, week_start + timedelta(days=6))
        week_records = [r for r in records if week_start <= r.created_at.date() <= week_end]
        if not week_records:
            continue
        scored = [r.overall_score for r in week_records if r.overall_score is not None]
        week_leads = distinct_leads(week_records, leads_by_id)
        won_in_week = sum(1 for lead in week_leads if reached_stage_in_period(lead, FunnelStage.WON, week_start, week_end))
        points.append(
            TrendPoint(
                period_label=f"Week {week + 1}",
                calls=len(week_records),
                avg_score=round(statistics.fmean(scored), 1) if scored else None,
                conversion_rate_pct=round(won_in_week / len(week_leads) * 100.0, 1) if week_leads else None,
            )
        )
    return points


def _strengths_and_weaknesses(
    breakdown: AgentScoreBreakdown | None, records: list[CallRecord]
) -> tuple[list[StrengthWeakness], list[StrengthWeakness]]:
    if breakdown is None:
        return [], []

    dims = [
        ("discovery_qualification", breakdown.discovery_qualification),
        ("objection_handling", breakdown.objection_handling),
        ("pitch_value_prop", breakdown.pitch_value_prop),
        ("closing_next_steps", breakdown.closing_next_steps),
        ("communication", breakdown.communication),
        ("sentiment", breakdown.sentiment),
        ("compliance", breakdown.compliance),
    ]
    scored_dims = [(key, agg) for key, agg in dims if agg.calls_scored > 0]
    if not scored_dims:
        return [], []

    ranked = sorted(scored_dims, key=lambda kv: kv[1].agent_score, reverse=True)
    top = ranked[:2]
    bottom = list(reversed(ranked[-2:])) if len(ranked) > 2 else []

    def _note(key: str, want_max: bool) -> str:
        candidates = [(r, v) for r in records if (v := dim_call_score(r, key)) is not None]
        if not candidates:
            return "Aggregate across scored calls."
        best = max(candidates, key=lambda cv: cv[1]) if want_max else min(candidates, key=lambda cv: cv[1])
        record, _ = best
        if key == "sentiment" and record.extraction and record.extraction.sentiment:
            return f'Example: {record.extraction.sentiment.signals[0] if record.extraction.sentiment.signals else "sentiment arc " + record.extraction.sentiment.overall.value}'
        if key == "compliance" and record.compliance and record.compliance.checks:
            failing = [c for c in record.compliance.checks if c.result.value in ("fail", "detected")]
            return f"Example: {failing[0].rule}" if failing else "Example: all compliance checks passed."
        if key == "communication" and record.extraction and record.extraction.score_breakdown:
            return record.extraction.score_breakdown.communication_professionalism.evidence
        if record.extraction and record.extraction.score_breakdown and hasattr(record.extraction.score_breakdown, key):
            dim = getattr(record.extraction.score_breakdown, key)
            return dim.evidence
        return "Aggregate across scored calls."

    strengths = [StrengthWeakness(dimension=DIM_LABELS[key], score=agg.agent_score, note=_note(key, True)) for key, agg in top]
    weaknesses = [
        StrengthWeakness(dimension=DIM_LABELS[key], score=agg.agent_score, note=_note(key, False)) for key, agg in bottom
    ]
    return strengths, weaknesses


def _coaching(weaknesses: list[StrengthWeakness], closing: ClosingAgg, subject: str) -> list[CoachingRecommendation]:
    """subject is the noun phrase these read naturally with — "the agent",
    "the team", "the org" — so agent/team/org reports get grammatically
    correct text instead of one generic phrasing awkwardly stretched
    across all three."""
    recommendations = []
    if weaknesses:
        weak = weaknesses[0]
        key = next((k for k, label in DIM_LABELS.items() if label == weak.dimension), None)
        recommendations.append(
            CoachingRecommendation(
                problem=f"{weak.dimension} is {subject}'s weakest scored area, at {weak.score:.0f}/100.",
                evidence=weak.note,
                recommendation=_COACHING_TEXT.get(key, "Review the lowest-scoring calls in this dimension."),
            )
        )

    if closing.qualified_leads > 0 and closing.qualified_leads_without_next_step > 0:
        pct = closing.qualified_leads_without_next_step / closing.qualified_leads * 100.0
        recommendations.append(
            CoachingRecommendation(
                problem=f"{subject.capitalize()} fails to log a next step for {pct:.0f}% of qualified leads.",  # subject e.g. "the agent" -> "The agent fails..."
                evidence=f"{closing.qualified_leads_without_next_step} of {closing.qualified_leads} qualified leads had no call with a specific next step this period.",
                recommendation=(
                    "Always close with an explicit, time-bound next step, e.g. 'I'll send the proposal today — "
                    "can we schedule 15 minutes tomorrow at 3pm to review it?'"
                ),
            )
        )
    return recommendations


def peer_benchmark(
    avg_call_score: float | None,
    talk_time: TalkTimeAgg | None,
    conversion: ConversionAgg,
    compliance_score_pct: float | None,
    peer_records: list[CallRecord],
    leads_by_id: dict[str, Lead],
    period_start: date,
    period_end: date,
    comparison_label: str,
) -> list[BenchmarkRow]:
    """Builds the "vs. peers" comparison rows — teammates for an agent,
    other teams for a team. comparison_label is what the caller wants shown
    ("Team average", "Org average"); pass peer_records=[] for a level with
    no peer group (org), which naturally yields comparison_value=None
    throughout rather than a special code path."""
    rows = []
    other_scores = [r.overall_score for r in peer_records if r.overall_score is not None]
    peer_avg_score = statistics.fmean(other_scores) if other_scores else None
    if avg_call_score is not None:
        rows.append(
            BenchmarkRow(
                label="Overall score",
                agent_value=avg_call_score,
                comparison_value=round(peer_avg_score, 1) if peer_avg_score is not None else None,
                comparison_label=comparison_label,
            )
        )
    if talk_time is not None:
        rows.append(
            BenchmarkRow(
                label="Rep talk time %",
                agent_value=talk_time.avg_rep_talk_pct,
                comparison_value=talk_time.team_avg_rep_talk_pct,
                comparison_label=comparison_label,
            )
        )
    if compliance_score_pct is not None:
        other_compliance = [r.compliance.adherence_pct for r in peer_records if r.compliance]
        rows.append(
            BenchmarkRow(
                label="Compliance %",
                agent_value=round(compliance_score_pct, 1),
                comparison_value=round(statistics.fmean(other_compliance), 1) if other_compliance else None,
                comparison_label=comparison_label,
            )
        )
    if conversion.conversion_rate_pct is not None:
        other_leads = distinct_leads(peer_records, leads_by_id)
        other_won = sum(1 for lead in other_leads if reached_stage_in_period(lead, FunnelStage.WON, period_start, period_end))
        rows.append(
            BenchmarkRow(
                label="Conversion rate %",
                agent_value=conversion.conversion_rate_pct,
                comparison_value=round(other_won / len(other_leads) * 100.0, 1) if other_leads else None,
                comparison_label=comparison_label,
            )
        )
    return rows


# Illustrative thresholds, not derived from any benchmark data — flagged as
# such in the field description. A real deployment would split on the
# team's own median quality/conversion instead of a fixed number.
_QUALITY_THRESHOLD = 75.0
_CONVERSION_THRESHOLD = 15.0


def _quality_outcome_matrix(avg_call_score: float | None, conversion: ConversionAgg) -> QualityOutcomeQuadrant | None:
    if avg_call_score is None or conversion.conversion_rate_pct is None:
        return None
    high_quality = avg_call_score >= _QUALITY_THRESHOLD
    high_outcome = conversion.conversion_rate_pct >= _CONVERSION_THRESHOLD
    if high_quality and high_outcome:
        quadrant = "star_performer"
    elif high_quality and not high_outcome:
        quadrant = "investigate_leads"
    elif not high_quality and high_outcome:
        quadrant = "strong_but_risky"
    else:
        quadrant = "needs_coaching"
    return QualityOutcomeQuadrant(quadrant=quadrant, quality_score=avg_call_score, outcome_conversion_pct=conversion.conversion_rate_pct)


def compute_performance_metrics(
    records: list[CallRecord],
    leads_by_id: dict[str, Lead],
    period_start: date,
    period_end: date,
    prev_records: list[CallRecord],
    peer_records: list[CallRecord],
    subject: str = "the agent",
) -> PerformanceMetrics:
    """The shared engine. Every argument is pre-filtered by the caller —
    this function has no idea what population `records` represents.
    `subject` (e.g. "the agent", "the team", "the org") only affects the
    wording of generated coaching-recommendation text."""
    calls_analyzed = len(records)
    scored = [r for r in records if r.overall_score is not None]
    avg_call_score = round(statistics.fmean(r.overall_score for r in scored), 1) if scored else None

    sentiments = [SENTIMENT_SCORE[r.extraction.sentiment.overall] for r in records if r.extraction and r.extraction.sentiment]
    avg_customer_sentiment_score = round(statistics.fmean(sentiments), 1) if sentiments else None

    compliance_scores = [r.compliance.adherence_pct for r in records if r.compliance]
    compliance_score_pct = round(statistics.fmean(compliance_scores), 1) if compliance_scores else None

    prev_scored = [r.overall_score for r in prev_records if r.overall_score is not None]
    performance_trend_pct = None
    if scored and prev_scored and statistics.fmean(prev_scored) > 0:
        performance_trend_pct = round(
            (statistics.fmean(r.overall_score for r in scored) - statistics.fmean(prev_scored)) / statistics.fmean(prev_scored) * 100.0,
            1,
        )

    breakdown = _score_breakdown(records, peer_records)
    talk_time = _talk_time(records, peer_records)
    objections = _objections(records)
    closing = _closing(records, leads_by_id)
    sentiment_agg = _sentiment_agg(records)
    conversion = _conversion(records, leads_by_id, period_start, period_end)
    calls_to_close = _calls_to_close(records, leads_by_id, period_start, period_end)
    lost_reasons = _lost_reasons(records, leads_by_id)
    source_breakdown = _source_breakdown(records, leads_by_id, period_start, period_end)
    strengths, weaknesses = _strengths_and_weaknesses(breakdown, records)

    return PerformanceMetrics(
        period_start=period_start,
        period_end=period_end,
        calls_analyzed=calls_analyzed,
        calls_scored=len(scored),
        avg_call_score=avg_call_score,
        avg_customer_sentiment_score=avg_customer_sentiment_score,
        compliance_score_pct=compliance_score_pct,
        performance_trend_pct=performance_trend_pct,
        score_breakdown=breakdown,
        talk_time=talk_time,
        discovery_avg_score=breakdown.discovery_qualification.agent_score if breakdown else None,
        objections=objections,
        closing=closing,
        sentiment=sentiment_agg,
        conversion=conversion,
        calls_to_close=calls_to_close,
        lost_reasons=lost_reasons,
        source_breakdown=source_breakdown,
        quality_distribution=_quality_distribution(records),
        consistency_score=_consistency_score(records),
        trend=_trend(records, leads_by_id, period_start, period_end),
        strengths=strengths,
        weaknesses=weaknesses,
        coaching_recommendations=_coaching(weaknesses, closing, subject),
        quality_outcome_matrix=_quality_outcome_matrix(avg_call_score, conversion),
        notes=list(UNIVERSAL_NOTES),
    )
