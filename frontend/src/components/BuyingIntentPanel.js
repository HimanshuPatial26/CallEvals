// Analytics doc section 12: kept deliberately separate from sentiment — a
// positive customer is not necessarily ready to buy.
export default function BuyingIntentPanel({ buyingIntent }) {
  if (!buyingIntent) {
    return <p className="hint">No buying-intent read for this call.</p>;
  }

  return (
    <div>
      <p>
        <span className={`intent-tag intent-${buyingIntent.level}`}>{buyingIntent.level} intent</span>
        <span className="item-meta"> · confidence {(buyingIntent.confidence * 100).toFixed(0)}%</span>
      </p>
      <p className="item-meta">Follow-up: {buyingIntent.follow_up_priority}</p>
      {buyingIntent.signals.length > 0 && (
        <ul className="insights-list">
          {buyingIntent.signals.map((signal, i) => (
            <li key={i}>
              <span className="insights-label">"{signal}"</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
