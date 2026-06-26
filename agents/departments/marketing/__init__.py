from agents.departments.marketing.copywriter import Copywriter
from agents.departments.marketing.graph import build_marketing_graph
from agents.departments.marketing.marketing_critic import MarketingCritic
from agents.departments.marketing.strategist import MarketingStrategist
from agents.registry import list_agents, register

_AGENTS = {
    "marketing.strategist": MarketingStrategist,
    "marketing.copywriter": Copywriter,
    "marketing.critic": MarketingCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "MarketingStrategist",
    "Copywriter",
    "MarketingCritic",
    "build_marketing_graph",
]
