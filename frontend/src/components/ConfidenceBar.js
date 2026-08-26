export default function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100);
  return (
    <span className="confidence">
      <span className="confidence-track">
        <span className="confidence-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="confidence-value">{pct}%</span>
    </span>
  );
}
