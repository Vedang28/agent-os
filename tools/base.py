from abc import ABC, abstractmethod
from enum import Enum


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    DESTRUCTIVE = "destructive"


class Tool(ABC):
    name: str
    permission: Permission

    @abstractmethod
    async def execute(self, **kwargs) -> str: ...
