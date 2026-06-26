from agents.departments.dependency.dep_scanner import DepScanner
from agents.departments.dependency.dep_upgrader import DepUpgrader
from agents.departments.dependency.dep_validator import DepValidator
from agents.departments.dependency.graph import build_dependency_graph
from agents.registry import list_agents, register

_AGENTS = {
    "dependency.dep_scanner": DepScanner,
    "dependency.dep_upgrader": DepUpgrader,
    "dependency.dep_validator": DepValidator,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "DepScanner",
    "DepUpgrader",
    "DepValidator",
    "build_dependency_graph",
]
