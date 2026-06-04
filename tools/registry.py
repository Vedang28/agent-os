from tools.base import Tool

_registry: dict[str, Tool] = {}


def register(name: str, tool: Tool) -> None:
    if name in _registry:
        raise ValueError(f"Tool already registered: {name}")
    _registry[name] = tool


def get(name: str) -> Tool:
    return _registry[name]


def list_tools() -> list[str]:
    return list(_registry.keys())


def clear() -> None:
    _registry.clear()
