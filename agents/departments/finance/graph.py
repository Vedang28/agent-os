import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.finance.bookkeeper import Bookkeeper
from agents.departments.finance.compliance_critic import ComplianceCritic
from agents.departments.finance.reporter import Reporter
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("finance.graph")

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
    logger.warning("finance department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_finance_graph(librarian=None, obsidian=None, tool_registry=None):
    bookkeeper = Bookkeeper(librarian=librarian, obsidian=obsidian)
    reporter = Reporter(tool_registry=tool_registry)
    critic = ComplianceCritic()

    graph = StateGraph(AgentState)

    graph.add_node("bookkeeper", _make_node(bookkeeper))
    graph.add_node("reporter", _make_node(reporter))
    graph.add_node("compliance_critic", _make_node(critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "bookkeeper")
    graph.add_edge("bookkeeper", "reporter")
    graph.add_edge("reporter", "compliance_critic")
    graph.add_conditional_edges(
        "compliance_critic",
        _route_decision,
        {"end": END, "revise": "reporter", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
