import { IconCoaching } from "../icons";
import { fmtTime } from "../utils/format";

// Coaching moments are a presentation of the same rule-based behavior flags shown
// on the Rubric screen — not a separate LLM-generated narrative, which the backend
// doesn't produce. Each entry's note is the flag's own rule description; the jump
// timestamp points at the transcript moment that actually triggered it, found
// locally from the same transcript the flag was computed against.
const DISCOUNT_WORDS = ["discount", "lower the price", "lower price", "reduce the price", "knock off"];

function findLongestRepTurn(segments) {
  const rep = segments.filter((s) => s.speaker === "rep");
  if (rep.length === 0) return 0;
  return rep.reduce((longest, s) => ((s.end - s.start) > (longest.end - longest.start) ? s : longest)).start;
}

function findFirstDiscountMention(segments) {
  const rep = segments.filter((s) => s.speaker === "rep");
  const hit = rep.find((s) => DISCOUNT_WORDS.some((w) => s.text.toLowerCase().includes(w)));
  return hit ? hit.start : 0;
}

function buildMoments(flags, segments, nextSteps) {
  if (!flags) return [];
  const defs = [
    {
      key: "monologue",
      title: "Rep monologue over 45 seconds",
      crit: "Listening",
      note: "A single uninterrupted rep turn ran past 45 seconds. Try one point, then a question, rather than the full pitch up front.",
      ts: () => findLongestRepTurn(segments),
    },
    {
      key: "no_discovery_question",
      title: "Fewer than two discovery questions",
      crit: "Discovery",
      note: "The rep asked fewer than two questions across the call — worth checking whether enough was learned to shape what gets sent next.",
      ts: () => 0,
    },
    {
      key: "no_dated_next_step",
      title: "No dated next step committed",
      crit: "Next step",
      note: "Nothing was extracted as a commitment with a date attached. An open-ended next step is a common churn signal.",
      ts: () => nextSteps?.[0]?.source_timestamp ?? 0,
    },
    {
      key: "missing_disclosure",
      title: "No recording disclosure in the opening",
      crit: "Compliance",
      note: "No disclosure language was found in the first 30 seconds. PDPL disclosure is a one-line script worth adding before anything else.",
      ts: () => 0,
    },
    {
      key: "discount_offered_first",
      title: "Discount offered before a question was asked",
      crit: "Objection handling",
      note: "A price reduction was mentioned before the rep asked a single question.",
      ts: () => findFirstDiscountMention(segments),
    },
  ];
  return defs.filter((d) => flags[d.key]);
}

export default function CoachingPanel({ flags, segments, nextSteps, onJump }) {
  const moments = buildMoments(flags, segments, nextSteps);

  if (moments.length === 0) {
    return (
      <div className="ce-dashed-empty">
        <span className="ce-state-title">No coaching moments flagged.</span>
        <span className="ce-state-body">Nothing on this call tripped a configured rubric rule.</span>
      </div>
    );
  }

  return (
    <div className="ce-card">
      <div className="ce-card-header">
        <span className="ce-card-title">Coaching moments</span>
        <span className="ce-card-tag">SUGGESTIONS, NOT VERDICTS</span>
      </div>
      <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        {moments.map((m) => (
          <div key={m.key} className="ce-coaching-item">
            <div className="ce-coaching-head">
              <IconCoaching size={16} />
              <span className="ce-flag-name">{m.title}</span>
              <span className="ce-chip" style={{ marginLeft: "auto" }}>{m.crit}</span>
            </div>
            <span className="ce-coaching-note">{m.note}</span>
            <button type="button" className="ce-jump-chip" style={{ alignSelf: "flex-start" }} onClick={() => onJump(m.ts())}>
              ↳ {fmtTime(m.ts())}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
