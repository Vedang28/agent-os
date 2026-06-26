from agents.departments.seo.content_optimizer import ContentOptimizer
from agents.departments.seo.graph import build_seo_graph
from agents.departments.seo.keyword_scout import KeywordScout
from agents.departments.seo.seo_auditor import SeoAuditor
from agents.registry import list_agents, register

_AGENTS = {
    "seo.keyword_scout": KeywordScout,
    "seo.content_optimizer": ContentOptimizer,
    "seo.auditor": SeoAuditor,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "KeywordScout",
    "ContentOptimizer",
    "SeoAuditor",
    "build_seo_graph",
]
