from agents.prompts import ML_TRAINER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ml.trainer")


class Trainer:
    name = "ml.trainer"
    role = "worker"

    SYSTEM_PROMPT = ML_TRAINER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        parts = [
            f"Original request: {request}",
            "",
            f"Data pipeline plan:\n{draft}",
            "",
            f"Embedding pipeline produced so far (build on this):\n{result}",
        ]

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            parts.append("")
            parts.append(f"Revision {revisions}. Fix these issues:")
            parts += [f"- {s}" for s in suggestions]

        user_prompt = "\n".join(parts)

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("trainer produced training pipeline, revision=%d", revisions)
        return {"result": result}
