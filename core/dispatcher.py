from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("core.dispatcher")

_INSTANT_KEYWORDS = frozenset([
    "hello", "hi", "hey", "greetings", "good morning", "good evening",
    "good night", "bye", "goodbye", "thanks", "thank you", "ping",
])

_DEEP_KEYWORDS = frozenset([
    "build", "create", "design", "implement", "architect", "develop",
    "refactor", "migrate", "deploy", "scaffold", "generate", "write code",
    "rest api", "authentication", "database schema", "microservice",
    "briefing", "intelligence", "research", "analyze trends", "daily brief",
    "scan news", "trending", "investigate",
])


def _normalize(text: str) -> str:
    return text.lower().strip()


def _is_instant(request: str) -> bool:
    normalized = _normalize(request)
    if normalized in _INSTANT_KEYWORDS:
        return True
    words = set(normalized.split())
    if words & {"hello", "hi", "hey", "ping", "bye", "goodbye"}:
        return True
    if normalized.startswith("what time") or normalized.startswith("what's the time"):
        return True
    return False


def _is_deep(request: str) -> bool:
    normalized = _normalize(request)
    for keyword in _DEEP_KEYWORDS:
        if keyword in normalized:
            return True
    if len(normalized.split()) > 15:
        return True
    return False


def assign_lane(state: AgentState) -> dict:
    request = state.get("request", "")

    if _is_instant(request):
        lane = "instant"
    elif _is_deep(request):
        lane = "deep"
    else:
        lane = "fast"

    logger.info("assigned lane=%s for request=%r", lane, request[:80])
    return {"lane": lane}
