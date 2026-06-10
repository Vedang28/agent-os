from agents.departments.engineering.architect import Architect
from agents.departments.engineering.code_doctor import CodeDoctor
from agents.departments.engineering.graph import build_engineering_graph
from agents.departments.engineering.scaffolder import Scaffolder
from agents.registry import list_agents, register

_AGENTS = {
    "engineering.architect": Architect,
    "engineering.scaffolder": Scaffolder,
    "engineering.code_doctor": CodeDoctor,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = ["Architect", "Scaffolder", "CodeDoctor", "build_engineering_graph"]
