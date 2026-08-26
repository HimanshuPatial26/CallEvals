import { useRef, useState } from "react";
import { uploadCall } from "../api/client";
import { IconUpload } from "../icons";

export default function UploadPanel({ onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  async function handleChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const record = await uploadCall(file);
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
      <label className={`upload-label${busy ? " busy" : ""}`}>
        <input ref={inputRef} type="file" accept="audio/*" onChange={handleChange} disabled={busy} />
        <IconUpload size={14} />
        {busy ? "Uploading…" : "Upload a call"}
      </label>
      {error && <p className="error">{error}</p>}
      <p className="hint">Dual-channel (stereo) files get real speaker separation. Mono files are labeled "unknown" — diarization is a Phase 1 add.</p>
    </div>
  );
}
