// Analytics doc section 20, reduced to fields a manager can act on directly —
// no "recommended training module" without a training-content library to
// point at.
const ROWS = [
  ["Top strength", "top_strength"],
  ["Top weakness", "top_weakness"],
  ["Behavior to stop", "behavior_to_stop"],
  ["Behavior to continue", "behavior_to_continue"],
  ["Behavior to start", "behavior_to_start"],
];

export default function CoachingPanel({ coaching }) {
  if (!coaching) {
    return <p className="hint">No coaching notes for this call.</p>;
  }

  return (
    <ul className="insights-list coaching-list">
      {ROWS.map(([label, key]) => (
        <li key={key}>
          <span className="insights-label">{label}</span>
          <span className="insights-value coaching-value">{coaching[key]}</span>
        </li>
      ))}
    </ul>
  );
}
