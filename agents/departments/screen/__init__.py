from agents.departments.screen.frame_critic import FrameCritic
from agents.departments.screen.graph import build_screen_graph
from agents.departments.screen.screen_watcher import ScreenWatcher
from agents.departments.screen.vision_reader import VisionReader
from agents.registry import list_agents, register

_AGENTS = {
    "screen.vision_reader": VisionReader,
    "screen.screen_watcher": ScreenWatcher,
    "screen.frame_critic": FrameCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = ["VisionReader", "ScreenWatcher", "FrameCritic", "build_screen_graph"]
