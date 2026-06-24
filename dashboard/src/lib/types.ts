export interface AgentInfo {
  name: string;
  role: string;
  department: string;
  status: "idle" | "active" | "error";
}

export interface NoteInfo {
  title: string;
  content: string;
  tags: string[];
  created_at: string;
}

export interface NotesListResponse {
  notes: NoteInfo[];
  total: number;
}

export interface SearchResultResponse {
  results: NoteInfo[];
  query: string;
}

export interface StatusInfo {
  daemon: string;
  tick_count: number;
  last_tick: string | null;
  agents_registered: number;
  tools_registered: number;
  checkpointer: string;
}

export interface HistoryItem {
  task_id: string;
  department: string;
  success: boolean;
  revisions: number;
  tokens_used: number;
  wall_clock_seconds: number;
  timestamp: string;
}

export interface HistoryResponse {
  tasks: HistoryItem[];
  total: number;
}

export interface RequestResponse {
  task_id: string;
  lane: string;
  status: string;
}

export interface AgentEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface IntegrationInfo {
  name: string;
  type: "composio" | "mcp";
  connected: boolean;
  tools_count: number;
}

export interface IntegrationListResponse {
  integrations: IntegrationInfo[];
  total: number;
}

export interface IntegrationToolInfo {
  name: string;
  permission: string;
  integration: string;
}

export interface CostSummary {
  total_cost_usd: number;
  total_tokens: number;
  total_records: number;
  by_department: Record<string, number>;
  by_model: Record<string, number>;
  burn_rate_per_hour: number;
}

export interface CostBurnRate {
  burn_rate_usd_per_hour: number;
  window_hours: number;
}
