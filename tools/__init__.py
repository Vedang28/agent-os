from tools.base import Permission, Tool, set_permission_checker
from tools.registry import clear, get, list_tools, register


def register_all() -> None:
    from tools.bash import BashTool
    from tools.browser import BrowserTool
    from tools.file import FileTool
    from tools.web import WebTool

    register("bash", BashTool())
    register("browser", BrowserTool())
    register("file", FileTool())
    register("web", WebTool())


__all__ = [
    "Permission",
    "Tool",
    "register",
    "get",
    "list_tools",
    "clear",
    "register_all",
    "set_permission_checker",
]
