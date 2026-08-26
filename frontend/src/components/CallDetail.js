import { useState } from "react";
import TranscriptView from "./TranscriptView";
import NextStepsPanel from "./NextStepsPanel";
import ObjectionTags from "./ObjectionTags";
import { LogoMark, IconFailed } from "../icons";

export default function CallDetail({ call, onFeedbackChange }) {
  const [highlightTimestamp, setHighlightTimestamp] = useState(null);

  if (call.status === "processing") {
    return (
      <div className="call-processing">
        <LogoMark size={22} animated />
        <p className="hint">Transcribing and extracting… this can take a minute for longer calls.</p>
      </div>
    );
  }

  if (call.status === "failed") {
    return (
      <div className="call-failed">
        <IconFailed size={22} />
        <p className="error">Processing failed: {call.error}</p>
      </div>
    );
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
        </section>

        <section className="panel">
          <h3>Transcript</h3>
          <TranscriptView segments={call.transcript} highlightTimestamp={highlightTimestamp} />
        </section>
      </div>
    </div>
  );
}
