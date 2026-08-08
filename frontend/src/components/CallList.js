import { useEffect, useState } from "react";
import { listAgents } from "../api/client";

const STATUS_LABEL = {
  processing: "Processing…",
  done: "Ready",
  failed: "Failed",
};

export default function CallList({ calls, selectedId, onSelect }) {
  const [agentNames, setAgentNames] = useState({});

  useEffect(() => {
    listAgents()
      .then((data) => setAgentNames(Object.fromEntries(data.map((a) => [a.id, a.name]))))
      .catch(() => {});
  }, []);

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
          <span className="call-list-text">
            <span className="call-filename">{call.filename}</span>
            <span className="call-agent-name">{agentNames[call.agent_id] || call.agent_id}</span>
          </span>
          <span className={`status-badge status-${call.status}`}>{STATUS_LABEL[call.status] || call.status}</span>
        </li>
      ))}
    </ul>
  );
}
