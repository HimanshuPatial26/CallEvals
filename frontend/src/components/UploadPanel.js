import { useRef, useState } from "react";
import { uploadCall } from "../api/client";

const LAST_AGENT_KEY = "callevals.lastAgentName";

export default function UploadPanel({ onUploaded }) {
  const [agentName, setAgentName] = useState(() => localStorage.getItem(LAST_AGENT_KEY) || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  async function handleChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!agentName.trim()) {
      setError("Enter the agent's name before uploading — every call needs a rep attributed to it.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const record = await uploadCall(file, agentName.trim());
      localStorage.setItem(LAST_AGENT_KEY, agentName.trim());
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
      <label className="upload-label" htmlFor="agent-name-input">
        Agent
      </label>
      <input
        id="agent-name-input"
        type="text"
        className="agent-name-input"
        placeholder="Rep's name"
        value={agentName}
        onChange={(e) => setAgentName(e.target.value)}
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
