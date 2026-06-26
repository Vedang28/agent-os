import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.graphics.art_director import ArtDirector
from agents.departments.graphics.asset_generator import AssetGenerator
from agents.departments.graphics.brand_keeper import BrandKeeper
from agents.departments.graphics.graphics_critic import GraphicsCritic
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("graphics.graph")

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
    logger.warning("graphics department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_graphics_graph(librarian=None, obsidian=None, tool_registry=None):
    art_director = ArtDirector(librarian=librarian, obsidian=obsidian)
    asset_generator = AssetGenerator(tool_registry=tool_registry)
    brand_keeper = BrandKeeper(tool_registry=tool_registry)
    graphics_critic = GraphicsCritic()

    graph = StateGraph(AgentState)

    graph.add_node("art_director", _make_node(art_director))
    graph.add_node("asset_generator", _make_node(asset_generator))
    graph.add_node("brand_keeper", _make_node(brand_keeper))
    graph.add_node("graphics_critic", _make_node(graphics_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "art_director")
    graph.add_edge("art_director", "asset_generator")
    graph.add_edge("asset_generator", "brand_keeper")
    graph.add_edge("brand_keeper", "graphics_critic")
    graph.add_conditional_edges(
        "graphics_critic",
        _route_decision,
        {"end": END, "revise": "asset_generator", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
