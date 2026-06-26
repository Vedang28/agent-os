from agents.departments.video.graph import build_video_graph
from agents.departments.video.video_capturer import VideoCapturer
from agents.departments.video.video_critic import VideoCritic
from agents.departments.video.video_summarizer import VideoSummarizer
from agents.registry import list_agents, register

_AGENTS = {
    "video.video_summarizer": VideoSummarizer,
    "video.video_capturer": VideoCapturer,
    "video.video_critic": VideoCritic,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "VideoSummarizer",
    "VideoCapturer",
    "VideoCritic",
    "build_video_graph",
]
