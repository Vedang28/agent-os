from agents.departments.devops_ci.ci_fixer import CiFixer
from agents.departments.devops_ci.ci_monitor import CiMonitor
from agents.departments.devops_ci.ci_validator import CiValidator
from agents.departments.devops_ci.graph import build_devops_ci_graph
from agents.registry import list_agents, register

_AGENTS = {
    "devops_ci.ci_monitor": CiMonitor,
    "devops_ci.ci_fixer": CiFixer,
    "devops_ci.ci_validator": CiValidator,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "CiMonitor",
    "CiFixer",
    "CiValidator",
    "build_devops_ci_graph",
]
