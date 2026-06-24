from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from infra.telemetry import get_logger
from io_layer.dashboard_api.auth import require_auth
from io_layer.dashboard_api.models import (
    AgentResponse,
    ApprovalBody,
    ConnectBody,
    ConnectResponse,
    CostBurnRateResponse,
    CostSummaryResponse,
    HistoryItem,
    HistoryResponse,
    IntegrationInfo,
    IntegrationListResponse,
    IntegrationToolInfo,
    KillBody,
    NoteResponse,
    NotesListResponse,
    RequestBody,
    RequestResponse,
    SearchResultResponse,
    StatusResponse,
)

logger = get_logger("io.dashboard_api.routes")

router = APIRouter(prefix="/api")

_services: dict[str, Any] = {}
_active_tasks: dict[str, asyncio.Task] = {}
_pending_approvals: dict[str, dict] = {}


def set_services(
    *,
    obsidian: Any = None,
    librarian: Any = None,
    outcome_store: Any = None,
    daemon: Any = None,
    guardian: Any = None,
    graph_factory: Any = None,
    composio_bridge: Any = None,
    mcp_bridge: Any = None,
    cost_tracker: Any = None,
) -> None:
    if obsidian is not None:
        _services["obsidian"] = obsidian
    if librarian is not None:
        _services["librarian"] = librarian
    if outcome_store is not None:
        _services["outcome_store"] = outcome_store
    if daemon is not None:
        _services["daemon"] = daemon
    if guardian is not None:
        _services["guardian"] = guardian
    if graph_factory is not None:
        _services["graph_factory"] = graph_factory
    if composio_bridge is not None:
        _services["composio_bridge"] = composio_bridge
    if mcp_bridge is not None:
        _services["mcp_bridge"] = mcp_bridge
    if cost_tracker is not None:
        _services["cost_tracker"] = cost_tracker


def _get(name: str) -> Any:
    svc = _services.get(name)
    if svc is None:
        raise HTTPException(status_code=503, detail=f"Service not available: {name}")
    return svc


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents() -> list[AgentResponse]:
    from agents import registry as agent_registry

    names = agent_registry.list_agents()
    results = []
    for name in names:
        parts = name.split(".")
        dept = parts[0] if len(parts) > 1 else ""
        results.append(AgentResponse(name=name, department=dept))
    return results


