from agents.departments.cloud.architect import CloudArchitect
from agents.departments.cloud.cost_watcher import CostWatcher
from agents.departments.cloud.graph import build_cloud_graph
from agents.departments.cloud.provisioner import Provisioner
from agents.departments.cloud.reliability_critic import ReliabilityCritic
from agents.registry import list_agents, register

_AGENTS = {
    "cloud.architect": CloudArchitect,
    "cloud.provisioner": Provisioner,
    "cloud.cost_watcher": CostWatcher,
    "cloud.reliability_critic": ReliabilityCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "CloudArchitect",
    "Provisioner",
    "CostWatcher",
    "ReliabilityCritic",
    "build_cloud_graph",
]
