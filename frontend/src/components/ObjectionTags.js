import { submitFeedback } from "../api/client";

export default function ObjectionTags({ callId, objections, feedback, onJumpToTimestamp, onFeedbackChange }) {
  function feedbackFor(index) {
    return feedback.find((f) => f.item_type === "objection" && f.item_index === index);
  }

  async function handleFeedback(index, confirmed) {
    const record = await submitFeedback(callId, "objection", index, confirmed);
    onFeedbackChange(record.feedback);
  }

  if (objections.length === 0) {
    return <p className="hint">No objections tagged on this call.</p>;
  }

  return (
    <ul className="item-list">
      {objections.map((objection, i) => {
        const existing = feedbackFor(i);
        return (
          <li key={i} className="extracted-item">
            <button className={`jump-link objection-tag tag-${objection.category}`} onClick={() => onJumpToTimestamp(objection.source_timestamp)}>
              {objection.category}
            </button>
            <span className="item-meta">"{objection.quote}" · confidence {(objection.confidence * 100).toFixed(0)}%</span>
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
