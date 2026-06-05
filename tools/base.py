from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    DESTRUCTIVE = "destructive"


_AUTO_APPROVED = frozenset({Permission.READ, Permission.WRITE})

PermissionChecker = Callable[["Tool"], bool]

_active_checker: PermissionChecker | None = None


def set_permission_checker(checker: PermissionChecker | None) -> None:
    global _active_checker
    _active_checker = checker


def get_permission_checker() -> PermissionChecker | None:
    return _active_checker


class Tool(ABC):
    name: str
    permission: Permission

    async def execute(self, **kwargs) -> str:
        checker = _active_checker
        if checker is not None and not checker(self):
            raise PermissionError(
                f"Tool '{self.name}' requires {self.permission.value} permission, "
                f"which is not approved."
            )
        return await self._run(**kwargs)

    @abstractmethod
    async def _run(self, **kwargs) -> str: ...
