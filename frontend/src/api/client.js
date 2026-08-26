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

export function audioUrl(callId) {
  return `${API_BASE}/api/calls/${callId}/audio`;
}

export function uploadCall(file, meta = {}) {
  const formData = new FormData();
  formData.append("file", file);
  if (meta.agentName) formData.append("agent_name", meta.agentName);
  if (meta.leadPhone) formData.append("lead_phone", meta.leadPhone);
  if (meta.leadName) formData.append("lead_name", meta.leadName);
  if (meta.leadUnit) formData.append("lead_unit", meta.leadUnit);
  if (meta.leadBudget) formData.append("lead_budget", meta.leadBudget);
  if (meta.leadSource) formData.append("lead_source", meta.leadSource);
  return request("/api/calls", { method: "POST", body: formData });
}

export function submitFeedback(callId, itemType, itemIndex, confirmed) {
  return request(`/api/calls/${callId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_type: itemType, item_index: itemIndex, confirmed }),
  });
}

export function listAgents() {
  return request("/api/agents");
}

export function getAgent(agentId) {
  return request(`/api/agents/${agentId}`);
}

export function listLeads() {
  return request("/api/leads");
}

export function getLead(leadId) {
  return request(`/api/leads/${leadId}`);
}

export function updateLead(leadId, patch) {
  return request(`/api/leads/${leadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export function getOrg() {
  return request("/api/org");
}

export function getSettings() {
  return request("/api/settings");
}

export function updateSettings(rubric) {
  return request("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rubric),
  });
}
