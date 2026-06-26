from agents.departments.finance.bookkeeper import Bookkeeper
from agents.departments.finance.compliance_critic import ComplianceCritic
from agents.departments.finance.graph import build_finance_graph
from agents.departments.finance.reporter import Reporter
from agents.registry import list_agents, register

_AGENTS = {
    "finance.bookkeeper": Bookkeeper,
    "finance.reporter": Reporter,
    "finance.compliance_critic": ComplianceCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "Bookkeeper",
    "Reporter",
    "ComplianceCritic",
    "build_finance_graph",
]
