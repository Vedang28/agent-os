from typing import Protocol, runtime_checkable

from core.state import AgentState


@runtime_checkable
class Agent(Protocol):
    name: str

    async def run(self, state: AgentState) -> AgentState: ...
