from agents.departments.documentation.doc_detector import DocDetector
from agents.departments.documentation.doc_reviewer import DocReviewer
from agents.departments.documentation.doc_writer import DocWriter
from agents.departments.documentation.graph import build_documentation_graph
from agents.registry import list_agents, register

_AGENTS = {
    "documentation.doc_detector": DocDetector,
    "documentation.doc_writer": DocWriter,
    "documentation.doc_reviewer": DocReviewer,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "DocDetector",
    "DocWriter",
    "DocReviewer",
    "build_documentation_graph",
]
