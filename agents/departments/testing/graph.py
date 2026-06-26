import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.testing.bug_triager import BugTriager
from agents.departments.testing.strategist import TestStrategist
from agents.departments.testing.test_executor import TestExecutor
from agents.departments.testing.test_writer import TestWriter
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("testing.graph")

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
    logger.warning("testing department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_testing_graph(librarian=None, obsidian=None, tool_registry=None):
    strategist = TestStrategist(librarian=librarian, obsidian=obsidian)
    test_writer = TestWriter(tool_registry=tool_registry)
    test_executor = TestExecutor(tool_registry=tool_registry)
    bug_triager = BugTriager()

    graph = StateGraph(AgentState)
    graph.add_node("strategist", _make_node(strategist))
    graph.add_node("test_writer", _make_node(test_writer))
    graph.add_node("test_executor", _make_node(test_executor))
    graph.add_node("bug_triager", _make_node(bug_triager))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "strategist")
    graph.add_edge("strategist", "test_writer")
    graph.add_edge("test_writer", "test_executor")
    graph.add_edge("test_executor", "bug_triager")
    graph.add_conditional_edges(
        "bug_triager",
        _route_decision,
        {"end": END, "revise": "test_writer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
