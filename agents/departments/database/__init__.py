from agents.departments.database.architect import DatabaseArchitect
from agents.departments.database.graph import build_database_graph
from agents.departments.database.integrity_critic import DataIntegrityCritic
from agents.departments.database.migration_runner import MigrationRunner
from agents.departments.database.query_writer import QueryWriter
from agents.registry import list_agents, register

_AGENTS = {
    "database.architect": DatabaseArchitect,
    "database.query_writer": QueryWriter,
    "database.migration_runner": MigrationRunner,
    "database.integrity_critic": DataIntegrityCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "DatabaseArchitect",
    "QueryWriter",
    "MigrationRunner",
    "DataIntegrityCritic",
    "build_database_graph",
]
