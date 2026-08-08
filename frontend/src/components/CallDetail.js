import { useState } from "react";
import TranscriptView from "./TranscriptView";
import NextStepsPanel from "./NextStepsPanel";
import ObjectionTags from "./ObjectionTags";
import CallInsightsPanel from "./CallInsightsPanel";
import ScoreBreakdownPanel from "./ScoreBreakdownPanel";
import SentimentPanel from "./SentimentPanel";
import BuyingIntentPanel from "./BuyingIntentPanel";
import CoachingPanel from "./CoachingPanel";
import ComplianceChecklist from "./ComplianceChecklist";
import OutcomePanel from "./OutcomePanel";

export default function CallDetail({ call, onFeedbackChange, onOutcomeChange }) {
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

      <section className="panel">
        <h3>Score breakdown</h3>
        <ScoreBreakdownPanel
          scoreBreakdown={call.extraction.score_breakdown}
          compliance={call.compliance}
          overallScore={call.overall_score}
        />
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

      <div className="call-detail-columns">
        <section className="panel">
          <h3>Sentiment</h3>
          <SentimentPanel sentiment={call.extraction.sentiment} />
        </section>

        <section className="panel">
          <h3>Buying intent</h3>
          <BuyingIntentPanel buyingIntent={call.extraction.buying_intent} />
        </section>
      </div>

      <div className="call-detail-columns">
        <section className="panel">
          <h3>Coaching</h3>
          <CoachingPanel coaching={call.extraction.coaching} />
        </section>

        <section className="panel">
          <h3>Compliance</h3>
          <ComplianceChecklist compliance={call.compliance} />
        </section>
      </div>

      <section className="panel">
        <h3>Outcome</h3>
        <OutcomePanel callId={call.id} outcome={call.outcome} onOutcomeChange={onOutcomeChange} />
      </section>
    </div>
  );
}
