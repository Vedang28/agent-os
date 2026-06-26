from agents.departments.memory.decision_recorder import DecisionRecorder
from agents.departments.memory.graph import build_memory_graph
from agents.departments.memory.log_auditor import LogAuditor
from agents.departments.memory.session_scribe import SessionScribe
from agents.registry import list_agents, register

_AGENTS = {
    "memory.session_scribe": SessionScribe,
    "memory.decision_recorder": DecisionRecorder,
    "memory.log_auditor": LogAuditor,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "SessionScribe",
    "DecisionRecorder",
    "LogAuditor",
    "build_memory_graph",
]
