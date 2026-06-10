from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("infra.model_router")


class ModelConfig(BaseModel):
    model_name: str
    provider: str
    api_base: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


_DEFAULT_ROUTES: dict[str, ModelConfig] = {
    "code": ModelConfig(
        model_name="claude-sonnet-4-6",
        provider="anthropic",
        api_base="https://api.anthropic.com",
        max_tokens=8192,
        temperature=0.3,
    ),
    "long_docs": ModelConfig(
        model_name="gemini-2.0-flash",
        provider="google",
        api_base="https://generativelanguage.googleapis.com",
        max_tokens=32768,
        temperature=0.4,
    ),
    "triage": ModelConfig(
        model_name="llama3",
        provider="local",
        api_base="http://localhost:11434",
        max_tokens=2048,
        temperature=0.5,
    ),
    "default": ModelConfig(
        model_name="claude-sonnet-4-6",
        provider="anthropic",
        api_base="https://api.anthropic.com",
        max_tokens=4096,
        temperature=0.7,
    ),
}

_routes: dict[str, ModelConfig] = dict(_DEFAULT_ROUTES)


def route(task_type: str) -> ModelConfig:
    config = _routes.get(task_type, _routes["default"])
    logger.info("routed task_type=%s to model=%s", task_type, config.model_name)
    return config


def set_route(task_type: str, config: ModelConfig) -> None:
    _routes[task_type] = config
    logger.info("updated route: task_type=%s -> model=%s", task_type, config.model_name)


def list_models() -> dict[str, ModelConfig]:
    return dict(_routes)


def reset_routes() -> None:
    _routes.clear()
    _routes.update(_DEFAULT_ROUTES)
