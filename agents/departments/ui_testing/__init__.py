from agents.departments.ui_testing.graph import build_ui_testing_graph
from agents.departments.ui_testing.playwright_operator import PlaywrightOperator
from agents.departments.ui_testing.visual_regression_critic import VisualRegressionCritic
from agents.departments.ui_testing.visual_test_designer import VisualTestDesigner
from agents.registry import list_agents, register

_AGENTS = {
    "ui_testing.visual_test_designer": VisualTestDesigner,
    "ui_testing.playwright_operator": PlaywrightOperator,
    "ui_testing.visual_regression_critic": VisualRegressionCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "VisualTestDesigner",
    "PlaywrightOperator",
    "VisualRegressionCritic",
    "build_ui_testing_graph",
]
