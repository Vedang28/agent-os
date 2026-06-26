import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.memory.decision_recorder import DecisionRecorder
from agents.departments.memory.log_auditor import LogAuditor
from agents.departments.memory.session_scribe import SessionScribe
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("memory.graph")

MAX_REVISIONS = 3


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
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
    logger.warning("memory department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_memory_graph(librarian=None, obsidian=None, tool_registry=None):
    session_scribe = SessionScribe(librarian=librarian, obsidian=obsidian)
    decision_recorder = DecisionRecorder(tool_registry=tool_registry)
    log_auditor = LogAuditor()

    graph = StateGraph(AgentState)

    graph.add_node("session_scribe", _make_node(session_scribe))
    graph.add_node("decision_recorder", _make_node(decision_recorder))
    graph.add_node("log_auditor", _make_node(log_auditor))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "session_scribe")
    graph.add_edge("session_scribe", "decision_recorder")
    graph.add_edge("decision_recorder", "log_auditor")
    graph.add_conditional_edges(
        "log_auditor",
        _route_decision,
        {"end": END, "revise": "decision_recorder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
