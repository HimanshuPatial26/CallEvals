import { submitFeedback } from "../api/client";
import ConfidenceBar from "./ConfidenceBar";

export default function NextStepsPanel({ callId, nextSteps, feedback, onJumpToTimestamp, onFeedbackChange }) {
  function feedbackFor(index) {
    return feedback.find((f) => f.item_type === "next_step" && f.item_index === index);
  }

  async function handleFeedback(index, confirmed) {
    const record = await submitFeedback(callId, "next_step", index, confirmed);
    onFeedbackChange(record.feedback);
  }

  if (nextSteps.length === 0) {
    return <p className="hint">No next steps extracted from this call.</p>;
  }

  return (
    <ul className="item-list">
      {nextSteps.map((step, i) => {
        const existing = feedbackFor(i);
        return (
          <li key={i} className="extracted-item">
            <button className="jump-link" onClick={() => onJumpToTimestamp(step.source_timestamp)}>
              {step.description}
            </button>
            <span className="item-meta">
              <span>
                {step.owner}
                {step.due ? ` · due ${step.due}` : ""}
              </span>
              <ConfidenceBar value={step.confidence} />
            </span>
            <div className="feedback-buttons">
              <button
                className={existing?.confirmed === true ? "active confirm" : "confirm"}
                onClick={() => handleFeedback(i, true)}
              >
                Correct
              </button>
              <button
                className={existing?.confirmed === false ? "active reject" : "reject"}
                onClick={() => handleFeedback(i, false)}
              >
                Wrong
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
