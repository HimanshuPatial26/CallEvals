import { useEffect, useState } from "react";
import { getCall, getLead, reassignLead } from "../api/client";
import CallDetail from "./CallDetail";

const STAGE_LABELS = {
  untagged: "Untagged",
  qualified: "Qualified",
  demo_booked: "Demo booked",
  proposal_sent: "Proposal sent",
  won: "Won",
  lost: "Lost",
};

function fmtDateTime(iso) {
  return new Date(iso).toLocaleString();
}

// ROADMAP.md C6 — the "one lead, many calls" view: full stage-change audit
// trail (already collected by set_stage, just not surfaced anywhere until
// now), full reassignment history (new — see AssignmentEvent/reassign()),
// and a read-only call history list. Reached via each LeadCard's "view
// details" button rather than clicking the card itself, since the card is
// also a drag handle and click-after-drag is unreliable across browsers.
export default function LeadDetailModal({ leadId, agents, onClose }) {
  const [lead, setLead] = useState(null);
  const [error, setError] = useState(null);
  const [reassignTo, setReassignTo] = useState("");
  const [reassigning, setReassigning] = useState(false);

  // Popup-within-a-popup for a call-history row's full analysis, fetched on
  // demand (LeadCallSummary only carries id/date/agent/score/status, not
  // the transcript/extraction CallDetail needs) -- kept as a second overlay
  // on top of this one, rather than navigating to the Calls tab, so the
  // manager stays on the Leads board with this lead's modal still open
  // underneath once they close it.
  const [openCallId, setOpenCallId] = useState(null);
  const [openCall, setOpenCall] = useState(null);
  const [openCallError, setOpenCallError] = useState(null);

  useEffect(() => {
    setLead(null);
    setError(null);
    getLead(leadId)
      .then((data) => {
        setLead(data);
        setReassignTo(data.assigned_agent_id || "");
      })
      .catch((err) => setError(err.message));
  }, [leadId]);

  useEffect(() => {
    if (!openCallId) return;
    setOpenCall(null);
    setOpenCallError(null);
    getCall(openCallId)
      .then(setOpenCall)
      .catch((err) => setOpenCallError(err.message));
  }, [openCallId]);

  async function handleReassign() {
    setReassigning(true);
    setError(null);
    try {
      const updated = await reassignLead(leadId, reassignTo || null, null);
      setLead((prev) => ({
        ...prev,
        assigned_agent_id: updated.assigned_agent_id,
        assignment_history: updated.assignment_history,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setReassigning(false);
    }
  }

  const agentNameById = Object.fromEntries(agents.map((a) => [a.id, a.name]));

  return (
    <>
      <div className="modal-overlay" onClick={onClose}>
        <div
          className="modal panel lead-detail-modal"
          onClick={(e) => e.stopPropagation()}
        >
          {error && <p className="error">{error}</p>}
          {!lead ? (
            <p className="hint loading-state">Loading…</p>
          ) : (
            <>
              <div className="lead-detail-header">
                <h3>{lead.display_name}</h3>
                <button type="button" className="link-button" onClick={onClose}>
                  Close
                </button>
              </div>
              <p className="item-meta">
                {lead.phone || "No phone"} · {lead.source || "Unknown source"} ·{" "}
                {STAGE_LABELS[lead.stage]}
                {lead.stage === "won" &&
                  lead.deal_size_aed != null &&
                  ` · ${lead.deal_size_aed.toLocaleString()} AED`}
              </p>

              <div className="outcome-panel">
                <label className="outcome-field">
                  Reassign to
                  <select
                    value={reassignTo}
                    onChange={(e) => setReassignTo(e.target.value)}
                    disabled={reassigning}
                  >
                    <option value="">Unassigned</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button onClick={handleReassign} disabled={reassigning}>
                  {reassigning ? "Saving…" : "Reassign"}
                </button>
              </div>

              <div className="call-detail-columns">
                <section>
                  <h4>Stage history</h4>
                  {lead.stage_history.length === 0 ? (
                    <p className="hint">No stage changes yet.</p>
                  ) : (
                    <ul className="insights-list">
                      {lead.stage_history
                        .slice()
                        .reverse()
                        .map((event, i) => (
                          <li key={i}>
                            <span className="insights-label">
                              {STAGE_LABELS[event.stage]}
                            </span>
                            <span className="insights-value">
                              {fmtDateTime(event.changed_at)}
                            </span>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
                <section>
                  <h4>Assignment history</h4>
                  {lead.assignment_history.length === 0 ? (
                    <p className="hint">Never reassigned.</p>
                  ) : (
                    <ul className="insights-list">
                      {lead.assignment_history
                        .slice()
                        .reverse()
                        .map((event, i) => (
                          <li key={i}>
                            <span className="insights-label">
                              {event.assigned_agent_id
                                ? agentNameById[event.assigned_agent_id] ||
                                  event.assigned_agent_id
                                : "Unassigned"}
                            </span>
                            <span className="insights-value">
                              {fmtDateTime(event.changed_at)}
                            </span>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
              </div>

              <h4>Call history ({lead.calls.length})</h4>
              {lead.calls.length === 0 ? (
                <p className="hint">No calls yet.</p>
              ) : (
                <table className="trend-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Agent</th>
                      <th>Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lead.calls.map((c) => (
                      <tr
                        key={c.id}
                        className="trend-table-row-clickable"
                        tabIndex={0}
                        role="button"
                        onClick={() => setOpenCallId(c.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setOpenCallId(c.id);
                          }
                        }}
                      >
                        <td>{fmtDateTime(c.created_at)}</td>
                        <td>{agentNameById[c.agent_id] || c.agent_id}</td>
                        <td>
                          {c.overall_score != null
                            ? Math.round(c.overall_score)
                            : "—"}
                        </td>
                        <td>{c.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </div>
      </div>

      {openCallId && (
        <div className="modal-overlay" onClick={() => setOpenCallId(null)}>
          <div
            className="modal panel call-detail-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="lead-detail-header">
              <h3>Call analysis</h3>
              <button
                type="button"
                className="link-button"
                onClick={() => setOpenCallId(null)}
              >
                Close
              </button>
            </div>
            {openCallError && <p className="error">{openCallError}</p>}
            {!openCall && !openCallError ? (
              <p className="hint loading-state">Loading…</p>
            ) : (
              openCall && (
                <CallDetail
                  call={openCall}
                  onFeedbackChange={(newFeedback) =>
                    setOpenCall((prev) => ({ ...prev, feedback: newFeedback }))
                  }
                />
              )
            )}
          </div>
        </div>
      )}
    </>
  );
}
