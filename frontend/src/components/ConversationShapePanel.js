import { fmtTime } from "../utils/format";

function sentimentPoints(curve) {
  if (!curve || curve.length === 0) return "";
  return curve
    .map((v, i) => {
      const x = (i / (curve.length - 1)) * 100;
      const y = 17 - v * 15;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function ConversationShapePanel({ shape }) {
  if (!shape) {
    return (
      <div className="ce-card">
        <div className="ce-card-header">
          <span className="ce-card-title">Conversation shape</span>
        </div>
        <div className="ce-unavailable">Not available for this call.</div>
      </div>
    );
  }

  const talkPct = Math.round(shape.talk_ratio_rep * 100);
  const talkColor = talkPct > 75 ? "var(--ce-danger)" : "var(--ce-accent)";

  return (
    <div className="ce-card">
      <div className="ce-card-header">
        <span className="ce-card-title">Conversation shape</span>
      </div>
      <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="ce-shape-block">
          <div className="ce-shape-label-row">
            <span className="ce-shape-caps">TALK RATIO</span>
            <span className="ce-shape-value" style={{ color: talkColor }}>{talkPct}% rep</span>
          </div>
          <div className="ce-talk-track">
            <span className="ce-talk-track-rep" style={{ width: `${talkPct}%`, background: talkColor }} />
            <span className="ce-talk-track-customer" />
          </div>
          <div className="ce-shape-endcaps">
            <span>rep</span>
            <span>customer</span>
          </div>
        </div>

        <div className="ce-shape-block">
          <div className="ce-shape-label-row">
            <span className="ce-shape-caps">SENTIMENT</span>
            <span className="ce-shape-value" style={{ color: "var(--ce-text-hint)" }}>{shape.sentiment_label}</span>
          </div>
          {shape.sentiment_curve.length > 0 ? (
            <svg viewBox="0 0 100 34" preserveAspectRatio="none" className="ce-sentiment-svg">
              <line x1="0" y1="17" x2="100" y2="17" stroke="var(--ce-border)" strokeWidth="0.5" />
              <polyline
                points={sentimentPoints(shape.sentiment_curve)}
                fill="none"
                stroke="var(--ce-accent)"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          ) : (
            <span className="hint">Not enough speaker-separated audio to estimate.</span>
          )}
          <span className="hint">Keyword heuristic, not a validated model — shown as context, never scored.</span>
        </div>

        <div className="ce-shape-stats">
          <div className="ce-shape-stat-row">
            <span className="ce-shape-stat-label">Questions asked</span>
            <span className="ce-shape-stat-value">{shape.questions_asked_rep}</span>
          </div>
          <div className="ce-shape-stat-row">
            <span className="ce-shape-stat-label">Longest rep turn</span>
            <span className="ce-shape-stat-value">{fmtTime(shape.longest_rep_turn)}</span>
          </div>
          <div className="ce-shape-stat-row">
            <span className="ce-shape-stat-label">Words / minute</span>
            <span className="ce-shape-stat-value">{Math.round(shape.words_per_minute)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
