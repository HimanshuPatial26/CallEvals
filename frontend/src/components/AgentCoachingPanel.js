// Strengths/weaknesses (doc section 18) + coaching recommendations (section
// 19) + team benchmarking (section 20), grouped as "what to do about it" —
// the payoff of everything computed above.
export default function AgentCoachingPanel({ strengths, weaknesses, recommendations, benchmark }) {
  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Strengths & weaknesses</h3>
        {strengths.length === 0 && weaknesses.length === 0 ? (
          <p className="hint">Not enough scored calls yet.</p>
        ) : (
          <>
            <ul className="item-list">
              {strengths.map((s) => (
                <li key={s.dimension} className="extracted-item score-row">
                  <div className="score-row-header">
                    <span>🟢 {s.dimension}</span>
                    <span className="insights-value">{s.score.toFixed(0)}/100</span>
                  </div>
                  <span className="item-meta">{s.note}</span>
                </li>
              ))}
              {weaknesses.map((w) => (
                <li key={w.dimension} className="extracted-item score-row">
                  <div className="score-row-header">
                    <span>🔴 {w.dimension}</span>
                    <span className="insights-value">{w.score.toFixed(0)}/100</span>
                  </div>
                  <span className="item-meta">{w.note}</span>
                </li>
              ))}
            </ul>
          </>
        )}

        <h3>Team benchmark</h3>
        {benchmark.length === 0 ? (
          <p className="hint">No benchmark rows available.</p>
        ) : (
          <ul className="insights-list">
            {benchmark.map((row) => (
              <li key={row.label}>
                <span className="insights-label">{row.label}</span>
                <span className="insights-value">
                  {row.agent_value.toFixed(1)}
                  {row.comparison_value != null && (
                    <span className="benchmark-value">
                      {" "}
                      ({row.comparison_label.toLowerCase()} {row.comparison_value.toFixed(1)})
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>Coaching recommendations</h3>
        {recommendations.length === 0 ? (
          <p className="hint">Nothing flagged for this period.</p>
        ) : (
          <ul className="item-list">
            {recommendations.map((rec, i) => (
              <li key={i} className="extracted-item">
                <p className="coaching-problem">{rec.problem}</p>
                <span className="item-meta">Evidence: {rec.evidence}</span>
                <p className="coaching-recommendation-text">→ {rec.recommendation}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
