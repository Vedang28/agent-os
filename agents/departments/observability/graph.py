import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.observability.alert_designer import AlertDesigner
from agents.departments.observability.incident_responder import IncidentResponder
from agents.departments.observability.telemetry_engineer import TelemetryEngineer
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("observability.graph")

MAX_REVISIONS = 3


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _make_node(agent_instance):
    def node(state: AgentState) -> dict:
        return _run_async(agent_instance.run(state))

    node.__name__ = agent_instance.name.replace(".", "_")
    return node


def _route_decision(state: AgentState) -> str:
    if state.get("approved"):
        return "end"
    if state.get("revisions", 0) >= MAX_REVISIONS:
        return "escalate"
    return "revise"


def _escalate(state: AgentState) -> dict:
    revisions = state.get("revisions", 0)
    logger.warning("observability department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_observability_graph(librarian=None, obsidian=None, tool_registry=None):
    telemetry_engineer = TelemetryEngineer(
        librarian=librarian, obsidian=obsidian, tool_registry=tool_registry
    )
    alert_designer = AlertDesigner(tool_registry=tool_registry)
    incident_responder = IncidentResponder()

    graph = StateGraph(AgentState)
    graph.add_node("telemetry_engineer", _make_node(telemetry_engineer))
    graph.add_node("alert_designer", _make_node(alert_designer))
    graph.add_node("incident_responder", _make_node(incident_responder))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "telemetry_engineer")
    graph.add_edge("telemetry_engineer", "alert_designer")
    graph.add_edge("alert_designer", "incident_responder")
    graph.add_conditional_edges(
        "incident_responder",
        _route_decision,
        {"end": END, "revise": "alert_designer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
