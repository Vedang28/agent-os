from agents.departments.dev_testing.graph import build_dev_testing_graph
from agents.departments.dev_testing.test_critic import DevTestCritic
from agents.departments.dev_testing.test_planner import TestPlanner
from agents.departments.dev_testing.test_writer_dev import DevTestWriter
from agents.registry import list_agents, register

_AGENTS = {
    "dev_testing.test_planner": TestPlanner,
    "dev_testing.test_writer": DevTestWriter,
    "dev_testing.test_critic": DevTestCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "TestPlanner",
    "DevTestWriter",
    "DevTestCritic",
    "build_dev_testing_graph",
]
