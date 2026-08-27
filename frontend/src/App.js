import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { getSettings, listAgents, listCalls, listLeads } from "./api/client";
import Sidebar from "./components/Sidebar";
import TopHeader from "./components/TopHeader";
import UploadModal from "./components/UploadModal";
import LeadModal from "./components/LeadModal";
import CallPreviewModal from "./components/CallPreviewModal";
import CallsScreen from "./screens/CallsScreen";
import CallHistoryScreen from "./screens/CallHistoryScreen";
import AgentsScreen from "./screens/AgentsScreen";
import OrgScreen from "./screens/OrgScreen";
import LeadsScreen from "./screens/LeadsScreen";
import RubricScreen from "./screens/RubricScreen";

const SCREEN_TITLES = {
  calls: ["LIBRARY / CALL IN REVIEW", "Calls"],
  history: ["LIBRARY / HISTORY", "Call history"],
  agents: ["TEAM / AGENT PERFORMANCE", "Agent performance"],
  org: ["TEAM / ORGANIZATION", "Organization"],
  leads: ["PIPELINE / LEADS", "Leads"],
  rubric: ["SETTINGS / RUBRIC", "Rubric & flags"],
};

function App() {
  const [screen, setScreen] = useState("calls");
  const [calls, setCalls] = useState([]);
  const [agents, setAgents] = useState([]);
  const [leads, setLeads] = useState([]);
  const [settings, setSettings] = useState(null);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [openLeadId, setOpenLeadId] = useState(null);
  const [previewCallId, setPreviewCallId] = useState(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [callsData, agentsData, leadsData] = await Promise.all([listCalls(), listAgents(), listLeads()]);
      setCalls(callsData);
      setAgents(agentsData);
      setLeads(leadsData);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    getSettings().then(setSettings).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refresh();
    const hasProcessing = calls.some((c) => c.status === "processing" || c.status === "queued");
    const interval = setInterval(refresh, hasProcessing ? 3000 : 8000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, calls.length]);

  const agentsById = Object.fromEntries(agents.map((a) => [a.id, a]));
  const leadsById = Object.fromEntries(leads.map((l) => [l.id, l]));

  function handleUploadDone(callId) {
    setUploadOpen(false);
    setScreen("calls");
    setSelectedCallId(callId);
    refresh();
  }

  function openAgent(agentId) {
    setSelectedAgentId(agentId);
    setScreen("agents");
  }

  const processingCount = calls.filter((c) => c.status === "processing").length;
  const failedCount = calls.filter((c) => c.status === "failed").length;
  const queuedCount = calls.filter((c) => c.status === "queued").length;
  const doneCount = calls.filter((c) => c.status === "done").length;
  const coverage = calls.length ? Math.round((100 * doneCount) / calls.length) : 0;

  const [crumb, title] =
    screen === "calls" && selectedCallId
      ? ["LIBRARY / CALL IN REVIEW", calls.find((c) => c.id === selectedCallId)?.filename || "Call in review"]
      : SCREEN_TITLES[screen];

  return (
    <div className="ce-app">
      <Sidebar
        screen={screen}
        onNavigate={setScreen}
        counts={{ history: calls.length, agents: agents.length, org: agents.length, leads: leads.length }}
        repPrivateMode={settings?.rep_private_mode ?? true}
        pipelineText={`${processingCount} processing, ${failedCount} failed, ${queuedCount} queued. Coverage ${coverage}% overall.`}
      />

      <div className="ce-main">
        <TopHeader crumb={crumb} title={title} onUpload={() => setUploadOpen(true)} />

        {error && <p className="error" style={{ margin: "16px 24px 0" }}>{error}</p>}

        {screen === "calls" && (
          <CallsScreen
            calls={calls}
            selectedId={selectedCallId}
            agentsById={agentsById}
            leadsById={leadsById}
            settings={settings}
            onGoHistory={() => setScreen("history")}
            onOpenLead={setOpenLeadId}
          />
        )}

        {screen === "history" && (
          <CallHistoryScreen
            calls={calls}
            agentsById={agentsById}
            onOpenCall={(id) => {
              setSelectedCallId(id);
              setScreen("calls");
            }}
          />
        )}

        {screen === "agents" && (
          <AgentsScreen
            agents={agents}
            repPrivateMode={settings?.rep_private_mode ?? true}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />
        )}

        {screen === "org" && (
          <OrgScreen repPrivateMode={settings?.rep_private_mode ?? true} onOpenAgent={openAgent} onOpenRubric={() => setScreen("rubric")} />
        )}

        {screen === "leads" && <LeadsScreen leads={leads} onOpenLead={setOpenLeadId} />}

        {screen === "rubric" && <RubricScreen settings={settings} onSettingsChange={setSettings} />}
      </div>

      {openLeadId && (
        <LeadModal leadId={openLeadId} onClose={() => setOpenLeadId(null)} onOpenCall={setPreviewCallId} />
      )}

      {previewCallId && (
        <CallPreviewModal
          callId={previewCallId}
          onClose={() => setPreviewCallId(null)}
          onOpenFull={(callId) => {
            setPreviewCallId(null);
            setOpenLeadId(null);
            setSelectedCallId(callId);
            setScreen("calls");
          }}
        />
      )}

      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} onDone={handleUploadDone} />}
    </div>
  );
}

export default App;
