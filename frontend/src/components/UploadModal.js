import { useRef, useState } from "react";
import { getCall, uploadCall } from "../api/client";
import { IconReady, IconFailed, IconUpload, IconProcessing } from "../icons";

const POLL_MS = 2000;

function StageRow({ label, meta, state }) {
  let icon = <span style={{ width: 16, height: 16, borderRadius: "50%", border: "1.5px solid var(--ce-border-control)", display: "block" }} />;
  if (state === "done") icon = <IconReady size={16} />;
  if (state === "active") icon = <IconProcessing size={16} />;
  if (state === "failed") icon = <IconFailed size={16} />;
  return (
    <div className={`ce-stage-row${state === "active" ? " active" : ""}${state === "done" ? " done" : ""}`}>
      <span className="ce-stage-icon">{icon}</span>
      <span className="ce-stage-label">{label}</span>
      {meta && <span className="ce-stage-meta">{meta}</span>}
    </div>
  );
}

export default function UploadModal({ onClose, onDone }) {
  const [agentName, setAgentName] = useState("");
  const [leadPhone, setLeadPhone] = useState("");
  const [leadName, setLeadName] = useState("");
  const [leadUnit, setLeadUnit] = useState("");
  const [leadBudget, setLeadBudget] = useState("");
  const [file, setFile] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle | uploading | processing | done | failed
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  function handleFileChange(e) {
    const f = e.target.files[0];
    if (f) setFile(f);
  }

  async function startUpload() {
    if (!file) return;
    setPhase("uploading");
    setError(null);
    try {
      const created = await uploadCall(file, { agentName, leadPhone, leadName, leadUnit, leadBudget });
      setRecord(created);
      setPhase("processing");
      poll(created.id);
    } catch (err) {
      setError(err.message);
      setPhase("idle");
    }
  }

  function poll(callId) {
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getCall(callId);
        setRecord(updated);
        if (updated.status === "done") {
          clearInterval(pollRef.current);
          setPhase("done");
        } else if (updated.status === "failed") {
          clearInterval(pollRef.current);
          setPhase("failed");
        }
      } catch {
        // transient network error — keep polling
      }
    }, POLL_MS);
  }

  function handleClose() {
    if (pollRef.current) clearInterval(pollRef.current);
    onClose();
  }

  function handleReview() {
    if (pollRef.current) clearInterval(pollRef.current);
    onDone(record.id);
  }

  return (
    <div className="ce-modal-overlay" onClick={handleClose}>
      <div className="ce-modal ce-modal-sm" onClick={(e) => e.stopPropagation()}>
        <div className="ce-modal-header">
          <span className="ce-card-title">Upload a call recording</span>
          <button type="button" className="ce-modal-close" onClick={handleClose}>✕</button>
        </div>
        <div className="ce-modal-body">
          {phase === "idle" && (
            <>
              <div className="ce-upload-fields">
                <div className="ce-upload-field">
                  <span className="ce-upload-field-label">Agent</span>
                  <input className="ce-text-input" value={agentName} onChange={(e) => setAgentName(e.target.value)} placeholder="Agent name" />
                </div>
                <div className="ce-upload-field">
                  <span className="ce-upload-field-label">Lead phone</span>
                  <input className="ce-text-input" value={leadPhone} onChange={(e) => setLeadPhone(e.target.value)} placeholder="+971 50 …" />
                </div>
              </div>
              <div className="ce-upload-fields">
                <div className="ce-upload-field">
                  <span className="ce-upload-field-label">Lead name</span>
                  <input className="ce-text-input" value={leadName} onChange={(e) => setLeadName(e.target.value)} placeholder="Optional" />
                </div>
                <div className="ce-upload-field">
                  <span className="ce-upload-field-label">Unit</span>
                  <input className="ce-text-input" value={leadUnit} onChange={(e) => setLeadUnit(e.target.value)} placeholder="Optional" />
                </div>
              </div>
              <div className="ce-upload-fields">
                <div className="ce-upload-field">
                  <span className="ce-upload-field-label">Budget</span>
                  <input className="ce-text-input" value={leadBudget} onChange={(e) => setLeadBudget(e.target.value)} placeholder="Optional" />
                </div>
              </div>
              <label className="ce-dropzone">
                <input type="file" accept="audio/*" onChange={handleFileChange} />
                <IconUpload size={26} />
                <span className="ce-state-title" style={{ fontSize: 14 }}>{file ? file.name : "Drop a recording, or browse"}</span>
                <span className="ce-state-body" style={{ fontSize: 11 }}>
                  Stereo WAV or MP3 preferred — separate channels give perfect speaker separation. Mono files are
                  transcribed but not speaker-split.
                </span>
              </label>
              {error && <span className="ce-upload-error">{error}</span>}
              <button type="button" className="ce-btn ce-btn-primary" disabled={!file} onClick={startUpload}>
                {file ? `Upload · ${file.name}` : "Choose a file first"}
              </button>
            </>
          )}

          {phase !== "idle" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="ce-upload-progress-head">
                <IconProcessing size={22} className={phase === "processing" || phase === "uploading" ? "" : undefined} />
                <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="ce-upload-progress-file">{file?.name}</span>
                  <span className="ce-upload-progress-sub">
                    {phase === "uploading" && "Uploading…"}
                    {phase === "processing" && "Transcribing and extracting — this can take a minute."}
                    {phase === "done" && `Ready · ${record?.dual_channel ? "dual-channel" : "mono"}`}
                    {phase === "failed" && "Processing failed"}
                  </span>
                </span>
              </div>
              <div className="ce-stage-list">
                <StageRow label="Uploading file" meta={phase !== "uploading" ? "done" : ""} state={phase === "uploading" ? "active" : "done"} />
                <StageRow
                  label="Transcribing & extracting"
                  meta={phase === "processing" ? "in progress" : phase === "done" ? "done" : phase === "failed" ? "failed" : ""}
                  state={phase === "processing" ? "active" : phase === "done" ? "done" : phase === "failed" ? "failed" : "todo"}
                />
                <StageRow
                  label={phase === "failed" ? "Failed" : "Ready to review"}
                  meta={phase === "failed" ? record?.error : ""}
                  state={phase === "done" ? "done" : phase === "failed" ? "failed" : "todo"}
                />
              </div>
              {phase === "done" && (
                <button type="button" className="ce-btn ce-btn-primary" onClick={handleReview}>Review the call</button>
              )}
              {phase === "failed" && (
                <button type="button" className="ce-btn" onClick={handleClose}>Close</button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
