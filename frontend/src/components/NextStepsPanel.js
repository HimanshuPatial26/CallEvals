import { submitFeedback } from "../api/client";
import { IconReady } from "../icons";

export default function NextStepsPanel({ callId, nextSteps, feedback, autoflagThreshold, onJump, onFeedbackChange }) {
  function feedbackFor(index) {
    return feedback.find((f) => f.item_type === "next_step" && f.item_index === index);
  }

  async function handleFeedback(index, confirmed) {
    const existing = feedbackFor(index);
    const nextValue = existing?.confirmed === confirmed ? !confirmed : confirmed;
    const record = await submitFeedback(callId, "next_step", index, nextValue);
    onFeedbackChange(record.feedback);
  }

  if (nextSteps.length === 0) {
    return (
      <div className="ce-step-list">
        <span className="hint">No next steps extracted from this call.</span>
      </div>
    );
  }

  return (
    <div className="ce-step-list">
      {nextSteps.map((step, i) => {
        const existing = feedbackFor(i);
        const confPct = Math.round(step.confidence * 100);
        return (
          <div key={i} className="ce-step">
            <div className="ce-step-row">
              <IconReady size={16} style={{ marginTop: 2, flex: "none" }} />
              <span className="ce-step-desc">{step.description}</span>
              <span className="ce-step-conf" style={{ color: step.confidence >= autoflagThreshold / 100 ? "var(--ce-success)" : "var(--ce-accent)" }}>
                {confPct}%
              </span>
            </div>
            <div className="ce-step-meta">
              <span className="ce-chip">owner: {step.owner}</span>
              <span className="ce-chip">due: {step.due || "not stated"}</span>
              {step.source_timestamp != null && (
                <button type="button" className="ce-jump-chip" onClick={() => onJump(step.source_timestamp)}>
                  ↳ {formatJump(step.source_timestamp)}
                </button>
              )}
              <div className="ce-fb-actions">
                <button
                  type="button"
                  className={`ce-fb-btn ok${existing?.confirmed === true ? " active" : ""}`}
                  onClick={() => handleFeedback(i, true)}
                >
                  Correct
                </button>
                <button
                  type="button"
                  className={`ce-fb-btn no${existing?.confirmed === false ? " active" : ""}`}
                  onClick={() => handleFeedback(i, false)}
                >
                  Wrong
                </button>
              </div>
            </div>
          </div>
        );
      })}
      <span className="hint">Every confirm or reject is one labelled data point behind the extraction-precision metric.</span>
    </div>
  );
}

function formatJump(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}
