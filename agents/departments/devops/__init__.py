from agents.departments.devops.architect import CiCdArchitect
from agents.departments.devops.deploy_critic import DeployCritic
from agents.departments.devops.graph import build_devops_graph
from agents.departments.devops.pipeline_builder import PipelineBuilder
from agents.departments.devops.release_manager import ReleaseManager
from agents.registry import list_agents, register

_AGENTS = {
    "devops.architect": CiCdArchitect,
    "devops.pipeline_builder": PipelineBuilder,
    "devops.release_manager": ReleaseManager,
    "devops.deploy_critic": DeployCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "CiCdArchitect",
    "PipelineBuilder",
    "ReleaseManager",
    "DeployCritic",
    "build_devops_graph",
]
