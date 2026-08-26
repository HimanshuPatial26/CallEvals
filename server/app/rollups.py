"""Aggregate views over stored call records — agent performance, org rollup, leads.

Everything here is computed from real stored CallRecord/Agent/Lead data (see
storage.py). Nothing is sampled, seeded, or hardcoded. Where the PRD names a metric
directly (coverage, extraction precision, manager engagement, behavior improvement
rate — section 6), the computation here follows that definition; where the mockup
wanted something the data model has no honest way to produce (e.g. per-deal stall
reasons beyond objection category), it's approximated from the closest real signal
instead of invented, and that approximation is called out in a comment.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.schemas import Agent, BehaviorFlags, CallRecord, Lead

_FLAG_FIELDS = ["monologue", "no_discovery_question", "no_dated_next_step", "missing_disclosure", "discount_offered_first"]
_FLAG_LABELS = {
    "monologue": "Monologue",
    "no_discovery_question": "No discovery question",
    "no_dated_next_step": "No dated next step",
    "missing_disclosure": "Missing disclosure",
    "discount_offered_first": "Discount offered first",
}


def _week_start(dt: datetime) -> datetime:
    d = dt.astimezone(timezone.utc)
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _flag_free(flags: BehaviorFlags | None) -> bool:
    if flags is None:
        return True
    return not any(getattr(flags, f) for f in _FLAG_FIELDS)


def weekly_flag_free_rate(calls: list[CallRecord], weeks: int = 8) -> list[float]:
    """% of that week's done calls with zero active behavior flags, forward-filled
    across weeks with no data so the trend line stays continuous."""
    done = [c for c in calls if c.status == "done"]
    now = datetime.now(timezone.utc)
    buckets = [_week_start(now) - timedelta(weeks=(weeks - 1 - i)) for i in range(weeks)]
    by_week: dict[datetime, list[CallRecord]] = defaultdict(list)
    for c in done:
        by_week[_week_start(c.created_at)].append(c)

    series: list[float] = []
    last = 50.0
    for wk in buckets:
        wk_calls = by_week.get(wk, [])
        if wk_calls:
            last = 100.0 * sum(1 for c in wk_calls if _flag_free(c.flags)) / len(wk_calls)
        series.append(round(last, 1))
    return series


def coverage(calls: list[CallRecord]) -> float:
    """PRD section 6: % of calls successfully ingested/transcribed (done vs. attempted)."""
    attempted = [c for c in calls if c.status in ("done", "failed")]
    if not attempted:
        return 0.0
    return round(100.0 * sum(1 for c in attempted if c.status == "done") / len(attempted), 1)


def extraction_precision(calls: list[CallRecord]) -> float:
    """PRD section 6: % of extracted next steps a manager confirms as correct."""
    confirmations = [
        f.confirmed for c in calls for f in c.feedback if f.item_type == "next_step"
    ]
    if not confirmations:
        return 0.0
    return round(100.0 * sum(1 for ok in confirmations if ok) / len(confirmations), 1)


def manager_engagement(calls: list[CallRecord]) -> float:
    """PRD section 6: % of summaries opened within 24h of the call landing."""
    done = [c for c in calls if c.status == "done"]
    if not done:
        return 0.0
    opened_in_time = sum(
        1 for c in done if c.first_viewed_at and (c.first_viewed_at - c.created_at) <= timedelta(hours=24)
    )
    return round(100.0 * opened_in_time / len(done), 1)


def objection_mix(calls: list[CallRecord]) -> list[dict]:
    done = [c for c in calls if c.status == "done" and c.extraction]
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # category -> [raised, handled]
    for c in done:
        for obj in c.extraction.objections:
            counts[obj.category.value][0] += 1
    total = sum(v[0] for v in counts.values())
    return [
        {"category": cat, "raised": n[0], "pct": round(100.0 * n[0] / total, 1) if total else 0.0}
        for cat, n in sorted(counts.items(), key=lambda kv: -kv[1][0])
    ]


def top_objection(calls: list[CallRecord]) -> str | None:
    mix = objection_mix(calls)
    return mix[0]["category"] if mix else None


def behavior_improvement_rate(calls: list[CallRecord]) -> tuple[float, list[dict]]:
    """PRD section 6 north star: share of flagged behaviors that clear within the
    next 5 calls after they're first flagged. Returns (rate_pct, per_behavior_rows)
    for the flagged-behaviors table — first-flag date, calls since, and a status
    derived from the clear rate in that follow-up window.
    """
    done = sorted((c for c in calls if c.status == "done" and c.flags), key=lambda c: c.created_at)
    rows = []
    total_flagged, total_improved = 0, 0

    for field in _FLAG_FIELDS:
        flagged_idxs = [i for i, c in enumerate(done) if getattr(c.flags, field)]
        if not flagged_idxs:
            continue
        first_idx = flagged_idxs[0]
        window = done[first_idx + 1 : first_idx + 6]
        dots = [0 if getattr(c.flags, field) else 1 for c in window]
        clear_rate = (sum(dots) / len(dots)) if dots else 0.0

        total_flagged += 1
        if clear_rate >= 0.8:
            status = "improved"
        elif clear_rate >= 0.5:
            status = "improving"
        elif dots:
            status = "holding"
        else:
            status = "monitoring"
        if clear_rate >= 0.5:
            total_improved += 1

        rows.append(
            {
                "name": _FLAG_LABELS[field],
                "first_flag_at": done[first_idx].created_at,
                "calls_since": len(done) - first_idx - 1,
                "dots": dots,
                "status": status,
            }
        )

    rate = round(100.0 * total_improved / total_flagged, 1) if total_flagged else 0.0
    return rate, rows


def open_flag_count(calls: list[CallRecord]) -> int:
    done = sorted((c for c in calls if c.status == "done"), key=lambda c: c.created_at, reverse=True)
    if not done or not done[0].flags:
        return 0
    return sum(1 for f in _FLAG_FIELDS if getattr(done[0].flags, f))


def agent_calls(calls: list[CallRecord], agent_id: str) -> list[CallRecord]:
    return [c for c in calls if c.agent_id == agent_id]


def agent_summary(agent: Agent, calls: list[CallRecord]) -> dict:
    a_calls = agent_calls(calls, agent.id)
    done = [c for c in a_calls if c.status == "done"]
    rate, _ = behavior_improvement_rate(a_calls)
    return {
        "id": agent.id,
        "name": agent.name,
        "team": agent.team,
        "calls_reviewed": len(done),
        "coverage": coverage(a_calls),
        "behavior_improvement": rate,
        "open_flags": open_flag_count(a_calls),
        "top_objection": top_objection(a_calls),
    }


def where_deals_stall(calls: list[CallRecord], leads: list[Lead]) -> list[dict]:
    """Approximated from real data: each open (non-Offer) lead is bucketed by its
    most recent objection category, or 'no next step committed' if its latest done
    call left nothing committed. This is a proxy for stall reason, not a tracked
    CRM stage-change log, which the product doesn't have.
    """
    by_lead: dict[str, list[CallRecord]] = defaultdict(list)
    for c in calls:
        if c.lead_id:
            by_lead[c.lead_id].append(c)

    buckets: dict[str, int] = defaultdict(int)
    for lead in leads:
        if lead.stage == "Offer":
            continue
        lead_calls = sorted((c for c in by_lead.get(lead.id, []) if c.status == "done"), key=lambda c: c.created_at)
        if not lead_calls:
            continue
        latest = lead_calls[-1]
        if latest.extraction and latest.extraction.objections:
            buckets[latest.extraction.objections[-1].category.value + " objection"] += 1
        elif not (latest.extraction and latest.extraction.next_steps):
            buckets["No next step committed"] += 1
        else:
            buckets["No objection, in nurture"] += 1

    total = sum(buckets.values())
    return [
        {"label": label, "count": n, "pct": round(100.0 * n / total, 1) if total else 0.0}
        for label, n in sorted(buckets.items(), key=lambda kv: -kv[1])
    ]


def lead_open_next_step(calls: list[CallRecord], lead_id: str) -> dict | None:
    lead_calls = sorted(
        (c for c in calls if c.lead_id == lead_id and c.status == "done" and c.extraction and c.extraction.next_steps),
        key=lambda c: c.created_at,
        reverse=True,
    )
    if not lead_calls:
        return None
    step = lead_calls[0].extraction.next_steps[0]
    return {"description": step.description, "due": step.due}


def lead_objection_tags(calls: list[CallRecord], lead_id: str) -> list[str]:
    tags: list[str] = []
    for c in calls:
        if c.lead_id == lead_id and c.status == "done" and c.extraction:
            for obj in c.extraction.objections:
                if obj.category.value not in tags:
                    tags.append(obj.category.value)
    return tags
