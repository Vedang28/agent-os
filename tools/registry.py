from tools.base import Tool

_registry: dict[str, Tool] = {}


def register(name: str, tool: Tool) -> None:
    if name in _registry:
        raise ValueError(f"Tool already registered: {name}")
    _registry[name] = tool


def get(name: str) -> Tool:
    return _registry[name]


def list_tools(namespace: str | None = None) -> list[str]:
    if namespace is None:
        return list(_registry.keys())
    prefix = namespace + "."
    return [k for k in _registry if k.startswith(prefix)]


def clear() -> None:
    _registry.clear()
