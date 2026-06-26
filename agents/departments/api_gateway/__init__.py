from agents.departments.api_gateway.architect import GatewayArchitect
from agents.departments.api_gateway.cache_strategist import CacheStrategist
from agents.departments.api_gateway.graph import build_api_gateway_graph
from agents.departments.api_gateway.load_critic import LoadCritic
from agents.departments.api_gateway.rate_limiter import RateLimitEngineer
from agents.registry import list_agents, register

_AGENTS = {
    "api_gateway.architect": GatewayArchitect,
    "api_gateway.rate_limiter": RateLimitEngineer,
    "api_gateway.cache_strategist": CacheStrategist,
    "api_gateway.load_critic": LoadCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "GatewayArchitect",
    "RateLimitEngineer",
    "CacheStrategist",
    "LoadCritic",
    "build_api_gateway_graph",
]
