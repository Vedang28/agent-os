from agents.departments.testing.bug_triager import BugTriager
from agents.departments.testing.graph import build_testing_graph
from agents.departments.testing.strategist import TestStrategist
from agents.departments.testing.test_executor import TestExecutor
from agents.departments.testing.test_writer import TestWriter
from agents.registry import list_agents, register

_AGENTS = {
    "testing.strategist": TestStrategist,
    "testing.test_writer": TestWriter,
    "testing.test_executor": TestExecutor,
    "testing.bug_triager": BugTriager,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "TestStrategist",
    "TestWriter",
    "TestExecutor",
    "BugTriager",
    "build_testing_graph",
]
