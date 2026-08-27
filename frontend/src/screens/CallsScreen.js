import { useEffect, useRef, useState } from "react";
import { getCall } from "../api/client";
import AudioPlayer from "../components/AudioPlayer";
import NextStepsPanel from "../components/NextStepsPanel";
import ObjectionsList from "../components/ObjectionsList";
import TranscriptView from "../components/TranscriptView";
import CoachingPanel from "../components/CoachingPanel";
import ConversationShapePanel from "../components/ConversationShapePanel";
import LeadCard from "../components/LeadCard";
import ScoreCard from "../components/ScoreCard";
import { LogoMark, IconFailed, IconProcessing, IconRetry } from "../icons";
import { fmtTime } from "../utils/format";

const TABS = [
  { key: "summary", label: "Summary & next steps" },
  { key: "transcript", label: "Transcript" },
  { key: "objections", label: "Objections" },
  { key: "coaching", label: "Coaching" },
];

export default function CallsScreen({
  calls,
  selectedId,
  agentsById,
  leadsById,
  settings,
  onGoHistory,
  onOpenLead,
}) {
  const [tab, setTab] = useState("summary");
  const [activeTime, setActiveTime] = useState(0);
  const [detail, setDetail] = useState(null);
  const seekToRef = useRef(null);

  const listEntry = calls.find((c) => c.id === selectedId);

  useEffect(() => {
    setTab("summary");
    setActiveTime(0);
    setDetail(null);
    if (!selectedId) return;
    let cancelled = false;
    getCall(selectedId).then((data) => {
      if (!cancelled) setDetail(data);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  // Keep feedback/status current from the polled list without losing the
  // once-fetched transcript/extraction payload (list rows omit nothing, but this
  // avoids an extra round trip on every poll tick).
  useEffect(() => {
    if (listEntry && detail && listEntry.status !== detail.status) {
      getCall(selectedId).then(setDetail);
    }
  }, [listEntry, detail, selectedId]);

  function handleJump(time) {
    seekToRef.current?.(time);
    setActiveTime(time);
  }

  function handleJumpToTranscript(time) {
    setTab("transcript");
    seekToRef.current?.(time);
    setActiveTime(time);
  }

  function handleFeedbackChange(feedback) {
    setDetail((d) => (d ? { ...d, feedback } : d));
  }

  if (!selectedId) {
    return (
      <div className="ce-content">
        <div className="ce-state-screen ce-state-empty">
          <LogoMark size={34} />
          <span className="ce-state-title">No call in review.</span>
          <span className="ce-state-body">Upload a recording, or open one from call history.</span>
          <button type="button" className="ce-btn" style={{ marginTop: 6 }} onClick={onGoHistory}>
            Open call history
          </button>
        </div>
      </div>
    );
  }

  const call = detail || listEntry;
  if (!call) {
    return (
      <div className="ce-content">
        <div className="ce-state-screen">
          <IconProcessing size={28} />
          <span className="ce-state-title">Loading…</span>
        </div>
      </div>
    );
  }

  if (call.status !== "done") {
    return (
      <div className="ce-content">
        <div className="ce-state-screen">
          {call.status === "failed" ? <IconFailed size={34} /> : <IconProcessing size={34} />}
          <span className="ce-state-title">
            {call.status === "failed" ? "Speaker separation failed" : call.status === "processing" ? "Processing this call" : "Queued for processing"}
          </span>
          <span className="ce-state-body">
            {call.status === "failed" ? call.error : "Transcribing and extracting — this can take a minute for longer calls."}
          </span>
          {call.status === "failed" && (
            <button type="button" className="ce-btn" style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 7 }} disabled title="Diarization fallback isn't built yet">
              <IconRetry size={15} /> Retry with diarization fallback
            </button>
          )}
        </div>
      </div>
    );
  }

  const agent = agentsById[call.agent_id];
  const lead = leadsById[call.lead_id];
  const nextSteps = call.extraction?.next_steps || [];
  const objections = call.extraction?.objections || [];
  const markers = [
    ...objections.filter((o) => o.source_timestamp != null).map((o) => ({ ts: o.source_timestamp, color: "var(--ce-accent)" })),
    ...nextSteps.filter((s) => s.source_timestamp != null).map((s) => ({ ts: s.source_timestamp, color: "var(--ce-success)" })),
  ];
  const autoflagThreshold = settings?.autoflag_threshold ?? 88;
  // Ground truth from the backend (app/asr/base.py's speaker_source), not a
  // frontend guess — channel_split (hard separation) and diarization (a
  // voice-clustering heuristic that can be wrong) both happen on dual-channel
  // calls when the container didn't actually separate, so dual_channel alone
  // can't tell you which one a call actually got.
  const SPEAKER_SOURCE_LABEL = {
    channel_split: "SPEAKER-SEPARATED",
    diarization: "DIARIZED · HEURISTIC",
    unknown: "SPEAKERS UNKNOWN",
  };
  const speakerLabel = SPEAKER_SOURCE_LABEL[call.speaker_source] || "SPEAKERS UNKNOWN";

  return (
    <div className="ce-content">
      <div className="ce-call-detail">
        <div className="ce-call-detail-head">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="ce-call-title-row">
              <span className="ce-call-filename">{call.filename}</span>
              <span className="ce-chip ce-chip-success">Ready</span>
              <span className="ce-chip">{call.dual_channel ? "dual-channel" : "mono"}</span>
            </div>
            <span className="ce-call-submeta">
              {agent?.name || "Unassigned"} · {fmtTime(call.duration)}
              {lead ? ` · ${lead.name} · ${lead.unit || "no unit stated"}` : ""}
            </span>
          </div>
          <div className="ce-call-actions">
            <button type="button" className="ce-btn" disabled title="Not available in Phase 0">Share with rep</button>
            <button type="button" className="ce-btn" disabled title="Not available in Phase 0">Log to CRM</button>
          </div>
        </div>

        <AudioPlayer callId={call.id} duration={call.duration} markers={markers} onTimeChange={setActiveTime} seekToRef={seekToRef} />

        <div className="ce-call-body">
          <div className="ce-call-main">
            <div className="ce-tabs">
              {TABS.map((t) => (
                <button key={t.key} type="button" className={`ce-tab${tab === t.key ? " active" : ""}`} onClick={() => setTab(t.key)}>
                  {t.label}
                </button>
              ))}
            </div>

            {tab === "summary" && (
              <div className="ce-tab-panel">
                <div className="ce-card">
                  <div className="ce-card-header">
                    <span className="ce-card-title">Call summary</span>
                    <span className="ce-card-tag">F2 · UNDER 150 WORDS</span>
                  </div>
                  <div className="ce-card-body">{call.extraction?.summary}</div>
                </div>
                <div className="ce-card">
                  <div className="ce-card-header">
                    <span className="ce-card-title">Next steps</span>
                    <span className="ce-card-tag">F3 · CONFIRM OR REJECT</span>
                  </div>
                  <NextStepsPanel
                    callId={call.id}
                    nextSteps={nextSteps}
                    feedback={call.feedback}
                    autoflagThreshold={autoflagThreshold}
                    onJump={handleJumpToTranscript}
                    onFeedbackChange={handleFeedbackChange}
                  />
                </div>
              </div>
            )}

            {tab === "transcript" && (
              <div className="ce-card ce-tab-panel">
                <div className="ce-card-header">
                  <span className="ce-card-title">Transcript</span>
                  <span className="ce-card-tag">{speakerLabel}</span>
                  <span className="hint" style={{ marginLeft: "auto" }}>Click any line to jump the audio</span>
                </div>
                <TranscriptView
                  segments={call.transcript}
                  agentName={agent?.name}
                  leadName={lead?.name}
                  activeTime={activeTime}
                  onJump={handleJump}
                />
              </div>
            )}

            {tab === "objections" && (
              <ObjectionsList
                callId={call.id}
                objections={objections}
                feedback={call.feedback}
                autoflagThreshold={autoflagThreshold}
                onJump={handleJumpToTranscript}
                onFeedbackChange={handleFeedbackChange}
              />
            )}

            {tab === "coaching" && (
              <CoachingPanel flags={call.flags} segments={call.transcript} nextSteps={nextSteps} onJump={handleJumpToTranscript} />
            )}
          </div>

          <div className="ce-call-rail">
            {settings?.composite_score_enabled && <ScoreCard />}
            <ConversationShapePanel shape={call.shape} />
            <LeadCard lead={lead} callCount={lead?.call_count ?? 0} onOpenLead={() => lead && onOpenLead(lead.id)} />
          </div>
        </div>
      </div>
    </div>
  );
}
