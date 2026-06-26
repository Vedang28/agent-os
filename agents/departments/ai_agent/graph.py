import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.ai_agent.eval_critic import EvalCritic
from agents.departments.ai_agent.model_router_agent import ModelRouterAgent
from agents.departments.ai_agent.prompt_engineer import PromptEngineer
from agents.departments.ai_agent.tool_builder import ToolFunctionBuilder
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ai_agent.graph")

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
    logger.warning("ai_agent department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_ai_agent_graph(librarian=None, obsidian=None, tool_registry=None):
    prompt_engineer = PromptEngineer(librarian=librarian, obsidian=obsidian)
    tool_builder = ToolFunctionBuilder(tool_registry=tool_registry)
    model_router = ModelRouterAgent(tool_registry=tool_registry)
    eval_critic = EvalCritic()

    graph = StateGraph(AgentState)
    graph.add_node("prompt_engineer", _make_node(prompt_engineer))
    graph.add_node("tool_builder", _make_node(tool_builder))
    graph.add_node("model_router_agent", _make_node(model_router))
    graph.add_node("eval_critic", _make_node(eval_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "prompt_engineer")
    graph.add_edge("prompt_engineer", "tool_builder")
    graph.add_edge("tool_builder", "model_router_agent")
    graph.add_edge("model_router_agent", "eval_critic")
    graph.add_conditional_edges(
        "eval_critic",
        _route_decision,
        {"end": END, "revise": "tool_builder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
