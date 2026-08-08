const MATRIX_LABELS = {
  star_performer: "🟢 Star performer",
  investigate_leads: "🟡 Investigate leads/product",
  strong_but_risky: "🟠 Strong seller but risky",
  needs_coaching: "🔴 Needs coaching",
};

// Closing/funnel (doc section 11) + conversion/revenue (section 14) + the
// quality-vs-outcome matrix (section 21) — all downstream of the manually
// tagged CallOutcome, since there's no CRM integration.
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
            <span className="insights-label">Qualified</span>
            <span className="insights-value">{closing.qualified_calls}</span>
          </li>
          <li>
            <span className="insights-label">Demo booked</span>
            <span className="insights-value">{closing.demo_booked}</span>
          </li>
          <li>
            <span className="insights-label">Proposal sent</span>
            <span className="insights-value">{closing.proposals_sent}</span>
          </li>
          <li>
            <span className="insights-label">Won / Lost</span>
            <span className="insights-value">
              {closing.won} / {closing.lost}
            </span>
          </li>
        </ul>
        {closing.qualified_without_next_step > 0 && (
          <p className="item-meta">
            ⚠️ {closing.qualified_without_next_step} of {closing.qualified_calls} qualified calls ended with no logged
            next step — funnel leakage.
          </p>
        )}
      </section>

      <section className="panel">
        <h3>Conversion & revenue</h3>
        <ul className="insights-list">
          <li>
            <span className="insights-label">Tagged calls</span>
            <span className="insights-value">{conversion.tagged_calls}</span>
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
            <span className="insights-label">Lost rate</span>
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
