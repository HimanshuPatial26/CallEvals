import { useEffect, useRef, useState } from "react";
import { listAgents, uploadCall } from "../api/client";

const LAST_AGENT_KEY = "callevals.lastAgentId";

// Lead attribution is a plain lead_id field, not a search/create widget —
// leads are created via the API for now (ROADMAP.md Phase A decision).
// Agent is a real roster dropdown, not free text, since agent_id must
// reference an existing Agent record.
export default function UploadPanel({ onUploaded }) {
  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState(() => localStorage.getItem(LAST_AGENT_KEY) || "");
  const [leadId, setLeadId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    listAgents()
      .then((data) => {
        setAgents(data);
        if (!agentId && data.length > 0) setAgentId(data[0].id);
      })
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!agentId) {
      setError("Select an agent before uploading — every call needs a rep attributed to it.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (!leadId.trim()) {
      setError("Enter a lead ID before uploading — every call needs a lead attributed to it (create one via POST /api/leads).");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const record = await uploadCall(file, agentId, leadId.trim());
      localStorage.setItem(LAST_AGENT_KEY, agentId);
      onUploaded(record);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="panel upload-panel">
      <label className="upload-label" htmlFor="agent-select">
        Agent
      </label>
      <select id="agent-select" className="agent-name-input" value={agentId} onChange={(e) => setAgentId(e.target.value)} disabled={busy}>
        {agents.length === 0 && <option value="">No agents in roster yet</option>}
        {agents.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
            {a.team_name ? ` — ${a.team_name}` : ""}
          </option>
        ))}
      </select>

      <label className="upload-label" htmlFor="lead-id-input">
        Lead ID
      </label>
      <input
        id="lead-id-input"
        type="text"
        className="agent-name-input"
        placeholder="Existing lead's ID"
        value={leadId}
        onChange={(e) => setLeadId(e.target.value)}
        disabled={busy}
      />

      <label className="upload-label">
        <input ref={inputRef} type="file" accept="audio/*" onChange={handleChange} disabled={busy} />
        {busy ? "Uploading…" : "Upload a call recording"}
      </label>
      {error && <p className="error">{error}</p>}
      <p className="hint">Dual-channel (stereo) files get real speaker separation. Mono files are labeled "unknown" — diarization is a Phase 1 add.</p>
    </div>
  );
}
