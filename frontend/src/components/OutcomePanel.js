import { useState } from "react";
import { submitOutcome } from "../api/client";

const STAGES = [
  ["untagged", "Untagged"],
  ["qualified", "Qualified"],
  ["demo_booked", "Demo booked"],
  ["proposal_sent", "Proposal sent"],
  ["won", "Won"],
  ["lost", "Lost"],
];

// The only data source behind every CRM-shaped agent-performance metric
// (conversion, qualified-lead rate, revenue) — there's no CRM integration,
// so this is a manager-recorded fact, not something the model infers.
export default function OutcomePanel({ callId, outcome, onOutcomeChange }) {
  const [stage, setStage] = useState(outcome.stage);
  const [dealSize, setDealSize] = useState(outcome.deal_size_aed ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const dealSizeAed = stage === "won" && dealSize !== "" ? Number(dealSize) : null;
      const record = await submitOutcome(callId, stage, dealSizeAed);
      onOutcomeChange(record.outcome);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="outcome-panel">
      <label className="outcome-field">
        Funnel stage
        <select value={stage} onChange={(e) => setStage(e.target.value)} disabled={saving}>
          {STAGES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {stage === "won" && (
        <label className="outcome-field">
          Deal size (AED)
          <input
            type="number"
            min="0"
            value={dealSize}
            onChange={(e) => setDealSize(e.target.value)}
            disabled={saving}
          />
        </label>
      )}
      <button onClick={handleSave} disabled={saving}>
        {saving ? "Saving…" : "Save outcome"}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
