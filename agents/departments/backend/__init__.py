from agents.departments.backend.api_builder import ApiBuilder
from agents.departments.backend.architect import BackendArchitect
from agents.departments.backend.graph import build_backend_graph
from agents.departments.backend.reviewer import BackendReviewer
from agents.departments.backend.schema_designer import SchemaDesigner
from agents.registry import list_agents, register

_AGENTS = {
    "backend.architect": BackendArchitect,
    "backend.api_builder": ApiBuilder,
    "backend.schema_designer": SchemaDesigner,
    "backend.reviewer": BackendReviewer,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "BackendArchitect",
    "ApiBuilder",
    "SchemaDesigner",
    "BackendReviewer",
    "build_backend_graph",
]
