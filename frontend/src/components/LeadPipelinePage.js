import { useCallback, useEffect, useMemo, useState } from "react";
import { listAgents, listLeads, setLeadStage } from "../api/client";
import LeadCard from "./LeadCard";
import LeadDetailModal from "./LeadDetailModal";

// ROADMAP.md C5 — the funnel as a board, not a per-call dropdown. Stage
// order here drives both column layout and the prev/next arrow buttons on
// each card; the backend itself places no restriction on which stage a
// lead can move to from which (see lead_storage.set_stage), so nothing
// here validates transitions either.
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

export default function LeadPipelinePage() {
  const [leads, setLeads] = useState([]);
  const [agents, setAgents] = useState([]);
  const [agentFilter, setAgentFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dragOverStage, setDragOverStage] = useState(null);
  const [movingLeadId, setMovingLeadId] = useState(null);
  const [wonPrompt, setWonPrompt] = useState(null); // { lead, targetStage }
  const [wonDealSize, setWonDealSize] = useState("");
  const [lostPrompt, setLostPrompt] = useState(null); // { lead, targetStage }
  const [lostReasonChoice, setLostReasonChoice] = useState("");
  const [detailLeadId, setDetailLeadId] = useState(null);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((err) => setError(err.message));
  }, []);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listLeads({ assignedAgentId: agentFilter || undefined, q: search || undefined });
      setLeads(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [agentFilter, search]);

  useEffect(() => {
    const timer = setTimeout(loadLeads, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [loadLeads, search]);

  const agentNameById = useMemo(() => Object.fromEntries(agents.map((a) => [a.id, a.name])), [agents]);

  const columns = useMemo(
    () => STAGES.map(([stage, label]) => ({ stage, label, leads: leads.filter((l) => l.stage === stage) })),
    [leads]
  );

  async function commitMove(lead, targetStage, dealSizeAed, lostReason) {
    setMovingLeadId(lead.id);
    setError(null);
    try {
      const updated = await setLeadStage(lead.id, targetStage, dealSizeAed, lostReason);
      setLeads((prev) => prev.map((l) => (l.id === lead.id ? updated : l)));
    } catch (err) {
      setError(err.message);
    } finally {
      setMovingLeadId(null);
    }
  }

  function moveLead(lead, targetStage) {
    if (targetStage === lead.stage) return;
    if (targetStage === "won" && lead.deal_size_aed == null) {
      setWonDealSize("");
      setWonPrompt({ lead, targetStage });
      return;
    }
    if (targetStage === "lost" && lead.lost_reason == null) {
      setLostReasonChoice("");
      setLostPrompt({ lead, targetStage });
      return;
    }
    commitMove(lead, targetStage, null, null);
  }

  function confirmWonPrompt(dealSizeAed) {
    const { lead, targetStage } = wonPrompt;
    setWonPrompt(null);
    commitMove(lead, targetStage, dealSizeAed, null);
  }

  function confirmLostPrompt(reason) {
    const { lead, targetStage } = lostPrompt;
    setLostPrompt(null);
    commitMove(lead, targetStage, null, reason);
  }

  function handleDragStart(e, lead) {
    e.dataTransfer.setData("text/plain", lead.id);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(e, targetStage) {
    e.preventDefault();
    setDragOverStage(null);
    const leadId = e.dataTransfer.getData("text/plain");
    const lead = leads.find((l) => l.id === leadId);
    if (lead) moveLead(lead, targetStage);
  }

  return (
    <div className="lead-pipeline-page">
      <div className="agent-performance-controls panel">
        <label className="outcome-field">
          Agent
          <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)}>
            <option value="">All agents</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="outcome-field">
          Search
          <input type="text" placeholder="Name or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint loading-state">Loading…</p>}

      {!loading && (
        <div className="lead-board">
          {columns.map(({ stage, label, leads: stageLeads }) => {
            const wonTotal = stage === "won" ? stageLeads.reduce((sum, l) => sum + (l.deal_size_aed || 0), 0) : null;
            return (
              <div
                key={stage}
                className={`lead-column${dragOverStage === stage ? " lead-column-drag-over" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOverStage(stage);
                }}
                onDragLeave={() => setDragOverStage((s) => (s === stage ? null : s))}
                onDrop={(e) => handleDrop(e, stage)}
              >
                <div className="lead-column-header">
                  <span>{label}</span>
                  <span className="lead-column-count">
                    {stageLeads.length}
                    {wonTotal != null && wonTotal > 0 && ` · ${wonTotal.toLocaleString()} AED`}
                  </span>
                </div>
                <ul className="lead-column-list">
                  {stageLeads.length === 0 && <li className="hint lead-column-empty">No leads</li>}
                  {stageLeads.map((lead) => {
                    const index = STAGES.findIndex(([s]) => s === lead.stage);
                    return (
                      <LeadCard
                        key={lead.id}
                        lead={lead}
                        agentName={lead.assigned_agent_id ? agentNameById[lead.assigned_agent_id] : null}
                        onDragStart={handleDragStart}
                        onMovePrev={(l) => moveLead(l, STAGES[index - 1][0])}
                        onMoveNext={(l) => moveLead(l, STAGES[index + 1][0])}
                        canMovePrev={index > 0}
                        canMoveNext={index < STAGES.length - 1}
                        onViewDetails={(l) => setDetailLeadId(l.id)}
                        busy={movingLeadId === lead.id}
                      />
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {wonPrompt && (
        <div className="modal-overlay" onClick={() => setWonPrompt(null)}>
          <div className="modal panel" onClick={(e) => e.stopPropagation()}>
            <h3>Mark "{wonPrompt.lead.display_name}" as Won</h3>
            <label className="outcome-field">
              Deal size (AED)
              <input
                type="number"
                min="0"
                autoFocus
                value={wonDealSize}
                onChange={(e) => setWonDealSize(e.target.value)}
              />
            </label>
            <div className="modal-actions">
              <button type="button" onClick={() => confirmWonPrompt(null)}>
                Skip
              </button>
              <button type="button" onClick={() => confirmWonPrompt(wonDealSize === "" ? null : Number(wonDealSize))}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {lostPrompt && (
        <div className="modal-overlay" onClick={() => setLostPrompt(null)}>
          <div className="modal panel" onClick={(e) => e.stopPropagation()}>
            <h3>Mark "{lostPrompt.lead.display_name}" as Lost</h3>
            <label className="outcome-field">
              Lost reason
              <select autoFocus value={lostReasonChoice} onChange={(e) => setLostReasonChoice(e.target.value)}>
                <option value="">Not recorded</option>
                {LOST_REASONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <div className="modal-actions">
              <button type="button" onClick={() => confirmLostPrompt(null)}>
                Skip
              </button>
              <button type="button" onClick={() => confirmLostPrompt(lostReasonChoice === "" ? null : lostReasonChoice)}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {detailLeadId && (
        <LeadDetailModal
          leadId={detailLeadId}
          agents={agents}
          onClose={() => {
            setDetailLeadId(null);
            loadLeads(); // a reassignment in the modal can change what the board shows under the current agent filter
          }}
        />
      )}
    </div>
  );
}
