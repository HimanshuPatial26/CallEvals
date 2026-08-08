// Sentiment movement (doc section 12) + buying-intent distribution with
// per-level conversion (section 13) — kept separate, same as the per-call
// panels: a positive customer isn't necessarily a ready one.
export default function AgentSentimentIntentPanel({ sentiment, conversion }) {
  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Sentiment movement</h3>
        {sentiment ? (
          <ul className="insights-list">
            <li>
              <span className="insights-label">Avg. start → end</span>
              <span className="insights-value">
                {sentiment.avg_beginning_score.toFixed(0)} → {sentiment.avg_end_score.toFixed(0)}
              </span>
            </li>
            <li>
              <span className="insights-label">Improvement</span>
              <span className="insights-value">
                {sentiment.sentiment_improvement > 0 ? "+" : ""}
                {sentiment.sentiment_improvement.toFixed(0)}
              </span>
            </li>
            <li>
              <span className="insights-label">Calls improved / deteriorated</span>
              <span className="insights-value">
                {sentiment.calls_improved} / {sentiment.calls_deteriorated}
              </span>
            </li>
            <li>
              <span className="insights-label">Positive / negative</span>
              <span className="insights-value">
                {sentiment.positive_pct.toFixed(0)}% / {sentiment.negative_pct.toFixed(0)}%
              </span>
            </li>
          </ul>
        ) : (
          <p className="hint">No sentiment data for this period.</p>
        )}
      </section>

      <section className="panel">
        <h3>Buying intent</h3>
        {conversion.intent_breakdown.length === 0 ? (
          <p className="hint">No buying-intent data for this period.</p>
        ) : (
          <ul className="item-list">
            {conversion.intent_breakdown.map((row) => (
              <li key={row.level} className="extracted-item score-row">
                <div className="score-row-header">
                  <span className={`intent-tag intent-${row.level}`}>{row.level}</span>
                  <span className="insights-value">
                    {row.count} calls ({row.pct.toFixed(0)}%)
                  </span>
                </div>
                {row.conversion_rate_pct != null && (
                  <span className="item-meta">{row.conversion_rate_pct.toFixed(0)}% converted</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
