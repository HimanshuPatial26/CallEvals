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

export function uploadCall(file, agentId, leadId) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("agent_id", agentId);
  formData.append("lead_id", leadId);
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

export function getAgentPerformance(agentId, start, end) {
  const params = new URLSearchParams({ start, end });
  return request(`/api/agents/${encodeURIComponent(agentId)}/performance?${params}`);
}

export function getTeamPerformance(teamId, start, end) {
  const params = new URLSearchParams({ start, end });
  return request(`/api/teams/${encodeURIComponent(teamId)}/performance?${params}`);
}

export function getOrgPerformance(start, end) {
  const params = new URLSearchParams({ start, end });
  return request(`/api/organization/performance?${params}`);
}

export function getLead(leadId) {
  return request(`/api/leads/${leadId}`);
}

export function listLeads({ assignedAgentId, stage, q } = {}) {
  const params = new URLSearchParams();
  if (assignedAgentId) params.set("assigned_agent_id", assignedAgentId);
  if (stage) params.set("stage", stage);
  if (q) params.set("q", q);
  const qs = params.toString();
  return request(`/api/leads${qs ? `?${qs}` : ""}`);
}

export function setLeadStage(leadId, stage, dealSizeAed, lostReason) {
  return request(`/api/leads/${leadId}/stage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage, deal_size_aed: dealSizeAed, lost_reason: lostReason || null }),
  });
}

export function updateLead(leadId, updates) {
  return request(`/api/leads/${leadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}

export function reassignLead(leadId, assignedAgentId, changedBy) {
  return request(`/api/leads/${leadId}/reassign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assigned_agent_id: assignedAgentId, changed_by: changedBy }),
  });
}
