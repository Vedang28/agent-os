from agents.departments.auth.access_control import AccessControlBuilder
from agents.departments.auth.architect import AuthArchitect
from agents.departments.auth.auth_critic import AuthCritic
from agents.departments.auth.graph import build_auth_graph
from agents.departments.auth.token_manager import TokenManager
from agents.registry import list_agents, register

_AGENTS = {
    "auth.architect": AuthArchitect,
    "auth.token_manager": TokenManager,
    "auth.access_control": AccessControlBuilder,
    "auth.auth_critic": AuthCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "AuthArchitect",
    "TokenManager",
    "AccessControlBuilder",
    "AuthCritic",
    "build_auth_graph",
]
