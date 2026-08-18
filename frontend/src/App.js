import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import { listCalls } from "./api/client";
import UploadPanel from "./components/UploadPanel";
import CallList from "./components/CallList";
import CallDetail from "./components/CallDetail";
import CallEmptyState from "./components/CallEmptyState";
import AgentPerformancePage from "./components/AgentPerformancePage";
import OrganizationPage from "./components/OrganizationPage";
import LeadPipelinePage from "./components/LeadPipelinePage";
import LineSidebar from "./components/LineSidebar";

const NAV_ITEMS = [
  { key: "calls", label: "Calls", crumb: "LIBRARY / CALLS", title: "Call inbox" },
  { key: "agents", label: "Agent Performance", crumb: "QUALITY / AGENT", title: "Agent performance" },
  { key: "organization", label: "Organization", crumb: "ANALYTICS / OVERVIEW", title: "Organization overview" },
  { key: "leads", label: "Leads", crumb: "PIPELINE / LEADS", title: "Lead pipeline" },
];

function App() {
  const [tab, setTab] = useState("calls");
  const [calls, setCalls] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);
  const [presetAgentId, setPresetAgentId] = useState(null);
  const [assistOpen, setAssistOpen] = useState(false);

  function goToAgent(agentId) {
    setPresetAgentId(agentId);
    setTab("agents");
  }

  const refresh = useCallback(async () => {
    try {
      const data = await listCalls();
      setCalls(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const hasProcessing = calls.some((c) => c.status === "processing");
    const interval = setInterval(refresh, hasProcessing ? 3000 : 8000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, calls.length]);

  function handleUploaded(record) {
    setCalls((prev) => [record, ...prev]);
    setSelectedId(record.id);
  }

  function handleFeedbackChange(newFeedback) {
    setCalls((prev) => prev.map((c) => (c.id === selectedId ? { ...c, feedback: newFeedback } : c)));
  }

  const selectedCall = calls.find((c) => c.id === selectedId);
  const processingCount = useMemo(() => calls.filter((c) => c.status === "processing").length, [calls]);
  const active = NAV_ITEMS.find((item) => item.key === tab) || NAV_ITEMS[0];
  const navLabels = NAV_ITEMS.map((item) => (item.key === "calls" ? `${item.label} · ${calls.length}` : item.label));
  const activeNavIndex = NAV_ITEMS.findIndex((item) => item.key === tab);

  return (
    <div className="app">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">CE</div>
          <div>
            <div className="brand-name">CallEvals</div>
            <div className="brand-tagline">CALL INTELLIGENCE</div>
          </div>
        </div>

        <div className="side-nav">
          <div className="side-nav-heading">NAVIGATION</div>
          <LineSidebar
            // Remounted on every tab change (including ones that don't
            // originate from clicking the sidebar itself, e.g. the
            // Organization page's "drill into agent" link): LineSidebar
            // only exposes an initial defaultActive, not a controlled
            // active index, so a fresh mount is how its highlighted item
            // stays in sync with which page is actually showing.
            key={tab}
            items={navLabels}
            accentColor="#f0923e"
            textColor="#9db6b3"
            markerColor="#56716e"
            showIndex
            showMarker
            proximityRadius={55}
            maxShift={10}
            falloff="smooth"
            markerLength={20}
            markerGap={8}
            tickScale={0.5}
            scaleTick
            itemGap={22}
            fontSize={0.92}
            smoothing={80}
            defaultActive={activeNavIndex}
            onItemClick={(index) => setTab(NAV_ITEMS[index].key)}
          />
        </div>

        <div className="model-status">
          <div className="model-status-head">
            <span className={`status-dot-pulse${processingCount === 0 ? " idle" : ""}`} />
            <span className="model-status-label">PIPELINE STATUS</span>
          </div>
          <div className="model-status-text">
            {processingCount > 0 ? (
              <>
                Transcribing <strong>{processingCount}</strong> call{processingCount === 1 ? "" : "s"}…
              </>
            ) : (
              "All uploaded calls processed."
            )}
          </div>
          {processingCount > 0 && (
            <div className="model-status-bar">
              <div className="model-status-bar-fill" />
            </div>
          )}
        </div>
      </aside>

      <div className="app-shell">
        <header className="app-topbar">
          <div>
            <div className="topbar-crumb">{active.crumb}</div>
            <div className="topbar-title">{active.title}</div>
          </div>
          <button className="assist-button" onClick={() => setAssistOpen(true)}>
            <span className="assist-button-dot" />
            Ask CallEvals
          </button>
        </header>

        {error && <p className="error" style={{ margin: "1rem 1.75rem 0" }}>{error}</p>}

        <div className="app-content">
          {tab === "calls" ? (
            <div className="app-body">
              <aside className="sidebar">
                <UploadPanel onUploaded={handleUploaded} />
                <CallList calls={calls} selectedId={selectedId} onSelect={setSelectedId} />
              </aside>

              <main className="main">
                {selectedCall ? (
                  <CallDetail key={selectedCall.id} call={selectedCall} onFeedbackChange={handleFeedbackChange} />
                ) : (
                  <CallEmptyState />
                )}
              </main>
            </div>
          ) : tab === "agents" ? (
            <AgentPerformancePage initialAgentId={presetAgentId} />
          ) : tab === "organization" ? (
            <OrganizationPage onDrillToAgent={goToAgent} />
          ) : (
            <LeadPipelinePage />
          )}
        </div>
      </div>

      {assistOpen && (
        <div className="assist-panel">
          <div className="assist-panel-head">
            <span className="assist-panel-title">ASK CALLEVALS</span>
            <button className="assist-panel-close" onClick={() => setAssistOpen(false)}>
              ✕
            </button>
          </div>
          <div className="assist-panel-body">
            <p>
              A natural-language assistant over your call data isn't built yet — this is a placeholder for where it
              would live, not a working feature. Today, the Agent Performance, Organization, and Leads tabs already
              surface the real underlying numbers (conversion, objections, lost reasons, coaching recommendations)
              this would eventually summarize on demand.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
