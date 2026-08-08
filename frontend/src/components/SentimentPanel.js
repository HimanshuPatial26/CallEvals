// Analytics doc section 11: "sentiment should be treated as an AI-derived
// signal rather than a definitive measurement of emotion" — confidence is
// always shown alongside the read, never hidden.
export default function SentimentPanel({ sentiment }) {
  if (!sentiment) {
    return <p className="hint">No sentiment read for this call.</p>;
  }

  return (
    <div>
      <p className="sentiment-arc">
        <span className={`sentiment-tag sentiment-${sentiment.beginning}`}>{sentiment.beginning}</span>
        <span className="sentiment-arrow">→</span>
        <span className={`sentiment-tag sentiment-${sentiment.middle}`}>{sentiment.middle}</span>
        <span className="sentiment-arrow">→</span>
        <span className={`sentiment-tag sentiment-${sentiment.end}`}>{sentiment.end}</span>
      </p>
      <p className="item-meta">
        Overall: <span className={`sentiment-tag sentiment-${sentiment.overall}`}>{sentiment.overall}</span> ·
        confidence {(sentiment.confidence * 100).toFixed(0)}%
      </p>
      {sentiment.signals.length > 0 && (
        <ul className="insights-list">
          {sentiment.signals.map((signal, i) => (
            <li key={i}>
              <span className="insights-label">{signal}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
