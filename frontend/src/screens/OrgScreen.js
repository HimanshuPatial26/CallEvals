import { useEffect, useState } from "react";
import { getOrg } from "../api/client";

export default function OrgScreen({ repPrivateMode, onOpenAgent, onOpenRubric }) {
  const [org, setOrg] = useState(null);

  useEffect(() => {
    let cancelled = false;
    function load() {
      getOrg().then((data) => !cancelled && setOrg(data));
    }
    load();
    const interval = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!org) {
    return (
      <div className="ce-content-scroll">
        <span className="hint">Loading…</span>
      </div>
    );
  }

  const kpis = [
    { label: "COVERAGE", value: `${org.coverage}%`, note: "Target 85%. Below that the summaries have blind spots." },
    { label: "EXTRACTION PRECISION", value: `${org.extraction_precision}%`, note: "Manager-confirmed next steps, sampled from real feedback." },
    { label: "MANAGER ENGAGEMENT", value: `${org.manager_engagement}%`, note: "Summaries opened within 24h. Leading churn signal." },
    { label: "BEHAVIOUR IMPROVEMENT", value: `${org.behavior_improvement}%`, note: "North star. Flags that clear across the next 5 calls." },
  ];

  const roster = [...org.roster].sort((a, b) =>
    repPrivateMode ? b.calls_reviewed - a.calls_reviewed : b.behavior_improvement - a.behavior_improvement
  );

  return (
    <div className="ce-content-scroll">
      <div className="ce-kpi-grid">
        {kpis.map((k) => (
          <div key={k.label} className="ce-kpi-tile">
            <span className="ce-shape-caps">{k.label}</span>
            <span className="ce-kpi-value">{k.value}</span>
            <div className="ce-crit-bar-track">
              <span className="ce-crit-bar-fill" style={{ width: k.value, background: "var(--ce-accent)" }} />
            </div>
            <span className="ce-kpi-note">{k.note}</span>
          </div>
        ))}
      </div>

      <div className="ce-card">
        <div className="ce-card-header">
          <span className="ce-card-title">Team</span>
          <span className="ce-card-tag">
            {org.agent_count} AGENTS {repPrivateMode ? "· NAMES MASKED · RANKING OFF" : "· RANKING ON"}
          </span>
          <button type="button" className="ce-jump-chip" style={{ marginLeft: "auto" }} onClick={onOpenRubric}>
            Ranking settings
          </button>
        </div>
        <div className="ce-table-head" style={{ gridTemplateColumns: "1.5fr .7fr .8fr .8fr 1.1fr" }}>
          <span className="ce-table-head-cell">AGENT</span>
          <span className="ce-table-head-cell">CALLS</span>
          <span className="ce-table-head-cell">COVERAGE</span>
          <span className="ce-table-head-cell">OPEN FLAGS</span>
          <span className="ce-table-head-cell">TOP OBJECTION</span>
        </div>
        {roster.length === 0 && <div className="ce-table-empty">No agents yet.</div>}
        {roster.map((r, i) => (
          <button key={r.id} type="button" className="ce-table-row" style={{ gridTemplateColumns: "1.5fr .7fr .8fr .8fr 1.1fr" }} onClick={() => onOpenAgent(r.id)}>
            <span className="ce-table-cell-primary">
              <span className="ce-user-avatar" style={{ width: 24, height: 24, fontSize: 9 }}>
                {repPrivateMode ? i + 1 : initials(r.name)}
              </span>
              <span style={{ fontSize: 13, color: "var(--ce-text)" }}>{repPrivateMode ? `Agent ${i + 1}` : r.name}</span>
            </span>
            <span className="ce-shape-value">{r.calls_reviewed}</span>
            <span className="ce-shape-value" style={{ color: r.coverage >= 85 ? "var(--ce-success)" : "var(--ce-danger)" }}>{r.coverage}%</span>
            <span className="ce-shape-value">{r.open_flags}</span>
            {r.top_objection ? <span className="ce-chip ce-chip-accent">{r.top_objection}</span> : <span className="hint">none</span>}
          </button>
        ))}
        <div style={{ padding: "13px 16px" }}>
          <span className="ce-footnote">
            {repPrivateMode
              ? "Rep-private mode is on: names are masked and rows are sorted by call volume, not performance. Reps see their own analysis first for 30 days."
              : "Ranking is on. Sorted by behaviour improvement — worth watching whether calls quietly stop being recorded."}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <div className="ce-card" style={{ flex: 1 }}>
          <div className="ce-card-header"><span className="ce-card-title">Where deals stall</span></div>
          <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {org.where_deals_stall.length === 0 && <span className="hint">Not enough open leads yet to estimate.</span>}
            {org.where_deals_stall.map((s) => (
              <div key={s.label} className="ce-crit-row">
                <div className="ce-crit-label-row">
                  <span className="ce-crit-label" style={{ textTransform: "capitalize" }}>{s.label}</span>
                  <span className="ce-crit-value">{s.count} leads</span>
                </div>
                <div className="ce-crit-bar-track">
                  <span className="ce-crit-bar-fill" style={{ width: `${s.pct}%`, background: "var(--ce-accent)" }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="ce-card" style={{ width: 340, flex: "none" }}>
          <div className="ce-card-header"><span className="ce-card-title">Data & consent</span></div>
          <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 11 }}>
            <ConsentRow color="var(--ce-accent)" label={`Disclosure detected on ${org.disclosure_detected_pct}% of calls`} note="Compliance flag computed per call from the opening 30 seconds." />
            <ConsentRow color="var(--ce-success)" label={`Retention set to ${org.retention_days} days`} note="Configurable in Rubric & flags. Deletion cascades to transcripts and derived analysis." />
          </div>
        </div>
      </div>
    </div>
  );
}

function ConsentRow({ color, label, note }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", flex: "none", marginTop: 5, background: color }} />
      <span style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ce-text)" }}>{label}</span>
        <span className="hint">{note}</span>
      </span>
    </div>
  );
}

function initials(name) {
  return name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}
