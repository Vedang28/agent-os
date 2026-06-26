from agents.departments.observability.alert_designer import AlertDesigner
from agents.departments.observability.graph import build_observability_graph
from agents.departments.observability.incident_responder import IncidentResponder
from agents.departments.observability.telemetry_engineer import TelemetryEngineer
from agents.registry import list_agents, register

_AGENTS = {
    "observability.telemetry_engineer": TelemetryEngineer,
    "observability.alert_designer": AlertDesigner,
    "observability.incident_responder": IncidentResponder,
}

for _name, _cls in _AGENTS.items():
    if _name not in list_agents():
        register(_name, _cls())

__all__ = [
    "TelemetryEngineer",
    "AlertDesigner",
    "IncidentResponder",
    "build_observability_graph",
]
