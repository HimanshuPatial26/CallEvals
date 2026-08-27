import { LogoMark } from "../icons";

const NAV_ITEMS = [
  { key: "calls", n: "01", label: "Calls" },
  { key: "history", n: "02", label: "Call history" },
  { key: "agents", n: "03", label: "Agent performance" },
  { key: "org", n: "04", label: "Organization" },
  { key: "leads", n: "05", label: "Leads" },
  { key: "rubric", n: "06", label: "Rubric & flags" },
];

export default function Sidebar({ screen, onNavigate, counts, repPrivateMode, pipelineText }) {
  return (
    <aside className="ce-sidebar">
      <div className="ce-sidebar-logo">
        <LogoMark size={24} animated />
        <span className="ce-sidebar-logo-text">
          <span className="ce-sidebar-logo-name">CallEvals</span>
          <span className="ce-sidebar-logo-tag">CALL INTELLIGENCE</span>
        </span>
      </div>

      <div className="ce-nav-section">
        <span className="ce-nav-heading">NAVIGATION</span>
        <div className="ce-nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`ce-nav-item${screen === item.key ? " active" : ""}`}
              onClick={() => onNavigate(item.key)}
            >
              <span className="ce-nav-rule" />
              <span className="ce-nav-num">{item.n}</span>
              <span className="ce-nav-label">{item.label}</span>
              {counts[item.key] != null && <span className="ce-nav-count">{counts[item.key]}</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="ce-sidebar-footer">
        {repPrivateMode && (
          <div className="ce-mini-panel">
            <span className="ce-mini-panel-title">
              <span className="ce-mini-dot" />
              REP-PRIVATE MODE
            </span>
            <span className="ce-mini-panel-body">Agents see their own analysis first. Names masked in rollups for 30 days.</span>
          </div>
        )}
        <div className="ce-mini-panel">
          <span className="ce-mini-panel-title">
            <span className="ce-mini-dot success" />
            PIPELINE STATUS
          </span>
          <span className="ce-mini-panel-body">{pipelineText}</span>
        </div>
        <div className="ce-user-badge">
          <span className="ce-user-avatar">HP</span>
          <span>
            <span className="ce-user-name">Himanshu P.</span>
            <span className="ce-user-role">Sales manager</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
