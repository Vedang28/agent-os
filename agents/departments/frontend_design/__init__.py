from agents.departments.frontend_design.design_critic import DesignCritic
from agents.departments.frontend_design.graph import build_frontend_design_graph
from agents.departments.frontend_design.interaction_designer import (
    InteractionDesigner,
)
from agents.departments.frontend_design.ui_stylist import UiStylist
from agents.departments.frontend_design.ux_designer import UxDesigner
from agents.registry import list_agents, register

_AGENTS = {
    "frontend_design.ux_designer": UxDesigner,
    "frontend_design.ui_stylist": UiStylist,
    "frontend_design.interaction_designer": InteractionDesigner,
    "frontend_design.design_critic": DesignCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "UxDesigner",
    "UiStylist",
    "InteractionDesigner",
    "DesignCritic",
    "build_frontend_design_graph",
]
