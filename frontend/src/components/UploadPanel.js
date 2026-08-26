import { useEffect, useRef, useState } from "react";
import { listAgents, uploadCall } from "../api/client";
import BorderGlow from "./BorderGlow";

const LAST_AGENT_KEY = "callevals.lastAgentId";

// Lead attribution is a plain lead_id field, not a search/create widget.
// Any value works — a phone number, a CRM deal ID, whatever a manager
// already uses to track a prospect. First use creates the Lead; reusing
// the same value on a later call attributes it to the same one. Agent is
// a real roster dropdown, not free text, since agent_id must reference an
// existing Agent record.
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
      setError("Enter a lead ID before uploading — every call needs a lead attributed to it. Any value works; it'll be created if it's new.");
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
    <BorderGlow
      className="upload-panel"
      backgroundColor="#100e0c"
      borderRadius={14}
      glowColor="28 86 59"
      glowRadius={22}
      glowIntensity={1.3}
      coneSpread={30}
      edgeSensitivity={35}
      fillOpacity={0.45}
      colors={["#f0913c", "#ffb169", "#a0713c"]}
      animated
    >
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
        placeholder="Any ID — phone number, deal ID, anything"
        value={leadId}
        onChange={(e) => setLeadId(e.target.value)}
        disabled={busy}
      />

      <div className="upload-button-row">
        <label className="upload-button">
          <input
            ref={inputRef}
            type="file"
            accept="audio/*"
            onChange={handleChange}
            disabled={busy}
            className="upload-button-input"
          />
          {busy ? "Uploading…" : "Upload a call recording"}
        </label>
      </div>
      {error && <p className="error">{error}</p>}
    </BorderGlow>
  );
}
