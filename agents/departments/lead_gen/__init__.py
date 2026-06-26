from agents.departments.lead_gen.enricher import Enricher
from agents.departments.lead_gen.graph import build_lead_gen_graph
from agents.departments.lead_gen.prospector import Prospector
from agents.departments.lead_gen.qualifier import Qualifier
from agents.registry import list_agents, register

_AGENTS = {
    "lead_gen.prospector": Prospector,
    "lead_gen.enricher": Enricher,
    "lead_gen.qualifier": Qualifier,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "Prospector",
    "Enricher",
    "Qualifier",
    "build_lead_gen_graph",
]
