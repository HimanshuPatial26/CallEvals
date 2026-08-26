export default function LeadCard({ lead, callCount, onOpenLead }) {
  if (!lead) {
    return (
      <div className="ce-card">
        <div className="ce-card-header">
          <span className="ce-card-title">Lead</span>
        </div>
        <div className="ce-unavailable">No lead linked to this call.</div>
      </div>
    );
  }

  return (
    <div className="ce-card">
      <div className="ce-card-header">
        <span className="ce-card-title">Lead</span>
        <span className="ce-card-tag">FROM UPLOAD</span>
      </div>
      <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        <span className="ce-lead-name">{lead.name}</span>
        <span className="ce-lead-phone">{lead.phone}</span>
        <div className="ce-lead-fields">
          <div className="ce-lead-field-row">
            <span className="ce-lead-field-label">Unit</span>
            <span className="ce-lead-field-value">{lead.unit || "not stated"}</span>
          </div>
          <div className="ce-lead-field-row">
            <span className="ce-lead-field-label">Budget</span>
            <span className="ce-lead-field-value mono">{lead.budget || "not stated"}</span>
          </div>
          <div className="ce-lead-field-row">
            <span className="ce-lead-field-label">Stage</span>
            <span className="ce-lead-field-value">{lead.stage}</span>
          </div>
          <div className="ce-lead-field-row">
            <span className="ce-lead-field-label">Source</span>
            <span className="ce-lead-field-value">{lead.source || "not stated"}</span>
          </div>
        </div>
        <button type="button" className="ce-btn" onClick={onOpenLead}>
          All {callCount} call{callCount === 1 ? "" : "s"} on this lead
        </button>
      </div>
    </div>
  );
}
