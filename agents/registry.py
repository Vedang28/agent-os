from agents.protocol import Agent

_registry: dict[str, Agent] = {}


def register(name: str, agent: Agent) -> None:
    if name in _registry:
        raise ValueError(f"Agent already registered: {name}")
    _registry[name] = agent


def get(name: str) -> Agent:
    return _registry[name]


def list_agents() -> list[str]:
    return list(_registry.keys())


def clear() -> None:
    _registry.clear()
