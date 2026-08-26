import { useEffect, useState } from "react";
import { listAgents } from "../api/client";
import { FailedCrossIcon, PlayIcon, ProcessingIcon, ReadyCheckIcon, RetryIcon } from "./icons";

const STATUS_LABEL = {
  processing: "Processing…",
  done: "Ready",
  failed: "Failed",
};

// Design system 06 · Components > "CALL ROW": a leading icon (what the
// call needs next -- play a ready call, retry a failed one, watch a
// processing one) and a status chip with a matching check/cross glyph.
const ROW_ICON = {
  done: PlayIcon,
  failed: RetryIcon,
  processing: ProcessingIcon,
};

const STATUS_ICON = {
  done: ReadyCheckIcon,
  failed: FailedCrossIcon,
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
      {calls.map((call) => {
        const RowIcon = ROW_ICON[call.status] || PlayIcon;
        const StatusIcon = STATUS_ICON[call.status];
        return (
          <li
            key={call.id}
            className={`call-list-item ${call.id === selectedId ? "selected" : ""}`}
            onClick={() => onSelect(call.id)}
          >
            <RowIcon className="call-list-icon" aria-hidden="true" />
            <span className="call-list-text">
              <span className="call-filename">{call.filename}</span>
              <span className="call-agent-name">{agentNames[call.agent_id] || call.agent_id}</span>
            </span>
            <span className={`status-badge status-${call.status}`}>
              {StatusIcon && <StatusIcon aria-hidden="true" />}
              {STATUS_LABEL[call.status] || call.status}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
