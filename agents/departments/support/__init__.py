from agents.departments.support.escalation_critic import EscalationCritic
from agents.departments.support.graph import build_support_graph
from agents.departments.support.resolver import Resolver
from agents.departments.support.ticket_triager import TicketTriager
from agents.registry import list_agents, register

_AGENTS = {
    "support.ticket_triager": TicketTriager,
    "support.resolver": Resolver,
    "support.escalation_critic": EscalationCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "TicketTriager",
    "Resolver",
    "EscalationCritic",
    "build_support_graph",
]
