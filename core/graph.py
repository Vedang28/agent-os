"""Company graph — the main LangGraph that routes requests through AgentOS.

Flow:
  START → dispatcher → (instant | orchestrator → department(s)) → END

When the orchestrator selects multiple departments, they run in parallel
and results are merged.
"""

import concurrent.futures
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


def _run_single_department(department: str, state: dict) -> dict:
    """Run one department graph and return its output."""
    graph = _department_graphs.get(department)
    if graph is None:
        logger.error("no graph registered for department=%s", department)
        return {"department": department, "result": f"No department graph for: {department}", "approved": False}

    _start = time.monotonic()
    try:
        result = graph.invoke(dict(state))
    except Exception as e:
        logger.error("department=%s failed: %s", department, e)
        return {"department": department, "result": f"Department error: {e}", "approved": False}

    _elapsed = time.monotonic() - _start

    output = {
        "department": department,
        "draft": result.get("draft"),
        "result": result.get("result"),
        "critique": result.get("critique"),
        "approved": result.get("approved", False),
        "revisions": result.get("revisions", 0),
        "brain_context": result.get("brain_context", []),
    }

    try:
        from infra.cost_tracker import CostRecord, get_cost_tracker
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
        from io_layer.event_bus import DEPARTMENT_ACTIVE, TASK_COMPLETE, sync_publish
        sync_publish(TASK_COMPLETE, department=department, success=output["approved"], revisions=output["revisions"])
    except Exception:
        pass

    return output


def _department_node(state: AgentState) -> dict:
    """Execute department(s). Runs multiple departments in parallel when needed."""
    departments = state.get("departments") or [state.get("department", "engineering")]

    try:
        from io_layer.event_bus import DEPARTMENT_ACTIVE, sync_publish
        for dept in departments:
            sync_publish(DEPARTMENT_ACTIVE, department=dept)
    except Exception:
        pass

    if len(departments) == 1:
        result = _run_single_department(departments[0], state)
        result.pop("department", None)
        return result

    # Multiple departments — run in parallel
    logger.info("launching %d departments in parallel: %s", len(departments), departments)
    results: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(departments)) as pool:
        futures = {
            pool.submit(_run_single_department, dept, state): dept
            for dept in departments
        }
        for future in concurrent.futures.as_completed(futures):
            dept = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                logger.error("department=%s parallel execution failed: %s", dept, e)
                results.append({"department": dept, "result": f"Error: {e}", "approved": False})

    return _merge_results(results)


def _merge_results(results: list[dict]) -> dict:
    """Merge outputs from multiple departments into a single response."""
    all_approved = all(r.get("approved", False) for r in results)
    merged_result_parts: list[str] = []
    merged_draft_parts: list[str] = []
    all_context: list[dict] = []
    total_revisions = 0

    for r in results:
        dept = r.get("department", "unknown")
        if r.get("result"):
            merged_result_parts.append(f"=== [{dept}] ===\n{r['result']}")
        if r.get("draft"):
            merged_draft_parts.append(f"=== [{dept}] ===\n{r['draft']}")
        all_context.extend(r.get("brain_context") or [])
        total_revisions = max(total_revisions, r.get("revisions", 0))

    departments_run = [r.get("department", "unknown") for r in results]
    logger.info(
        "merged %d department results: departments=%s, all_approved=%s",
        len(results), departments_run, all_approved,
    )

    return {
        "result": "\n\n".join(merged_result_parts),
        "draft": "\n\n".join(merged_draft_parts),
        "approved": all_approved,
        "revisions": total_revisions,
        "brain_context": all_context,
        "departments": departments_run,
    }


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
