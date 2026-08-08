import Sparkline from "./Sparkline";

function fmtPct(value) {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function fmtScore(value) {
  return value == null ? "—" : Math.round(value);
}

function weeklySeries(trend, key) {
  const values = (trend || []).map((t) => t[key]).filter((v) => v != null);
  return values.length >= 2 ? values : null;
}

// Doc's own distinction: Conversation Performance ≠ Sales Outcome. Shown
// side by side, never blended into one number. Sparklines only appear on
// the three KPIs that actually have a per-week series in report.trend
// (avg_score, calls, conversion_rate_pct) -- the other tiles have no
// underlying weekly breakdown, so no fabricated trend line for them.
export default function AgentOverviewPanel({ report, title }) {
  const scoreTrend = weeklySeries(report.trend, "avg_score");
  const callsTrend = weeklySeries(report.trend, "calls");
  const conversionTrend = weeklySeries(report.trend, "conversion_rate_pct");

  return (
    <section className="panel">
      <h3>{title ?? `${report.agent_name} — ${report.period_start} to ${report.period_end}`}</h3>
      <div className="kpi-row">
        <div className="kpi-tile">
          <span className="kpi-label">Overall score</span>
          <span className="kpi-value">{fmtScore(report.avg_call_score)}</span>
          {scoreTrend && (
            <div className="kpi-tile-spark">
              <Sparkline points={scoreTrend} tint="#c084fc" />
            </div>
          )}
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Calls analyzed</span>
          <span className="kpi-value">{report.calls_analyzed}</span>
          {callsTrend && (
            <div className="kpi-tile-spark">
              <Sparkline points={callsTrend} tint="#67e8f9" />
            </div>
          )}
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Conversion rate</span>
          <span className="kpi-value">{fmtPct(report.conversion.conversion_rate_pct)}</span>
          {conversionTrend && (
            <div className="kpi-tile-spark">
              <Sparkline points={conversionTrend} tint="#4ade80" />
            </div>
          )}
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Qualified-lead rate</span>
          <span className="kpi-value">{fmtPct(report.conversion.qualified_rate_pct)}</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Avg. customer sentiment</span>
          <span className="kpi-value">{fmtScore(report.avg_customer_sentiment_score)}</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Compliance</span>
          <span className="kpi-value">{fmtPct(report.compliance_score_pct)}</span>
        </div>
        <div className="kpi-tile">
          <span className="kpi-label">Trend vs. prior period</span>
          <span className="kpi-value">
            {report.performance_trend_pct == null
              ? "—"
              : `${report.performance_trend_pct > 0 ? "↑" : report.performance_trend_pct < 0 ? "↓" : "→"} ${Math.abs(report.performance_trend_pct).toFixed(1)}%`}
          </span>
        </div>
      </div>
    </section>
  );
}
