import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.frontend_design.design_critic import DesignCritic
from agents.departments.frontend_design.interaction_designer import (
    InteractionDesigner,
)
from agents.departments.frontend_design.ui_stylist import UiStylist
from agents.departments.frontend_design.ux_designer import UxDesigner
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend_design.graph")

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
    logger.warning(
        "frontend_design department escalating after %d revisions", revisions
    )
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_frontend_design_graph(librarian=None, obsidian=None, tool_registry=None):
    ux_designer = UxDesigner(librarian=librarian, obsidian=obsidian)
    ui_stylist = UiStylist(tool_registry=tool_registry)
    interaction_designer = InteractionDesigner(tool_registry=tool_registry)
    design_critic = DesignCritic()

    graph = StateGraph(AgentState)

    graph.add_node("ux_designer", _make_node(ux_designer))
    graph.add_node("ui_stylist", _make_node(ui_stylist))
    graph.add_node("interaction_designer", _make_node(interaction_designer))
    graph.add_node("design_critic", _make_node(design_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "ux_designer")
    graph.add_edge("ux_designer", "ui_stylist")
    graph.add_edge("ui_stylist", "interaction_designer")
    graph.add_edge("interaction_designer", "design_critic")
    graph.add_conditional_edges(
        "design_critic",
        _route_decision,
        {"end": END, "revise": "ui_stylist", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
