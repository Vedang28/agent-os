from agents.departments.code_review.graph import build_code_review_graph
from agents.departments.code_review.review_critic import ReviewCritic
from agents.departments.code_review.review_planner import ReviewPlanner
from agents.departments.code_review.reviewer import CodeReviewer
from agents.registry import list_agents, register

_AGENTS = {
    "code_review.review_planner": ReviewPlanner,
    "code_review.reviewer": CodeReviewer,
    "code_review.review_critic": ReviewCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "ReviewPlanner",
    "CodeReviewer",
    "ReviewCritic",
    "build_code_review_graph",
]
