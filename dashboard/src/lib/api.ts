import type {
  AgentInfo,
  CostBurnRate,
  CostSummary,
  HistoryResponse,
  IntegrationListResponse,
  IntegrationToolInfo,
  NotesListResponse,
  RequestResponse,
  SearchResultResponse,
  StatusInfo,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN || "";

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  if (API_TOKEN) {
    headers["Authorization"] = `Bearer ${API_TOKEN}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getAgents(): Promise<AgentInfo[]> {
  return fetchApi<AgentInfo[]>("/api/agents");
}

export async function getStatus(): Promise<StatusInfo> {
  return fetchApi<StatusInfo>("/api/status");
}

export async function getBrainNotes(
  tag?: string,
  limit = 20,
  offset = 0
): Promise<NotesListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (tag) params.set("tag", tag);
  return fetchApi<NotesListResponse>(`/api/brain/notes?${params}`);
}

export async function searchBrain(
  query: string,
  topK = 5
): Promise<SearchResultResponse> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  return fetchApi<SearchResultResponse>(`/api/brain/search?${params}`);
}

export async function getHistory(
  department?: string,
  limit = 20
): Promise<HistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (department) params.set("department", department);
  return fetchApi<HistoryResponse>(`/api/history?${params}`);
}

export async function submitRequest(
  request: string
): Promise<RequestResponse> {
  return fetchApi<RequestResponse>("/api/request", {
    method: "POST",
    body: JSON.stringify({ request }),
  });
}

export async function approveAction(
  taskId: string,
  approved: boolean
): Promise<void> {
  await fetchApi("/api/approve", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, approved }),
  });
}

export async function killSwitch(reason = "manual"): Promise<void> {
  await fetchApi("/api/kill", {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function getIntegrations(): Promise<IntegrationListResponse> {
  return fetchApi<IntegrationListResponse>("/api/integrations");
}

export async function connectIntegration(
  appName: string
): Promise<{ app_name: string; auth_url: string; scopes: string[] }> {
  return fetchApi("/api/integrations/connect", {
    method: "POST",
    body: JSON.stringify({ app_name: appName }),
  });
}

export async function disconnectIntegration(appName: string): Promise<void> {
  await fetchApi("/api/integrations/disconnect", {
    method: "POST",
    body: JSON.stringify({ app_name: appName }),
  });
}

export async function getIntegrationTools(): Promise<IntegrationToolInfo[]> {
  return fetchApi<IntegrationToolInfo[]>("/api/integrations/tools");
}

export async function getCosts(): Promise<CostSummary> {
  return fetchApi<CostSummary>("/api/costs");
}

export async function getCostsByDepartment(dept: string): Promise<CostSummary> {
  return fetchApi<CostSummary>(`/api/costs/department/${encodeURIComponent(dept)}`);
}

export async function getCostsBurnRate(windowHours = 24): Promise<CostBurnRate> {
  return fetchApi<CostBurnRate>(`/api/costs/burn-rate?window_hours=${windowHours}`);
}
