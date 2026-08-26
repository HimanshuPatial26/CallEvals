import { useState } from "react";
import { fmtRelative } from "../utils/format";

const FILTERS = ["All open", "Objection raised", "No next step"];

const STAGE_STYLE = {
  Offer: "ce-chip-success",
  New: "ce-chip-muted",
};

export default function LeadsScreen({ leads, onOpenLead }) {
  const [filter, setFilter] = useState("All open");

  let rows = leads;
  if (filter === "Objection raised") rows = rows.filter((l) => l.objection_tags.length > 0);
  if (filter === "No next step") rows = rows.filter((l) => !l.open_next_step);

  return (
    <div className="ce-content-scroll">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {FILTERS.map((f) => (
          <button key={f} type="button" className={`ce-filter-pill${filter === f ? " active" : ""}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
        <span className="hint" style={{ marginLeft: "auto", fontFamily: "var(--ce-font-mono)" }}>
          {rows.length} OF {leads.length} LEADS
        </span>
      </div>

      <div className="ce-table">
        <div className="ce-table-head" style={{ gridTemplateColumns: "1.4fr 1.2fr .8fr 1.7fr .9fr" }}>
          <span className="ce-table-head-cell">LEAD</span>
          <span className="ce-table-head-cell">UNIT · BUDGET</span>
          <span className="ce-table-head-cell">STAGE</span>
          <span className="ce-table-head-cell">OPEN NEXT STEP</span>
          <span className="ce-table-head-cell">LAST CALL</span>
        </div>
        {rows.length === 0 && <div className="ce-table-empty">No leads match this filter.</div>}
        {rows.map((lead) => (
          <button key={lead.id} type="button" className="ce-table-row" style={{ gridTemplateColumns: "1.4fr 1.2fr .8fr 1.7fr .9fr" }} onClick={() => onOpenLead(lead.id)}>
            <span className="ce-table-cell-stack">
              <span style={{ fontSize: 13, color: "var(--ce-text)" }}>{lead.name}</span>
              <span className="ce-transcript-ts">{lead.phone}</span>
            </span>
            <span className="ce-table-cell-stack">
              <span style={{ fontSize: 12, color: "var(--ce-text-row)" }}>{lead.unit || "not stated"}</span>
              <span className="ce-transcript-ts">{lead.budget || "not stated"}</span>
            </span>
            <span className={`ce-chip ${STAGE_STYLE[lead.stage] || "ce-chip-accent"}`} style={{ justifySelf: "start" }}>{lead.stage}</span>
            <span className="ce-table-cell-stack">
              <span style={{ fontSize: 12, color: "var(--ce-text)" }}>{lead.open_next_step ? lead.open_next_step.description : "No next step committed"}</span>
              <span className="ce-transcript-ts">{lead.open_next_step?.due || "no date stated"}</span>
            </span>
            <span className="ce-shape-value">{fmtRelative(lead.last_call_at)}</span>
          </button>
        ))}
      </div>
      <span className="ce-footnote">
        Open next steps come straight from extraction — a lead with no committed next step is a real churn signal to check.
      </span>
    </div>
  );
}
