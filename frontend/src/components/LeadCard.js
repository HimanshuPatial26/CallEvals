// One lead in the pipeline board (LeadPipelinePage). Drag-and-drop is the
// primary way to move a card between stages; the prev/next buttons are a
// keyboard/touch-accessible fallback that do the exact same
// POST /api/leads/{id}/stage write, not a separate code path.
export default function LeadCard({ lead, agentName, onDragStart, onMovePrev, onMoveNext, canMovePrev, canMoveNext, busy }) {
  return (
    <li className={`lead-card${busy ? " lead-card-busy" : ""}`} draggable={!busy} onDragStart={(e) => onDragStart(e, lead)}>
      <div className="lead-card-header">
        <span className="lead-card-name">{lead.display_name}</span>
        {lead.stage === "won" && lead.deal_size_aed != null && (
          <span className="lead-card-deal">{lead.deal_size_aed.toLocaleString()} AED</span>
        )}
      </div>
      <p className="item-meta">
        {agentName || "Unassigned"}
        {lead.phone ? ` · ${lead.phone}` : ""}
        {lead.source ? ` · ${lead.source}` : ""}
      </p>
      <div className="lead-card-actions">
        <button type="button" className="lead-card-move" disabled={!canMovePrev || busy} onClick={() => onMovePrev(lead)} title="Move to previous stage">
          ‹
        </button>
        <button type="button" className="lead-card-move" disabled={!canMoveNext || busy} onClick={() => onMoveNext(lead)} title="Move to next stage">
          ›
        </button>
      </div>
    </li>
  );
}