@router.get("/brain/notes", response_model=NotesListResponse)
async def list_brain_notes(
    tag: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NotesListResponse:
    obsidian = _get("obsidian")
    titles = obsidian.list_notes()

    notes: list[NoteResponse] = []
    for title in titles:
        try:
            note = obsidian.read_note(title)
        except FileNotFoundError:
            continue
        if tag and tag not in note.tags:
            continue
        notes.append(
            NoteResponse(
                title=note.title,
                content=note.content,
                tags=note.tags,
                created_at=note.created_at.isoformat() if note.created_at else "",
            )
        )

    total = len(notes)
    page = notes[offset : offset + limit]
    return NotesListResponse(notes=page, total=total)


@router.get("/brain/search", response_model=SearchResultResponse)
async def search_brain(
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(5, ge=1, le=50),
) -> SearchResultResponse:
    librarian = _get("librarian")
    results = librarian.query(q, top_k=top_k)
    return SearchResultResponse(
        results=[
            NoteResponse(
                title=n.title,
                content=n.content,
                tags=n.tags,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in results
        ],
        query=q,
    )


@router.get("/status", response_model=StatusResponse)
async def system_status() -> StatusResponse:
    from agents import registry as agent_registry
    from tools import registry as tool_registry

    daemon = _services.get("daemon")
    return StatusResponse(
        daemon="running" if daemon and daemon.is_running else "stopped",
        tick_count=daemon.tick_count if daemon else 0,
        agents_registered=len(agent_registry.list_agents()),
        tools_registered=len(tool_registry.list_tools()),
    )


@router.get("/history", response_model=HistoryResponse)
async def task_history(
    department: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> HistoryResponse:
    outcome_store = _get("outcome_store")
    if department:
        outcomes = outcome_store.query_by_department(department)
    else:
        outcomes = outcome_store.query_recent(n=limit)

    tasks = [
        HistoryItem(
            task_id=o.task_id,
            department=o.department,
            success=o.success,
            revisions=o.revisions,
            tokens_used=o.tokens_used,
            wall_clock_seconds=o.wall_clock_seconds,
            timestamp=o.timestamp,
        )
        for o in outcomes[:limit]
    ]
    return HistoryResponse(tasks=tasks, total=len(tasks))


@router.post("/request", response_model=RequestResponse, status_code=202)
async def submit_request(
    body: RequestBody,
    _token: str = Depends(require_auth),
) -> RequestResponse:
    graph_factory = _get("graph_factory")
    task_id = str(uuid.uuid4())

    from core.dispatcher import assign_lane

    lane_result = assign_lane({"request": body.request})
    lane = lane_result.get("lane", "fast")

    async def _run() -> None:
        try:
            graph = graph_factory()
            await asyncio.to_thread(
                graph.invoke,
                {"request": body.request},
                {"configurable": {"thread_id": task_id}},
            )
        except Exception:
            logger.exception("background task %s failed", task_id)
        finally:
            _active_tasks.pop(task_id, None)

    task = asyncio.create_task(_run())
    _active_tasks[task_id] = task

    try:
        from io_layer.event_bus import REQUEST_SUBMITTED, publish_event

        await publish_event(
            REQUEST_SUBMITTED, task_id=task_id, request=body.request, lane=lane
        )
    except Exception:
        pass

    return RequestResponse(task_id=task_id, lane=lane)


@router.post("/approve")
async def approve_action(
    body: ApprovalBody,
    _token: str = Depends(require_auth),
) -> dict:
    guardian = _get("guardian")

    pending = _pending_approvals.pop(body.task_id, None)
    if pending is None:
        raise HTTPException(status_code=404, detail="No pending approval for this task")

    callback = pending.get("resolve")
    if callback:
        callback(body.approved)

    return {"task_id": body.task_id, "approved": body.approved, "status": "resolved"}


@router.post("/kill")
async def kill_switch(
    body: KillBody,
    _token: str = Depends(require_auth),
) -> dict:
    guardian = _get("guardian")
    guardian.kill()
    logger.warning("kill switch activated via API: %s", body.reason)
    return {"status": "killed", "reason": body.reason}


@router.get("/integrations", response_model=IntegrationListResponse)
async def list_integrations() -> IntegrationListResponse:
    from tools import registry as tool_registry

    items: list[IntegrationInfo] = []

    bridge = _services.get("composio_bridge")
    if bridge:
        connected = await bridge.list_connected_apps()
        from integrations.composio import APP_SCOPES

        for app in APP_SCOPES:
            tools_count = len(tool_registry.list_tools(namespace=f"composio.{app}"))
            items.append(
                IntegrationInfo(
                    name=app,
                    type="composio",
                    connected=app in connected,
                    tools_count=tools_count,
                )
            )

    mcp = _services.get("mcp_bridge")
    if mcp:
        servers = await mcp.list_servers()
        for server in servers:
            tools_count = len(tool_registry.list_tools(namespace=f"mcp.{server}"))
            items.append(
                IntegrationInfo(
                    name=server,
                    type="mcp",
                    connected=True,
                    tools_count=tools_count,
                )
            )

    return IntegrationListResponse(integrations=items, total=len(items))


@router.post("/integrations/connect", response_model=ConnectResponse)
async def connect_integration(
    body: ConnectBody,
    _token: str = Depends(require_auth),
) -> ConnectResponse:
    bridge = _services.get("composio_bridge")
    if not bridge:
        raise HTTPException(status_code=503, detail="Composio bridge not configured")
    result = await bridge.connect_app(body.app_name)
    return ConnectResponse(
        app_name=result.app_name,
        auth_url=result.auth_url,
        scopes=result.scopes,
    )


@router.post("/integrations/disconnect")
async def disconnect_integration(
    body: ConnectBody,
    _token: str = Depends(require_auth),
) -> dict:
    bridge = _services.get("composio_bridge")
    if not bridge:
        raise HTTPException(status_code=503, detail="Composio bridge not configured")
    await bridge.disconnect_app(body.app_name)
    return {"app_name": body.app_name, "status": "disconnected"}


@router.get("/integrations/tools", response_model=list[IntegrationToolInfo])
async def list_integration_tools() -> list[IntegrationToolInfo]:
    from tools import registry as tool_registry

    result: list[IntegrationToolInfo] = []
    for name in tool_registry.list_tools(namespace="composio"):
        tool = tool_registry.get(name)
        parts = name.split(".")
        integration = parts[1] if len(parts) > 1 else "unknown"
        result.append(
            IntegrationToolInfo(
                name=name,
                permission=tool.permission.value,
                integration=integration,
            )
        )
    for name in tool_registry.list_tools(namespace="mcp"):
        tool = tool_registry.get(name)
        parts = name.split(".")
        integration = parts[1] if len(parts) > 1 else "unknown"
        result.append(
            IntegrationToolInfo(
                name=name,
                permission=tool.permission.value,
                integration=integration,
            )
        )
    return result


@router.get("/costs", response_model=CostSummaryResponse)
async def get_costs(_token: str = Depends(require_auth)) -> CostSummaryResponse:
    tracker = _get("cost_tracker")
    summary = tracker.get_total()
    return CostSummaryResponse(
        total_cost_usd=summary.total_cost_usd,
        total_tokens=summary.total_tokens,
        total_records=summary.total_records,
        by_department=summary.by_department,
        by_model=summary.by_model,
        burn_rate_per_hour=summary.burn_rate_per_hour,
    )


@router.get("/costs/department/{dept}", response_model=CostSummaryResponse)
async def get_costs_by_department(
    dept: str, _token: str = Depends(require_auth)
) -> CostSummaryResponse:
    tracker = _get("cost_tracker")
    summary = tracker.get_by_department(dept)
    return CostSummaryResponse(
        total_cost_usd=summary.total_cost_usd,
        total_tokens=summary.total_tokens,
        total_records=summary.total_records,
        by_department=summary.by_department,
        by_model=summary.by_model,
        burn_rate_per_hour=summary.burn_rate_per_hour,
    )


@router.get("/costs/burn-rate", response_model=CostBurnRateResponse)
async def get_burn_rate(
    window_hours: float = Query(24.0, ge=1, le=720),
    _token: str = Depends(require_auth),
) -> CostBurnRateResponse:
    tracker = _get("cost_tracker")
    rate = tracker.get_burn_rate(window_hours=window_hours)
    return CostBurnRateResponse(
        burn_rate_usd_per_hour=rate, window_hours=window_hours,
    )
