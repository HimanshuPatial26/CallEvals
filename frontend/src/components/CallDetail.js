import { useState } from "react";
import TranscriptView from "./TranscriptView";
import NextStepsPanel from "./NextStepsPanel";
import ObjectionTags from "./ObjectionTags";
import CallInsightsPanel from "./CallInsightsPanel";

export default function CallDetail({ call, onFeedbackChange }) {
  const [highlightTimestamp, setHighlightTimestamp] = useState(null);

  if (call.status === "processing") {
    return <p className="hint">Transcribing and extracting… this can take a minute for longer calls.</p>;
  }

  if (call.status === "failed") {
    return <p className="error">Processing failed: {call.error}</p>;
  }

  return (
    <div className="call-detail">
      <section className="panel">
        <h3>Summary</h3>
        <p>{call.extraction.summary}</p>
      </section>

      <div className="call-detail-columns">
        <section className="panel">
          <h3>Next steps</h3>
          <NextStepsPanel
            callId={call.id}
            nextSteps={call.extraction.next_steps}
            feedback={call.feedback}
            onJumpToTimestamp={setHighlightTimestamp}
            onFeedbackChange={onFeedbackChange}
          />

          <h3>Objections</h3>
          <ObjectionTags
            callId={call.id}
            objections={call.extraction.objections}
            feedback={call.feedback}
            onJumpToTimestamp={setHighlightTimestamp}
            onFeedbackChange={onFeedbackChange}
          />

          <h3>Call insights</h3>
          <CallInsightsPanel insights={call.insights} />
        </section>

        <section className="panel">
          <h3>Transcript</h3>
          <TranscriptView segments={call.transcript} highlightTimestamp={highlightTimestamp} />
        </section>
      </div>
    </div>
  );
}
