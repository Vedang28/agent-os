import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.ml.data_curator import DataCurator
from agents.departments.ml.embedding_engineer import EmbeddingEngineer
from agents.departments.ml.ml_critic import MLCritic
from agents.departments.ml.trainer import Trainer
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ml.graph")

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
    logger.warning("ml department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_ml_graph(librarian=None, obsidian=None, tool_registry=None):
    data_curator = DataCurator(librarian=librarian, obsidian=obsidian)
    embedding_engineer = EmbeddingEngineer(tool_registry=tool_registry)
    trainer = Trainer(tool_registry=tool_registry)
    ml_critic = MLCritic()

    graph = StateGraph(AgentState)
    graph.add_node("data_curator", _make_node(data_curator))
    graph.add_node("embedding_engineer", _make_node(embedding_engineer))
    graph.add_node("trainer", _make_node(trainer))
    graph.add_node("ml_critic", _make_node(ml_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "data_curator")
    graph.add_edge("data_curator", "embedding_engineer")
    graph.add_edge("embedding_engineer", "trainer")
    graph.add_edge("trainer", "ml_critic")
    graph.add_conditional_edges(
        "ml_critic",
        _route_decision,
        {"end": END, "revise": "embedding_engineer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
