const ORDER = ["discovery_qualification", "objection_handling", "pitch_value_prop", "closing_next_steps", "communication", "sentiment", "compliance"];

// Doc section 2's 8-dim rubric, remapped onto the ScoreBreakdown already
// computed per call — Call Discipline has no defined scoring method yet and
// is shown as excluded rather than silently dropped.
export default function AgentScoreBreakdownPanel({ breakdown, title = "Agent score" }) {
  if (!breakdown) {
    return (
      <section className="panel">
        <h3>{title}</h3>
        <p className="hint">No scored calls in this period yet.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h3>{title}</h3>
      <div className="overall-score">
        <span className="overall-score-value">{Math.round(breakdown.overall_score)}</span>
        <span className="overall-score-max">/100</span>
      </div>
      <ul className="item-list">
        {ORDER.map((key) => {
          const dim = breakdown[key];
          const statusClass = dim.team_benchmark == null || dim.agent_score >= dim.team_benchmark ? "status-good" : "status-behind";
          return (
            <li key={key} className="extracted-item score-row">
              <div className="score-row-header">
                <span>{dim.label}</span>
                <span className={`insights-value ${statusClass}`}>
                  {dim.agent_score.toFixed(0)}
                  {dim.team_benchmark != null && <span className="benchmark-value"> (team {dim.team_benchmark.toFixed(0)})</span>}
                </span>
              </div>
              <span className="item-meta">{dim.calls_scored} calls scored</span>
            </li>
          );
        })}
        <li className="extracted-item score-row">
          <div className="score-row-header">
            <span>Call discipline</span>
            <span className="insights-value">—</span>
          </div>
          <span className="item-meta">{breakdown.call_discipline_excluded_note}</span>
        </li>
      </ul>
    </section>
  );
}
