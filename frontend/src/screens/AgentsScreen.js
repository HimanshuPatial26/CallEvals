import { useEffect, useState } from "react";
import { getAgent } from "../api/client";
import { fmtDateShort } from "../utils/format";

function trendSvgPoints(values, min, max, height) {
  if (!values || values.length === 0) return "";
  return values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = height - ((v - min) / Math.max(1, max - min)) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function AgentsScreen({ agents, repPrivateMode, selectedAgentId, onSelectAgent }) {
  const agentId = selectedAgentId || agents[0]?.id || null;
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!selectedAgentId && agents[0]) onSelectAgent(agents[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents, selectedAgentId]);

  useEffect(() => {
    if (!agentId) return;
    let cancelled = false;
    getAgent(agentId).then((data) => !cancelled && setDetail(data));
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  if (agents.length === 0) {
    return (
      <div className="ce-content-scroll">
        <div className="ce-dashed-empty">
          <span className="ce-state-title">No agents yet.</span>
          <span className="ce-state-body">Agents are created automatically the first time a call is uploaded under their name.</span>
        </div>
      </div>
    );
  }

  const displayName = (a, i) => (repPrivateMode ? `Agent ${i + 1}` : a.name);
  const activeAgent = agents.find((a) => a.id === agentId);

  return (
    <div className="ce-content-scroll">
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {agents.slice(0, 6).map((a, i) => (
          <button key={a.id} type="button" className={`ce-agent-chip${a.id === agentId ? " active" : ""}`} onClick={() => onSelectAgent(a.id)}>
            {displayName(a, i)}
            <span className="ce-agent-chip-count">{a.calls_reviewed}</span>
          </button>
        ))}
      </div>

      {!detail ? (
        <span className="hint">Loading…</span>
      ) : (
        <>
          <div className="ce-kpi-grid">
            <div className="ce-kpi-tile">
              <span className="ce-shape-caps">CALLS REVIEWED</span>
              <span className="ce-kpi-value">{detail.calls_reviewed}</span>
              <span className="ce-kpi-note">total done calls linked to this agent</span>
            </div>
            <div className="ce-kpi-tile">
              <span className="ce-shape-caps">BEHAVIOUR IMPROVEMENT</span>
              <span className="ce-kpi-value">{detail.behavior_improvement}%</span>
              <span className="ce-kpi-note">of flags cleared within the next 5 calls</span>
            </div>
            <div className="ce-kpi-tile">
              <span className="ce-shape-caps">OPEN FLAGS</span>
              <span className="ce-kpi-value">{detail.open_flags}</span>
              <span className="ce-kpi-note">active on the most recent call</span>
            </div>
            <div className="ce-kpi-tile">
              <span className="ce-shape-caps">COVERAGE</span>
              <span className="ce-kpi-value" style={{ color: detail.coverage >= 85 ? "var(--ce-success)" : "var(--ce-text)" }}>
                {detail.coverage}%
              </span>
              <span className="ce-kpi-note" style={{ color: detail.coverage >= 85 ? "var(--ce-success)" : "var(--ce-danger)" }}>
                {detail.coverage >= 85 ? "above the 85% floor" : "below the 85% floor"}
              </span>
            </div>
          </div>

          <div className="ce-trend-row">
            <div className="ce-card ce-trend-card">
              <div className="ce-card-header">
                <span className="ce-card-title">Behaviour improvement trend</span>
                <span className="ce-card-tag" style={{ marginLeft: "auto" }}>WEEKLY · FLAG-FREE RATE</span>
              </div>
              <div className="ce-trend-body">
                <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="ce-trend-svg">
                  <line x1="0" y1="10" x2="100" y2="10" stroke="var(--ce-divider)" strokeWidth="0.5" />
                  <line x1="0" y1="20" x2="100" y2="20" stroke="var(--ce-divider)" strokeWidth="0.5" />
                  <line x1="0" y1="30" x2="100" y2="30" stroke="var(--ce-divider)" strokeWidth="0.5" />
                  <polyline points={trendSvgPoints(detail.trend, 0, 100, 40)} fill="none" stroke="var(--ce-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                  <polyline points={trendSvgPoints(detail.team_trend, 0, 100, 40)} fill="none" stroke="var(--ce-track)" strokeWidth="1.4" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
                </svg>
                <div className="ce-trend-legend">
                  <span className="ce-legend-item"><span className="ce-legend-swatch" style={{ background: "var(--ce-accent)" }} />{repPrivateMode ? "this agent" : activeAgent?.name}</span>
                  <span className="ce-legend-item"><span className="ce-legend-swatch" style={{ background: "var(--ce-track)" }} />team median</span>
                </div>
              </div>
            </div>

            <div className="ce-card" style={{ width: 300, flex: "none" }}>
              <div className="ce-card-header"><span className="ce-card-title">Objection mix</span></div>
              <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {detail.objection_mix.length === 0 && <span className="hint">No objections recorded yet.</span>}
                {detail.objection_mix.map((o) => (
                  <div key={o.category} className="ce-crit-row">
                    <div className="ce-crit-label-row">
                      <span className="ce-crit-label" style={{ textTransform: "capitalize" }}>{o.category}</span>
                      <span className="ce-crit-value">{o.raised} raised</span>
                    </div>
                    <div className="ce-crit-bar-track">
                      <span className="ce-crit-bar-fill" style={{ width: `${o.pct}%`, background: "var(--ce-accent)" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="ce-card">
            <div className="ce-card-header">
              <span className="ce-card-title">Flagged behaviours</span>
              <span className="ce-card-tag">NORTH STAR · BEHAVIOUR IMPROVEMENT RATE</span>
            </div>
            <div className="ce-table-head" style={{ gridTemplateColumns: "1.6fr .8fr .8fr .9fr 1fr" }}>
              <span className="ce-table-head-cell">BEHAVIOUR</span>
              <span className="ce-table-head-cell">FIRST FLAG</span>
              <span className="ce-table-head-cell">CALLS SINCE</span>
              <span className="ce-table-head-cell">NEXT 5 CALLS</span>
              <span className="ce-table-head-cell">STATUS</span>
            </div>
            {detail.behaviors.length === 0 && <div className="ce-table-empty">No behavior flags raised yet — clean record.</div>}
            {detail.behaviors.map((b) => (
              <div key={b.name} className="ce-table-row" style={{ gridTemplateColumns: "1.6fr .8fr .8fr .9fr 1fr", cursor: "default" }}>
                <span style={{ fontSize: 13, color: "var(--ce-text)" }}>{b.name}</span>
                <span className="ce-shape-value">{fmtDateShort(b.first_flag_at)}</span>
                <span className="ce-shape-value">{b.calls_since} calls</span>
                <span className="ce-dots">
                  {b.dots.map((v, i) => (
                    <span key={i} className={`ce-dot${v ? " on" : ""}`} />
                  ))}
                </span>
                <span className={`ce-chip ${statusChipClass(b.status)}`}>{b.status}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function statusChipClass(status) {
  if (status === "improved") return "ce-chip-success";
  if (status === "improving") return "ce-chip-accent";
  if (status === "regressed") return "ce-chip-danger";
  return "ce-chip-muted";
}
