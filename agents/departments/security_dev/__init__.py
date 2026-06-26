from agents.departments.security_dev.graph import build_security_dev_graph
from agents.departments.security_dev.security_analyst import SecurityAnalyst
from agents.departments.security_dev.security_scanner import SecurityScanner
from agents.departments.security_dev.security_skeptic import SecuritySkeptic
from agents.registry import list_agents, register

_AGENTS = {
    "security_dev.security_scanner": SecurityScanner,
    "security_dev.security_analyst": SecurityAnalyst,
    "security_dev.security_skeptic": SecuritySkeptic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "SecurityScanner",
    "SecurityAnalyst",
    "SecuritySkeptic",
    "build_security_dev_graph",
]
