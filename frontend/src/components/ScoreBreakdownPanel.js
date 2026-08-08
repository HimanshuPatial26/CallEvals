const DIMENSION_LABELS = {
  opening_rapport: "Opening & rapport",
  discovery_qualification: "Discovery & qualification",
  active_listening: "Active listening",
  pitch_value_prop: "Pitch & value proposition",
  objection_handling: "Objection handling",
  communication_professionalism: "Communication & professionalism",
  closing_next_steps: "Closing & next steps",
};

// Every dimension carries its own evidence line (analytics doc section 19:
// "every score should be supported by transcript evidence rather than being
// a black-box number") — shown here, not hidden behind a tooltip.
export default function ScoreBreakdownPanel({ scoreBreakdown, compliance, overallScore }) {
  if (!scoreBreakdown) {
    return <p className="hint">No score breakdown for this call.</p>;
  }

  const complianceScore = compliance ? (compliance.adherence_pct / 100) * 5 : null;

  return (
    <div className="score-breakdown">
      <div className="overall-score">
        <span className="overall-score-value">{overallScore != null ? Math.round(overallScore) : "—"}</span>
        <span className="overall-score-max">/100</span>
      </div>
      <ul className="item-list">
        {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
          const dim = scoreBreakdown[key];
          if (!dim) return null;
          return (
            <li key={key} className="extracted-item score-row">
              <div className="score-row-header">
                <span>{label}</span>
                <span className="insights-value">
                  {dim.score}/{dim.max_score}
                </span>
              </div>
              <span className="item-meta">{dim.evidence}</span>
            </li>
          );
        })}
        <li className="extracted-item score-row">
          <div className="score-row-header">
            <span>Compliance / process adherence</span>
            <span className="insights-value">{complianceScore != null ? complianceScore.toFixed(1) : "—"}/5</span>
          </div>
          <span className="item-meta">Computed from the compliance checklist below, not model-judged.</span>
        </li>
      </ul>
    </div>
  );
}
