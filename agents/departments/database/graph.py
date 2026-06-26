import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.database.architect import DatabaseArchitect
from agents.departments.database.integrity_critic import DataIntegrityCritic
from agents.departments.database.migration_runner import MigrationRunner
from agents.departments.database.query_writer import QueryWriter
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("database.graph")

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
    logger.warning("database department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_database_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = DatabaseArchitect(librarian=librarian, obsidian=obsidian)
    query_writer = QueryWriter(tool_registry=tool_registry)
    migration_runner = MigrationRunner(tool_registry=tool_registry)
    integrity_critic = DataIntegrityCritic()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("query_writer", _make_node(query_writer))
    graph.add_node("migration_runner", _make_node(migration_runner))
    graph.add_node("integrity_critic", _make_node(integrity_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "query_writer")
    graph.add_edge("query_writer", "migration_runner")
    graph.add_edge("migration_runner", "integrity_critic")
    graph.add_conditional_edges(
        "integrity_critic",
        _route_decision,
        {"end": END, "revise": "query_writer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
