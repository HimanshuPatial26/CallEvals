const RESULT_LABELS = {
  pass: "Pass",
  fail: "Fail",
  warning: "Warning",
  detected: "Detected",
  not_detected: "Not detected",
  not_applicable: "N/A",
};

// Rule-based, not LLM-judged (app/compliance.py) — deterministic pass/fail
// against a configurable phrase list, per analytics doc section 14.
export default function ComplianceChecklist({ compliance }) {
  if (!compliance) {
    return <p className="hint">No compliance checks for this call.</p>;
  }

  return (
    <div>
      <p className="item-meta">Adherence: {compliance.adherence_pct.toFixed(0)}%</p>
      <ul className="item-list">
        {compliance.checks.map((check, i) => (
          <li key={i} className="extracted-item score-row">
            <div className="score-row-header">
              <span>{check.rule}</span>
              <span className={`compliance-tag compliance-${check.result}`}>{RESULT_LABELS[check.result]}</span>
            </div>
            {check.evidence && <span className="item-meta">{check.evidence}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
