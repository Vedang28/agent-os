import time

from langgraph.graph import END, START, StateGraph

from core.checkpointer import get_checkpointer
from core.dispatcher import assign_lane
from core.orchestrator import orchestrate
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("core.graph")

_department_graphs: dict[str, object] = {}
_department_keywords: dict[str, list[str]] = {}


def register_department_graph(name: str, compiled_graph, keywords: list[str] | None = None) -> None:
    _department_graphs[name] = compiled_graph
    if keywords:
        _department_keywords[name] = keywords


def get_department_keywords() -> dict[str, list[str]]:
    return _department_keywords


def _route_by_lane(state: AgentState) -> str:
    lane = state.get("lane", "fast")
    if lane == "instant":
        return "instant"
    return "orchestrate"


def _instant_response(state: AgentState) -> dict:
    request = state.get("request", "")
    return {"result": f"ACK: {request}", "approved": True}


def _department_node(state: AgentState) -> dict:
    department = state.get("department", "")

    try:
        from io_layer.event_bus import DEPARTMENT_ACTIVE, TASK_COMPLETE, sync_publish

        sync_publish(DEPARTMENT_ACTIVE, department=department)
    except Exception:
        pass

    graph = _department_graphs.get(department)
    if graph is None:
        logger.error("no graph registered for department=%s", department)
        return {"result": f"No department graph for: {department}", "approved": False}
    _start = time.monotonic()
    try:
        result = graph.invoke(dict(state))
    except Exception as e:
        logger.error("department=%s failed: %s", department, e)
        return {"result": f"Department error: {e}", "approved": False}

    output = {
        "draft": result.get("draft"),
        "result": result.get("result"),
        "critique": result.get("critique"),
        "approved": result.get("approved", False),
        "revisions": result.get("revisions", 0),
        "brain_context": result.get("brain_context", []),
    }

    try:
        from infra.cost_tracker import CostRecord, get_cost_tracker

        _elapsed = time.monotonic() - _start
        tracker = get_cost_tracker()
        tracker.record(CostRecord(
            task_id=state.get("request", "")[:50],
            department=department,
            model="unknown",
            tokens_input=0,
            tokens_output=0,
            cost_usd=0.0,
            wall_clock_seconds=_elapsed,
        ))
    except Exception:
        pass

    try:
        from io_layer.event_bus import TASK_COMPLETE, sync_publish

        sync_publish(
            TASK_COMPLETE,
            department=department,
            success=output["approved"],
            revisions=output["revisions"],
        )
    except Exception:
        pass

    return output


def build_company_graph():
    graph = StateGraph(AgentState)

    graph.add_node("dispatcher", assign_lane)
    graph.add_node("instant_response", _instant_response)
    graph.add_node("orchestrator", orchestrate)
    graph.add_node("department", _department_node)

    graph.add_edge(START, "dispatcher")
    graph.add_conditional_edges(
        "dispatcher",
        _route_by_lane,
        {"instant": "instant_response", "orchestrate": "orchestrator"},
    )
    graph.add_edge("instant_response", END)
    graph.add_edge("orchestrator", "department")
    graph.add_edge("department", END)

    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)


def build_graph():
    return build_company_graph()
