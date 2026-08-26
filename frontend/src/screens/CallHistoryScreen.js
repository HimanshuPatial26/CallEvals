import { useState } from "react";
import StatusChip from "../components/StatusChip";
import { StatusIcon } from "../icons";
import { fmtTime } from "../utils/format";

const FILTERS = ["All", "Ready", "Needs attention", "No next step"];

function outcomeFor(call) {
  if (call.status === "done") {
    const objs = call.extraction?.objections || [];
    return objs.length ? `${objs[0].category} objection` : "no objection raised";
  }
  if (call.status === "failed") return "speaker split failed";
  if (call.status === "processing") return "in the pipeline";
  return "waiting in queue";
}

export default function CallHistoryScreen({ calls, agentsById, onOpenCall }) {
  const [filter, setFilter] = useState("All");

  let rows = calls;
  if (filter === "Ready") rows = rows.filter((c) => c.status === "done");
  if (filter === "Needs attention") rows = rows.filter((c) => c.status === "failed");
  if (filter === "No next step") rows = rows.filter((c) => c.status === "done" && !(c.extraction?.next_steps || []).length);

  return (
    <div className="ce-content-scroll">
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {FILTERS.map((f) => (
          <button key={f} type="button" className={`ce-filter-pill${filter === f ? " active" : ""}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
        <span className="hint" style={{ marginLeft: "auto", fontFamily: "var(--ce-font-mono)" }}>
          {rows.length} OF {calls.length} CALLS
        </span>
      </div>

      <div className="ce-table">
        <div className="ce-table-head" style={{ gridTemplateColumns: "1.3fr 1.1fr .6fr .8fr .9fr" }}>
          <span className="ce-table-head-cell">RECORDING</span>
          <span className="ce-table-head-cell">AGENT</span>
          <span className="ce-table-head-cell">LENGTH</span>
          <span className="ce-table-head-cell">STATUS</span>
          <span className="ce-table-head-cell">OUTCOME</span>
        </div>
        {rows.length === 0 && <div className="ce-table-empty">No calls match this filter.</div>}
        {rows.map((call) => (
          <button
            key={call.id}
            type="button"
            className="ce-table-row"
            style={{ gridTemplateColumns: "1.3fr 1.1fr .6fr .8fr .9fr" }}
            onClick={() => onOpenCall(call.id)}
          >
            <span className="ce-table-cell-primary">
              <StatusIcon status={call.status} size={18} />
              <span className="ce-table-cell-file">{call.filename}</span>
            </span>
            <span style={{ fontSize: 13, color: "var(--ce-text-row)" }}>{agentsById[call.agent_id]?.name || "Unassigned"}</span>
            <span className="ce-shape-value">{call.duration ? fmtTime(call.duration) : "—"}</span>
            <span><StatusChip status={call.status} /></span>
            <span style={{ fontSize: 12, color: "var(--ce-text-hint)" }}>{outcomeFor(call)}</span>
          </button>
        ))}
      </div>
      <span className="ce-footnote">
        Opening a call moves it into the Calls tab for review. History keeps the full library — filters here, one call at a time there.
      </span>
    </div>
  );
}
