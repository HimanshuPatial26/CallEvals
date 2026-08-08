import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { listCalls } from "./api/client";
import UploadPanel from "./components/UploadPanel";
import CallList from "./components/CallList";
import CallDetail from "./components/CallDetail";
import AgentPerformancePage from "./components/AgentPerformancePage";
import OrganizationPage from "./components/OrganizationPage";
import LeadPipelinePage from "./components/LeadPipelinePage";

function App() {
  const [tab, setTab] = useState("calls");
  const [calls, setCalls] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);
  const [presetAgentId, setPresetAgentId] = useState(null);

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

  return (
    <div className="app">
      <header className="app-header">
        <h1>CallEvals</h1>
        <p className="subtitle">Sales call review — Phase 0</p>
        <nav className="app-nav">
          <button className={tab === "calls" ? "active" : ""} onClick={() => setTab("calls")}>
            Calls
          </button>
          <button className={tab === "agents" ? "active" : ""} onClick={() => setTab("agents")}>
            Agent Performance
          </button>
          <button className={tab === "organization" ? "active" : ""} onClick={() => setTab("organization")}>
            Organization
          </button>
          <button className={tab === "leads" ? "active" : ""} onClick={() => setTab("leads")}>
            Leads
          </button>
        </nav>
      </header>

      {error && <p className="error">{error}</p>}

      {tab === "calls" ? (
        <div className="app-body">
          <aside className="sidebar">
            <UploadPanel onUploaded={handleUploaded} />
            <CallList calls={calls} selectedId={selectedId} onSelect={setSelectedId} />
          </aside>

          <main className="main">
            {selectedCall ? (
              <CallDetail call={selectedCall} onFeedbackChange={handleFeedbackChange} />
            ) : (
              <p className="hint">Select a call to review it.</p>
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
  );
}

export default App;
