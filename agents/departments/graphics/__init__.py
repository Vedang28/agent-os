from agents.departments.graphics.art_director import ArtDirector
from agents.departments.graphics.asset_generator import AssetGenerator
from agents.departments.graphics.brand_keeper import BrandKeeper
from agents.departments.graphics.graph import build_graphics_graph
from agents.departments.graphics.graphics_critic import GraphicsCritic
from agents.registry import list_agents, register

_AGENTS = {
    "graphics.art_director": ArtDirector,
    "graphics.asset_generator": AssetGenerator,
    "graphics.brand_keeper": BrandKeeper,
    "graphics.graphics_critic": GraphicsCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "ArtDirector",
    "AssetGenerator",
    "BrandKeeper",
    "GraphicsCritic",
    "build_graphics_graph",
]
