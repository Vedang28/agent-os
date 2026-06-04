from abc import ABC, abstractmethod

from core.state import AgentState


class SecurityGate(ABC):
    @abstractmethod
    async def review(self, state: AgentState) -> AgentState:
        """Review output for security vulnerabilities.

        Returns state with approved=False and critique populated if issues found.
        """
        ...
