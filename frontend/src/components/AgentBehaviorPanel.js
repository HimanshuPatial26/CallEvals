function formatSeconds(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Talk-time (doc section 8) + discovery (section 9, aggregate-only — see the
// report's `notes`) + objections (section 10), grouped as "how the agent
// behaves on calls" rather than "what it produced."
export default function AgentBehaviorPanel({ talkTime, discoveryAvgScore, objections }) {
  return (
    <div className="call-detail-columns">
      <section className="panel">
        <h3>Talk time & discovery</h3>
        {talkTime ? (
          <ul className="insights-list">
            <li>
              <span className="insights-label">Rep talk time</span>
              <span className="insights-value">
                {talkTime.avg_rep_talk_pct.toFixed(0)}%
                {talkTime.team_avg_rep_talk_pct != null && (
                  <span className="benchmark-value"> (team {talkTime.team_avg_rep_talk_pct.toFixed(0)}%)</span>
                )}
              </span>
            </li>
            <li>
              <span className="insights-label">Customer talk time</span>
              <span className="insights-value">{talkTime.avg_customer_talk_pct.toFixed(0)}%</span>
            </li>
            <li>
              <span className="insights-label">Avg. interruptions/call</span>
              <span className="insights-value">{talkTime.avg_interruptions}</span>
            </li>
            <li>
              <span className="insights-label">Avg. questions/call</span>
              <span className="insights-value">{talkTime.avg_questions_per_call}</span>
            </li>
            <li>
              <span className="insights-label">Avg. longest monologue</span>
              <span className="insights-value">{formatSeconds(talkTime.avg_longest_monologue_seconds)}</span>
            </li>
            <li>
              <span className="insights-label">Discovery score</span>
              <span className="insights-value">{discoveryAvgScore != null ? discoveryAvgScore.toFixed(0) : "—"}/100</span>
            </li>
          </ul>
        ) : (
          <p className="hint">No talk-time data for this period.</p>
        )}
      </section>

      <section className="panel">
        <h3>Objections</h3>
        {objections.total_objections === 0 ? (
          <p className="hint">No objections tagged in this period.</p>
        ) : (
          <>
            <p className="item-meta">
              {objections.total_objections} total · {objections.overall_handling_effectiveness_pct.toFixed(0)}% handled
              {objections.weakest_category && <> · weakest: {objections.weakest_category}</>}
            </p>
            <ul className="item-list">
              {objections.by_category.map((row) => (
                <li key={row.category} className="extracted-item score-row">
                  <div className="score-row-header">
                    <span className={`objection-tag tag-${row.category}`}>{row.category}</span>
                    <span className="insights-value">{row.frequency_pct.toFixed(0)}% of objections</span>
                  </div>
                  <span className="item-meta">{row.addressed_rate_pct.toFixed(0)}% addressed</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
