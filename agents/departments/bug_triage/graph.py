import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.bug_triage.bug_classifier import BugClassifier
from agents.departments.bug_triage.bug_reproducer import BugReproducer
from agents.departments.bug_triage.bug_validator import BugValidator
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("bug_triage.graph")

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
    logger.warning("bug_triage department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_bug_triage_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    classifier = BugClassifier(librarian=librarian, obsidian=obsidian)
    reproducer = BugReproducer(tool_registry=tool_registry)
    validator = BugValidator()

    graph = StateGraph(AgentState)
    graph.add_node("bug_classifier", _make_node(classifier))
    graph.add_node("bug_reproducer", _make_node(reproducer))
    graph.add_node("bug_validator", _make_node(validator))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "bug_classifier")
    graph.add_edge("bug_classifier", "bug_reproducer")
    graph.add_edge("bug_reproducer", "bug_validator")
    graph.add_conditional_edges(
        "bug_validator",
        _route_decision,
        {"end": END, "revise": "bug_reproducer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
