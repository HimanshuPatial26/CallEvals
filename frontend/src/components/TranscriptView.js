import { fmtTime } from "../utils/format";

export default function TranscriptView({ segments, agentName, leadName, activeTime, onJump }) {
  if (segments.length === 0) {
    return <div className="ce-unavailable">No transcript available for this call.</div>;
  }

  const activeIndex = segments.reduce((acc, seg, i) => (activeTime >= seg.start ? i : acc), -1);

  return (
    <div className="ce-transcript-list">
      {segments.map((seg, i) => {
        const isRep = seg.speaker === "rep";
        const isActive = i === activeIndex;
        const speakerLabel = isRep
          ? `${firstName(agentName) || "Rep"} (rep)`
          : seg.speaker === "customer"
            ? `${firstName(leadName) || "Customer"} (customer)`
            : "Unknown speaker";
        return (
          <button
            key={i}
            type="button"
            className={`ce-transcript-row${isRep ? " rep" : ""}${isActive ? " active" : ""}`}
            onClick={() => onJump(seg.start)}
          >
            <span className="ce-transcript-who">
              <span className="ce-transcript-name">{speakerLabel}</span>
              <span className="ce-transcript-ts">{fmtTime(seg.start)}</span>
            </span>
            <span className="ce-transcript-text">{seg.text}</span>
          </button>
        );
      })}
    </div>
  );
}

function firstName(name) {
  if (!name) return "";
  return name.split(" ")[0];
}
