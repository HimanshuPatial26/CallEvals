import { submitFeedback } from "../api/client";
import { IconObjection } from "../icons";

export default function ObjectionsList({ callId, objections, feedback, autoflagThreshold, onJump, onFeedbackChange }) {
  function feedbackFor(index) {
    return feedback.find((f) => f.item_type === "objection" && f.item_index === index);
  }

  async function handleFeedback(index, confirmed) {
    const existing = feedbackFor(index);
    const nextValue = existing?.confirmed === confirmed ? !confirmed : confirmed;
    const record = await submitFeedback(callId, "objection", index, nextValue);
    onFeedbackChange(record.feedback);
  }

  if (objections.length === 0) {
    return (
      <div className="ce-dashed-empty">
        <span className="ce-state-title">No objections detected.</span>
        <span className="ce-state-body">
          Extraction stays quiet rather than inventing one. A false objection costs more manager trust than a missed one.
        </span>
      </div>
    );
  }

  return (
    <div className="ce-tab-panel">
      {objections.map((objection, i) => {
        const existing = feedbackFor(i);
        const confPct = Math.round(objection.confidence * 100);
        return (
          <div key={i} className="ce-card">
            <div className="ce-card-header">
              <IconObjection size={16} />
              <span className="ce-chip ce-chip-accent">{objection.category.toUpperCase()}</span>
              <span className="ce-shape-value" style={{ marginLeft: "auto", color: confPct >= autoflagThreshold ? "var(--ce-success)" : "var(--ce-accent)" }}>
                {confPct}% conf
              </span>
            </div>
            <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <span className="ce-objection-quote">&ldquo;{objection.quote}&rdquo;</span>
              <div className="ce-objection-footer">
                {objection.source_timestamp != null && (
                  <button type="button" className="ce-jump-chip" onClick={() => onJump(objection.source_timestamp)}>
                    ↳ {formatJump(objection.source_timestamp)} in transcript
                  </button>
                )}
                <span className="hint">customer's own words, not a paraphrase</span>
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
          </div>
        );
      })}
    </div>
  );
}

function formatJump(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}
