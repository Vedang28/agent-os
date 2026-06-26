from agents.departments.ml.data_curator import DataCurator
from agents.departments.ml.embedding_engineer import EmbeddingEngineer
from agents.departments.ml.graph import build_ml_graph
from agents.departments.ml.ml_critic import MLCritic
from agents.departments.ml.trainer import Trainer
from agents.registry import list_agents, register

_AGENTS = {
    "ml.data_curator": DataCurator,
    "ml.embedding_engineer": EmbeddingEngineer,
    "ml.trainer": Trainer,
    "ml.ml_critic": MLCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "DataCurator",
    "EmbeddingEngineer",
    "Trainer",
    "MLCritic",
    "build_ml_graph",
]
