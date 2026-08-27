import { useEffect, useState } from "react";
import { getCall } from "../api/client";
import StatusChip from "./StatusChip";
import { fmtTime } from "../utils/format";

export default function CallPreviewModal({ callId, onClose, onOpenFull }) {
  const [call, setCall] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!callId) return;
    setCall(null);
    setError(null);
    let cancelled = false;
    getCall(callId)
      .then((data) => !cancelled && setCall(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [callId]);

  if (!callId) return null;

  const done = call?.status === "done";
  const nextSteps = call?.extraction?.next_steps || [];
  const objections = call?.extraction?.objections || [];

  return (
    <div className="ce-modal-overlay" style={{ zIndex: 48 }} onClick={onClose}>
      <div className="ce-modal ce-modal-md" onClick={(e) => e.stopPropagation()}>
        <div className="ce-modal-header">
          <div className="ce-modal-header-titles">
            <div className="ce-call-title-row">
              <span className="ce-call-filename" style={{ fontSize: 15 }}>{call?.filename || "…"}</span>
              {call && <StatusChip status={call.status} />}
            </div>
            {call && (
              <span className="ce-call-submeta">
                {call.duration ? fmtTime(call.duration) : "—"}
                {call.dual_channel ? " · dual-channel" : " · mono"}
              </span>
            )}
          </div>
          <button type="button" className="ce-modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="ce-modal-body">
          {error && <span className="error">{error}</span>}
          {!error && !call && <span className="hint">Loading…</span>}

          {call && (
            <>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                <span className="ce-eyebrow">{done ? "CALL SUMMARY · F2" : call.status === "failed" ? "WHY IT FAILED" : "STATUS"}</span>
                <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--ce-text)" }}>
                  {done ? call.extraction?.summary : call.error || "Still processing — check back shortly."}
                </span>
              </div>

              {done && (
                <>
                  <div style={{ display: "flex", flexDirection: "column", gap: 7, borderTop: "1px solid var(--ce-divider)", paddingTop: 14 }}>
                    <span className="ce-eyebrow">NEXT STEPS</span>
                    {nextSteps.length === 0 && <span className="hint">None extracted.</span>}
                    {nextSteps.map((s, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, border: "1px solid var(--ce-border)", borderRadius: 10, background: "var(--ce-surface-2)", padding: "11px 12px" }}>
                        <span style={{ flex: 1, fontSize: 13, lineHeight: 1.5, color: "var(--ce-text)" }}>{s.description}</span>
                        <span className="ce-chip">{s.due || "no date"}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 7, borderTop: "1px solid var(--ce-divider)", paddingTop: 14 }}>
                    <span className="ce-eyebrow">OBJECTIONS</span>
                    {objections.length === 0 && <span className="hint">None detected.</span>}
                    {objections.map((o, i) => (
                      <div key={i} style={{ border: "1px solid var(--ce-border)", borderRadius: 10, background: "var(--ce-surface-2)", padding: "12px 13px", display: "flex", flexDirection: "column", gap: 9 }}>
                        <span className="ce-chip ce-chip-accent" style={{ alignSelf: "flex-start" }}>{o.category.toUpperCase()}</span>
                        <span style={{ fontSize: 14, lineHeight: 1.55, color: "var(--ce-text)", paddingLeft: 12, borderLeft: "2px solid var(--ce-accent)" }}>
                          &ldquo;{o.quote}&rdquo;
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              <button type="button" className="ce-btn" onClick={() => onOpenFull(call.id)}>
                {done ? "Open full review in Calls" : "Close"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
