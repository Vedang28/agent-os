from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    name: str
    role: str = ""
    department: str = ""
    status: str = "idle"


class NoteResponse(BaseModel):
    title: str
    content: str
    tags: list[str] = []
    created_at: str = ""


class NotesListResponse(BaseModel):
    notes: list[NoteResponse]
    total: int


class SearchResultResponse(BaseModel):
    results: list[NoteResponse]
    query: str


class StatusResponse(BaseModel):
    daemon: str
    tick_count: int = 0
    last_tick: str | None = None
    agents_registered: int = 0
    tools_registered: int = 0
    checkpointer: str = "active"


class HistoryItem(BaseModel):
    task_id: str
    department: str
    success: bool
    revisions: int = 0
    tokens_used: int = 0
    wall_clock_seconds: float = 0.0
    timestamp: str = ""


class HistoryResponse(BaseModel):
    tasks: list[HistoryItem]
    total: int


class RequestBody(BaseModel):
    request: str = Field(..., min_length=1, max_length=5000)


class RequestResponse(BaseModel):
    task_id: str
    lane: str
    status: str = "accepted"


class ApprovalBody(BaseModel):
    task_id: str
    approved: bool


class KillBody(BaseModel):
    reason: str = "manual"


class IntegrationInfo(BaseModel):
    name: str
    type: str  # "composio" | "mcp"
    connected: bool
    tools_count: int = 0


class IntegrationListResponse(BaseModel):
    integrations: list[IntegrationInfo]
    total: int


class ConnectBody(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=100)


class ConnectResponse(BaseModel):
    app_name: str
    auth_url: str
    scopes: list[str]


class IntegrationToolInfo(BaseModel):
    name: str
    permission: str
    integration: str


class CostSummaryResponse(BaseModel):
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_records: int = 0
    by_department: dict[str, float] = {}
    by_model: dict[str, float] = {}
    burn_rate_per_hour: float = 0.0


class CostBurnRateResponse(BaseModel):
    burn_rate_usd_per_hour: float = 0.0
    window_hours: float = 24.0
