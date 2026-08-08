const MATRIX_LABELS = {
  star_performer: "🟢 Star performer",
  investigate_leads: "🟡 Investigate leads/product",
  strong_but_risky: "🟠 Strong seller but risky",
  needs_coaching: "🔴 Needs coaching",
};

// Closing/funnel (doc section 11) + conversion/revenue (section 14) + the
// quality-vs-outcome matrix (section 21) — all downstream of manually
// tagged Lead.stage (ROADMAP.md C1), since there's no CRM integration.
// closing.* are current-stage snapshots of leads touched this period;
// conversion.conversion_rate_pct is period-scoped (only leads that actually
// transitioned to won during this period) — the two numbers can legitimately
// disagree, see the backend docstrings.
export default function AgentFunnelPanel({ closing, conversion, matrix }) {
  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Closing & funnel</h3>
        <ul className="insights-list">
          <li>
            <span className="insights-label">Calls with a next step</span>
            <span className="insights-value">{closing.calls_with_next_step}</span>
          </li>
          <li>
            <span className="insights-label">Qualified leads</span>
            <span className="insights-value">{closing.qualified_leads}</span>
          </li>
          <li>
            <span className="insights-label">Demo booked</span>
            <span className="insights-value">{closing.demo_booked_leads}</span>
          </li>
          <li>
            <span className="insights-label">Proposal sent</span>
            <span className="insights-value">{closing.proposals_sent_leads}</span>
          </li>
          <li>
            <span className="insights-label">Won / Lost (current)</span>
            <span className="insights-value">
              {closing.won_leads} / {closing.lost_leads}
            </span>
          </li>
        </ul>
        {closing.qualified_leads_without_next_step > 0 && (
          <p className="item-meta">
            ⚠️ {closing.qualified_leads_without_next_step} of {closing.qualified_leads} qualified leads had no call
            with a logged next step this period — funnel leakage.
          </p>
        )}
      </section>

      <section className="panel">
        <h3>Conversion & revenue</h3>
        <ul className="insights-list">
          <li>
            <span className="insights-label">Leads touched</span>
            <span className="insights-value">{conversion.leads_touched}</span>
          </li>
          <li>
            <span className="insights-label">Leads tagged</span>
            <span className="insights-value">{conversion.leads_tagged}</span>
          </li>
          <li>
            <span className="insights-label">Revenue (AED)</span>
            <span className="insights-value">{conversion.revenue_aed != null ? conversion.revenue_aed.toLocaleString() : "—"}</span>
          </li>
          <li>
            <span className="insights-label">Avg. deal size (AED)</span>
            <span className="insights-value">
              {conversion.avg_deal_size_aed != null ? conversion.avg_deal_size_aed.toLocaleString() : "—"}
            </span>
          </li>
          <li>
            <span className="insights-label">Lost rate (this period)</span>
            <span className="insights-value">{conversion.lost_rate_pct != null ? `${conversion.lost_rate_pct.toFixed(0)}%` : "—"}</span>
          </li>
        </ul>
        {matrix && (
          <p className="item-meta">
            Quality vs. outcome: {MATRIX_LABELS[matrix.quadrant]} (score {matrix.quality_score.toFixed(0)}, conversion{" "}
            {matrix.outcome_conversion_pct.toFixed(1)}%)
          </p>
        )}
      </section>
    </div>
  );
}
