const STATUS_LABEL = {
  processing: "Processing…",
  done: "Ready",
  failed: "Failed",
};

export default function CallList({ calls, selectedId, onSelect }) {
  if (calls.length === 0) {
    return <p className="hint">No calls yet — upload one to get started.</p>;
  }

  return (
    <ul className="call-list">
      {calls.map((call) => (
        <li
          key={call.id}
          className={`call-list-item ${call.id === selectedId ? "selected" : ""}`}
          onClick={() => onSelect(call.id)}
        >
          <span className="call-filename">{call.filename}</span>
          <span className={`status-badge status-${call.status}`}>{STATUS_LABEL[call.status] || call.status}</span>
        </li>
      ))}
    </ul>
  );
}
