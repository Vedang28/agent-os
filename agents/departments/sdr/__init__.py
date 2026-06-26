from agents.departments.sdr.graph import build_sdr_graph
from agents.departments.sdr.message_writer import MessageWriter
from agents.departments.sdr.outreach_planner import OutreachPlanner
from agents.departments.sdr.reply_handler import ReplyHandler
from agents.registry import list_agents, register

_AGENTS = {
    "sdr.outreach_planner": OutreachPlanner,
    "sdr.message_writer": MessageWriter,
    "sdr.reply_handler": ReplyHandler,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "OutreachPlanner",
    "MessageWriter",
    "ReplyHandler",
    "build_sdr_graph",
]
