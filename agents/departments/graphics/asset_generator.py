from agents.prompts import GRAPHICS_ASSET_GENERATOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("graphics.asset_generator")


class AssetGenerator:
    name = "graphics.asset_generator"
    role = "worker"
    SYSTEM_PROMPT = GRAPHICS_ASSET_GENERATOR

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = f"Art direction:\n{draft}\n\nOriginal request: {request}"
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in self._fixes_for(critique):
                user_prompt += f"- {s}\n"

        if self._tools:
            gen = self._tools.list_tools(namespace="stitch")
            if gen:
                user_prompt += f"\n\nAvailable image-generation tools: {', '.join(gen)}"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("asset_generator produced assets, revision=%d", revisions)
        return {"result": result}

    def _fixes_for(self, critique: dict) -> list[str]:
        return critique.get("suggestions", [critique.get("reason", "")])
