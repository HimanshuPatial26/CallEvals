import { useEffect, useState } from "react";
import { getLead } from "../api/client";
import StatusChip from "./StatusChip";
import { fmtDateShort, fmtTime } from "../utils/format";

export default function LeadModal({ leadId, onClose, onOpenCall }) {
  const [lead, setLead] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getLead(leadId)
      .then((data) => !cancelled && setLead(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [leadId]);

  return (
    <div className="ce-modal-overlay" onClick={onClose}>
      <div className="ce-modal ce-modal-lg" onClick={(e) => e.stopPropagation()}>
        {error && <div className="ce-modal-body"><span className="error">{error}</span></div>}
        {!error && !lead && <div className="ce-modal-body"><span className="hint">Loading…</span></div>}
        {lead && (
          <>
            <div className="ce-modal-header">
              <div className="ce-modal-header-titles">
                <div className="ce-call-title-row">
                  <span className="ce-lead-name" style={{ fontSize: 17 }}>{lead.name}</span>
                  <span className="ce-chip">{lead.stage}</span>
                </div>
                <span className="ce-lead-phone">
                  {lead.phone}
                  {lead.unit ? ` · ${lead.unit}` : ""}
                  {lead.budget ? ` · ${lead.budget}` : ""}
                </span>
              </div>
              <button type="button" className="ce-modal-close" onClick={onClose}>✕</button>
            </div>

            {lead.open_next_step && (
              <div className="ce-modal-subheader">
                <span style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                  <span className="ce-shape-caps">OPEN NEXT STEP</span>
                  <span style={{ fontSize: 13, color: "var(--ce-text-row)" }}>{lead.open_next_step.description}</span>
                </span>
                <span className="ce-shape-value" style={{ marginLeft: "auto" }}>{lead.open_next_step.due || "no date stated"}</span>
              </div>
            )}

            <div style={{ padding: "14px 18px 6px", display: "flex", alignItems: "baseline", gap: 10 }}>
              <span className="ce-card-title">Call history</span>
              <span className="ce-card-tag">{lead.calls.length} calls</span>
            </div>

            <div className="ce-modal-list">
              {lead.calls.length === 0 && <span className="hint">No calls recorded for this lead yet.</span>}
              {lead.calls.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className="ce-modal-list-row"
                  onClick={() => c.status === "done" && onOpenCall(c.id)}
                  disabled={c.status !== "done"}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0, flex: 1 }}>
                    <div className="ce-call-title-row">
                      <span className="ce-call-filename" style={{ fontSize: 11 }}>{c.filename}</span>
                      <StatusChip status={c.status} />
                    </div>
                    <span className="ce-call-submeta" style={{ textWrap: "pretty" }}>{c.summary || "Not analysed yet."}</span>
                  </div>
                  <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flex: "none" }}>
                    <span className="ce-transcript-ts">{fmtDateShort(c.created_at)}</span>
                    <span className="ce-shape-value">{c.duration ? fmtTime(c.duration) : "—"}</span>
                  </span>
                  {c.status === "done" && <span style={{ color: "var(--ce-accent)" }}>→</span>}
                </button>
              ))}
              <span className="hint">Calls recorded before CallEvals was linked to this lead won't appear here.</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
