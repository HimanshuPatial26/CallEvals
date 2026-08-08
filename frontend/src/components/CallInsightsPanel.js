function formatSeconds(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Deliberately plain numbers, no color-coding, no "good/bad" framing, no
// combined score — each stat is a factual readout a manager interprets
// themselves, matching the PRD's rejection of composite call scoring.
export default function CallInsightsPanel({ insights }) {
  if (!insights) {
    return (
      <p className="hint">
        No speaker-level insights for this call — the transcript doesn't distinguish rep from customer
        (mono audio without diarization).
      </p>
    );
  }

  const repSharePct = Math.round(insights.rep_talk_time_ratio * 100);

  return (
    <ul className="insights-list">
      <li>
        <span className="insights-label">Rep talk time</span>
        <span className="insights-value">{repSharePct}%</span>
      </li>
      <li>
        <span className="insights-label">Longest rep monologue</span>
        <span className="insights-value">{formatSeconds(insights.longest_rep_monologue_seconds)}</span>
      </li>
      <li>
        <span className="insights-label">Questions asked (rep / customer)</span>
        <span className="insights-value">
          {insights.rep_questions_asked} / {insights.customer_questions_asked}
        </span>
      </li>
      <li>
        <span className="insights-label">Interruptions</span>
        <span className="insights-value">{insights.interruption_count}</span>
      </li>
    </ul>
  );
}
