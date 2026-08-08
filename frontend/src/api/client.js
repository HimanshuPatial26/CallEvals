const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function listCalls() {
  return request("/api/calls");
}

export function getCall(callId) {
  return request(`/api/calls/${callId}`);
}

export function uploadCall(file, agentName) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("agent_name", agentName);
  return request("/api/calls", { method: "POST", body: formData });
}

export function submitFeedback(callId, itemType, itemIndex, confirmed) {
  return request(`/api/calls/${callId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_type: itemType, item_index: itemIndex, confirmed }),
  });
}

export function submitOutcome(callId, stage, dealSizeAed) {
  return request(`/api/calls/${callId}/outcome`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage, deal_size_aed: dealSizeAed }),
  });
}

export function listAgents() {
  return request("/api/agents");
}

export function getAgentPerformance(agentName, start, end) {
  const params = new URLSearchParams({ start, end });
  return request(`/api/agents/${encodeURIComponent(agentName)}/performance?${params}`);
}
