import { useEffect, useState } from "react";
import { getLead, setLeadStage, updateLead } from "../api/client";

const STAGES = [
  ["untagged", "Untagged"],
  ["qualified", "Qualified"],
  ["demo_booked", "Demo booked"],
  ["proposal_sent", "Proposal sent"],
  ["won", "Won"],
  ["lost", "Lost"],
];

const LOST_REASONS = [
  ["price", "Price"],
  ["timing", "Timing"],
  ["competitor", "Competitor"],
  ["financing", "Financing fell through"],
  ["unresponsive", "Went unresponsive"],
  ["not_qualified", "Not qualified"],
  ["changed_mind", "Changed mind"],
  ["other", "Other"],
];

const SOURCE_SUGGESTIONS = ["Website", "Referral", "Walk-in", "Portal", "Social media", "Cold call"];

// Stage editing lives here as a convenience while reviewing a call, but it
// writes through to the Lead (POST /api/leads/{id}/stage), not the call —
// the call-level outcome tag from the previous pass is gone. A lead can
// have many calls; this is the only one of them that gets a stage.
export default function LeadPanel({ leadId }) {
  const [lead, setLead] = useState(null);
  const [stage, setStage] = useState(null);
  const [dealSize, setDealSize] = useState("");
  const [lostReason, setLostReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const [source, setSource] = useState("");
  const [savingSource, setSavingSource] = useState(false);

  useEffect(() => {
    setLead(null);
    setError(null);
    getLead(leadId)
      .then((data) => {
        setLead(data);
        setStage(data.stage);
        setDealSize(data.deal_size_aed ?? "");
        setLostReason(data.lost_reason ?? "");
        setSource(data.source ?? "");
      })
      .catch((err) => setError(err.message));
  }, [leadId]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const dealSizeAed = stage === "won" && dealSize !== "" ? Number(dealSize) : null;
      const reason = stage === "lost" && lostReason !== "" ? lostReason : null;
      const updated = await setLeadStage(leadId, stage, dealSizeAed, reason);
      setLead((prev) => ({
        ...prev,
        stage: updated.stage,
        deal_size_aed: updated.deal_size_aed,
        lost_reason: updated.lost_reason,
        stage_history: updated.stage_history,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveSource() {
    setSavingSource(true);
    setError(null);
    try {
      const updated = await updateLead(leadId, { source: source.trim() || null });
      setLead((prev) => ({ ...prev, source: updated.source }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingSource(false);
    }
  }

  if (error && !lead) {
    return <p className="error">{error}</p>;
  }

  if (!lead) {
    return <p className="hint">Loading lead…</p>;
  }

  return (
    <div>
      <p className="item-meta">
        {lead.display_name}
        {lead.phone ? ` · ${lead.phone}` : ""}
        {lead.calls ? ` · ${lead.calls.length} call${lead.calls.length === 1 ? "" : "s"} on record` : ""}
      </p>
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
            <input type="number" min="0" value={dealSize} onChange={(e) => setDealSize(e.target.value)} disabled={saving} />
          </label>
        )}
        {stage === "lost" && (
          <label className="outcome-field">
            Lost reason
            <select value={lostReason} onChange={(e) => setLostReason(e.target.value)} disabled={saving}>
              <option value="">Not recorded</option>
              {LOST_REASONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        )}
        <button onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : "Save stage"}
        </button>
      </div>

      <div className="outcome-panel">
        <label className="outcome-field">
          Source
          <input
            type="text"
            list="lead-source-suggestions"
            placeholder="Website, Referral, …"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            disabled={savingSource}
          />
          <datalist id="lead-source-suggestions">
            {SOURCE_SUGGESTIONS.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </label>
        <button onClick={handleSaveSource} disabled={savingSource}>
          {savingSource ? "Saving…" : "Save source"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
