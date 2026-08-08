function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function TranscriptView({ segments, highlightTimestamp }) {
  return (
    <div className="transcript">
      {segments.map((segment, i) => {
        const isHighlighted = highlightTimestamp != null && Math.abs(segment.start - highlightTimestamp) < 0.01;
        return (
          <div key={i} className={`transcript-segment speaker-${segment.speaker} ${isHighlighted ? "highlighted" : ""}`}>
            <span className="transcript-time">{formatTime(segment.start)}</span>
            <span className="transcript-speaker">{segment.speaker}</span>
            <span className="transcript-text">{segment.text}</span>
          </div>
        );
      })}
    </div>
  );
}
