from agents.departments.frontend.architect import FrontendArchitect
from agents.departments.frontend.component_builder import ComponentBuilder
from agents.departments.frontend.graph import build_frontend_graph
from agents.departments.frontend.reviewer import FrontendReviewer
from agents.departments.frontend.state_wirer import StateWirer
from agents.registry import list_agents, register

_AGENTS = {
    "frontend.architect": FrontendArchitect,
    "frontend.component_builder": ComponentBuilder,
    "frontend.state_wirer": StateWirer,
    "frontend.reviewer": FrontendReviewer,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "FrontendArchitect",
    "ComponentBuilder",
    "StateWirer",
    "FrontendReviewer",
    "build_frontend_graph",
]
