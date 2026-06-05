from tools.base import Permission, Tool, set_permission_checker

AUTO_APPROVED = frozenset({Permission.READ, Permission.WRITE})


def default_checker(tool: Tool) -> bool:
    return tool.permission in AUTO_APPROVED


def install_default_checker() -> None:
    set_permission_checker(default_checker)
