// Call quality distribution (doc section 15) + consistency score (section
// 16) + weekly trend (section 17). Consistency answers a different question
// than the average: "how reliably good," not "how good."
export default function AgentQualityTrendPanel({ distribution, consistency, trend }) {
  const maxCount = Math.max(1, ...distribution.map((b) => b.count));

  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Quality distribution & consistency</h3>
        {distribution.length === 0 ? (
          <p className="hint">No scored calls in this period.</p>
        ) : (
          <>
            <ul className="quality-distribution">
              {distribution.map((bucket) => (
                <li key={bucket.range_label}>
                  <span className="quality-bucket-label">{bucket.range_label}</span>
                  <span className="quality-bar-track">
                    <span className="quality-bar-fill" style={{ width: `${(bucket.count / maxCount) * 100}%` }} />
                  </span>
                  <span className="quality-bucket-pct">{bucket.pct.toFixed(0)}%</span>
                </li>
              ))}
            </ul>
            <p className="item-meta">
              Consistency score: {consistency != null ? consistency.toFixed(0) : "—"}/100 — higher means more stable
              call-to-call quality, not just a higher average.
            </p>
          </>
        )}
      </section>

      <section className="panel">
        <h3>Weekly trend</h3>
        {trend.length === 0 ? (
          <p className="hint">No calls in this period.</p>
        ) : (
          <table className="trend-table">
            <thead>
              <tr>
                <th>Week</th>
                <th>Calls</th>
                <th>Avg. score</th>
                <th>Conversion</th>
              </tr>
            </thead>
            <tbody>
              {trend.map((point) => (
                <tr key={point.period_label}>
                  <td>{point.period_label}</td>
                  <td>{point.calls}</td>
                  <td>{point.avg_score != null ? point.avg_score.toFixed(0) : "—"}</td>
                  <td>{point.conversion_rate_pct != null ? `${point.conversion_rate_pct.toFixed(0)}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
