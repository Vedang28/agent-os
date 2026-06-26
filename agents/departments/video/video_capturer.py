from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import VIDEO_CAPTURER

logger = get_logger("video.video_capturer")


class VideoCapturer:
    name = "video.video_capturer"
    role = "worker"

    SYSTEM_PROMPT = VIDEO_CAPTURER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = f"Plan/Draft:\n{draft}\n\nOriginal request: {request}"
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("video_capturer produced result, revision=%d", revisions)
        return {"result": result}
