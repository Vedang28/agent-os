from agents.departments.document.doc_critic import DocCritic
from agents.departments.document.doc_extractor import DocExtractor
from agents.departments.document.doc_ingester import DocIngester
from agents.departments.document.graph import build_document_graph
from agents.registry import list_agents, register

_AGENTS = {
    "document.doc_extractor": DocExtractor,
    "document.doc_ingester": DocIngester,
    "document.doc_critic": DocCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "DocExtractor",
    "DocIngester",
    "DocCritic",
    "build_document_graph",
]
