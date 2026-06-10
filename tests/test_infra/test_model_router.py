import pytest

from infra.model_router import ModelConfig, list_models, reset_routes, route, set_route


@pytest.fixture(autouse=True)
def _clean():
    reset_routes()
    yield
    reset_routes()


class TestRoute:
    def test_code_returns_claude(self):
        cfg = route("code")
        assert cfg.provider == "anthropic"
        assert "claude" in cfg.model_name.lower()

    def test_long_docs_returns_gemini(self):
        cfg = route("long_docs")
        assert cfg.provider == "google"
        assert "gemini" in cfg.model_name.lower()

    def test_triage_returns_local(self):
        cfg = route("triage")
        assert cfg.provider == "local"

    def test_unknown_returns_default(self):
        cfg = route("unknown_task_type")
        assert cfg.provider == "anthropic"

    def test_default_returns_claude(self):
        cfg = route("default")
        assert cfg.provider == "anthropic"


class TestSetRoute:
    def test_override_route(self):
        custom = ModelConfig(
            model_name="custom-model",
            provider="custom",
            max_tokens=1024,
        )
        set_route("code", custom)
        assert route("code").model_name == "custom-model"

    def test_add_new_route(self):
        custom = ModelConfig(model_name="summarizer", provider="local")
        set_route("summarize", custom)
        assert route("summarize").model_name == "summarizer"


class TestListModels:
    def test_returns_all_routes(self):
        models = list_models()
        assert "code" in models
        assert "long_docs" in models
        assert "triage" in models
        assert "default" in models

    def test_returns_model_config_instances(self):
        for cfg in list_models().values():
            assert isinstance(cfg, ModelConfig)


class TestModelConfig:
    def test_validates_required_fields(self):
        cfg = ModelConfig(model_name="test", provider="test")
        assert cfg.model_name == "test"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.7

    def test_optional_api_base(self):
        cfg = ModelConfig(model_name="test", provider="test")
        assert cfg.api_base is None
