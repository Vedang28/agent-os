from agents.departments.intelligence.analyst import Analyst
from agents.departments.intelligence.graph import build_intelligence_graph
from agents.departments.intelligence.scout import Scout
from agents.departments.intelligence.skeptic import Skeptic
from agents.registry import list_agents, register

_AGENTS = {
    "intelligence.scout": Scout,
    "intelligence.analyst": Analyst,
    "intelligence.skeptic": Skeptic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = ["Scout", "Analyst", "Skeptic", "build_intelligence_graph"]
