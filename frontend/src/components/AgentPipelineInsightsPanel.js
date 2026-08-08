const LOST_REASON_LABELS = {
  price: "Price",
  timing: "Timing",
  competitor: "Competitor",
  financing: "Financing fell through",
  unresponsive: "Went unresponsive",
  not_qualified: "Not qualified",
  changed_mind: "Changed mind",
  other: "Other",
};

// Calls-to-close (doc: "how many touches does it take" — ROADMAP.md C2) +
// lost reasons (C3) + lead source conversion (C4), grouped together since
// they're all "why the funnel looks the way it does" diagnostics, same
// spirit as AgentFunnelPanel's closing/conversion pairing one level up.
export default function AgentPipelineInsightsPanel({ callsToClose, lostReasons, sourceBreakdown }) {
  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Calls to close</h3>
        {callsToClose.calls_per_lead_distribution.length === 0 ? (
          <p className="hint">No leads touched this period.</p>
        ) : (
          <>
            <ul className="insights-list">
              <li>
                <span className="insights-label">Avg. calls to close</span>
                <span className="insights-value">{callsToClose.avg_calls_to_close ?? "—"}</span>
              </li>
              <li>
                <span className="insights-label">Avg. days to close</span>
                <span className="insights-value">{callsToClose.avg_days_to_close ?? "—"}</span>
              </li>
            </ul>
            <p className="item-meta">
              Calls per lead ({callsToClose.won_leads_measured} won lead{callsToClose.won_leads_measured === 1 ? "" : "s"} measured):
            </p>
            <ul className="quality-distribution">
              {callsToClose.calls_per_lead_distribution.map((bucket) => (
                <li key={bucket.range_label}>
                  <span className="quality-bucket-label">{bucket.range_label}</span>
                  <span className="quality-bar-track">
                    <span className="quality-bar-fill" style={{ width: `${bucket.pct}%` }} />
                  </span>
                  <span className="quality-bucket-pct">{bucket.pct.toFixed(0)}%</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="panel">
        <h3>Lost reasons</h3>
        {lostReasons.by_reason.length === 0 ? (
          <p className="hint">No lost leads with a reason recorded yet.</p>
        ) : (
          <ul className="item-list">
            {lostReasons.by_reason.map((row) => (
              <li key={row.reason} className="extracted-item score-row">
                <div className="score-row-header">
                  <span>{LOST_REASON_LABELS[row.reason] || row.reason}</span>
                  <span className="insights-value">
                    {row.count} ({row.pct.toFixed(0)}%)
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>Lead source</h3>
        {sourceBreakdown.by_source.length === 0 ? (
          <p className="hint">No leads touched this period.</p>
        ) : (
          <ul className="item-list">
            {sourceBreakdown.by_source.map((row) => (
              <li key={row.source} className="extracted-item score-row">
                <div className="score-row-header">
                  <span>{row.source}</span>
                  <span className="insights-value">
                    {row.leads_touched} lead{row.leads_touched === 1 ? "" : "s"}
                  </span>
                </div>
                {row.conversion_rate_pct != null && <span className="item-meta">{row.conversion_rate_pct.toFixed(0)}% converted</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
