function fmtPct(value) {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function fmtScore(value) {
  return value == null ? "—" : Math.round(value);
}

// Doc's own distinction: Conversation Performance ≠ Sales Outcome. Shown
// side by side, never blended into one number.
export default function AgentOverviewPanel({ report }) {
  return (
    <section className="panel">
      <h3>
        {report.agent_name} — {report.period_start} to {report.period_end}
      </h3>
      <div className="kpi-row">
        <div className="kpi-tile">
          <span className="kpi-value">{fmtScore(report.avg_call_score)}</span>
          <span className="kpi-label">Overall score</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">{report.calls_analyzed}</span>
          <span className="kpi-label">Calls analyzed</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">{fmtPct(report.conversion.conversion_rate_pct)}</span>
          <span className="kpi-label">Conversion rate</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">{fmtPct(report.conversion.qualified_rate_pct)}</span>
          <span className="kpi-label">Qualified-lead rate</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">{fmtScore(report.avg_customer_sentiment_score)}</span>
          <span className="kpi-label">Avg. customer sentiment</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">{fmtPct(report.compliance_score_pct)}</span>
          <span className="kpi-label">Compliance</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-value">
            {report.performance_trend_pct == null
              ? "—"
              : `${report.performance_trend_pct > 0 ? "↑" : report.performance_trend_pct < 0 ? "↓" : "→"} ${Math.abs(report.performance_trend_pct).toFixed(1)}%`}
          </span>
          <span className="kpi-label">Trend vs. prior period</span>
        </div>
      </div>
    </section>
  );
}
