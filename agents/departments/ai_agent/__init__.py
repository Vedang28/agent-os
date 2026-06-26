from agents.departments.ai_agent.eval_critic import EvalCritic
from agents.departments.ai_agent.graph import build_ai_agent_graph
from agents.departments.ai_agent.model_router_agent import ModelRouterAgent
from agents.departments.ai_agent.prompt_engineer import PromptEngineer
from agents.departments.ai_agent.tool_builder import ToolFunctionBuilder
from agents.registry import list_agents, register

_AGENTS = {
    "ai_agent.prompt_engineer": PromptEngineer,
    "ai_agent.tool_builder": ToolFunctionBuilder,
    "ai_agent.model_router_agent": ModelRouterAgent,
    "ai_agent.eval_critic": EvalCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "PromptEngineer",
    "ToolFunctionBuilder",
    "ModelRouterAgent",
    "EvalCritic",
    "build_ai_agent_graph",
]
