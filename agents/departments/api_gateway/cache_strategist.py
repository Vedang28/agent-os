from agents.prompts import API_GATEWAY_CACHE_STRATEGIST
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("api_gateway.cache_strategist")


class CacheStrategist:
    name = "api_gateway.cache_strategist"
    role = "worker"

    SYSTEM_PROMPT = API_GATEWAY_CACHE_STRATEGIST

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        prior = state.get("result", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)

        user_prompt = (
            f"Existing implementation:\n{prior}\n\nOriginal request: {request}"
        )

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("cache_strategist produced strategy, revision=%d", revisions)
        return {"result": result}
