from agents.departments.bug_triage.bug_classifier import BugClassifier
from agents.departments.bug_triage.bug_reproducer import BugReproducer
from agents.departments.bug_triage.bug_validator import BugValidator
from agents.departments.bug_triage.graph import build_bug_triage_graph
from agents.registry import list_agents, register

_AGENTS = {
    "bug_triage.bug_classifier": BugClassifier,
    "bug_triage.bug_reproducer": BugReproducer,
    "bug_triage.bug_validator": BugValidator,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "BugClassifier",
    "BugReproducer",
    "BugValidator",
    "build_bug_triage_graph",
]
