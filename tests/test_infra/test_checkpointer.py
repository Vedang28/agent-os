import pytest
from unittest.mock import patch, MagicMock

from langgraph.checkpoint.memory import MemorySaver

from infra.checkpointer import CheckpointerConfig, get_checkpointer, reset_checkpointer


@pytest.fixture(autouse=True)
def _reset():
    reset_checkpointer()
    yield
    reset_checkpointer()


class TestCheckpointerConfig:
    def test_defaults(self):
        config = CheckpointerConfig()
        assert config.backend == "memory"
        assert config.connection_string is None
        assert config.db_path is None

    def test_backend_literal(self):
        for backend in ("memory", "sqlite", "postgres"):
            config = CheckpointerConfig(backend=backend)
            assert config.backend == backend

    def test_invalid_backend_rejected(self):
        with pytest.raises(Exception):
            CheckpointerConfig(backend="redis")


class TestGetCheckpointer:
    def test_default_is_memory(self):
        cp = get_checkpointer()
        assert isinstance(cp, MemorySaver)

    def test_memory_explicit(self):
        config = CheckpointerConfig(backend="memory")
        cp = get_checkpointer(config)
        assert isinstance(cp, MemorySaver)

    def test_sqlite_import_error(self):
        with patch.dict("sys.modules", {"langgraph.checkpoint.sqlite": None}):
            config = CheckpointerConfig(backend="sqlite")
            with pytest.raises(ImportError, match="langgraph-checkpoint-sqlite"):
                get_checkpointer(config)

    def test_postgres_import_error(self):
        with patch.dict("sys.modules", {"langgraph.checkpoint.postgres": None}):
            config = CheckpointerConfig(backend="postgres", connection_string="postgresql://x")
            with pytest.raises(ImportError, match="langgraph-checkpoint-postgres"):
                get_checkpointer(config)

    def test_postgres_requires_connection_string(self):
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"langgraph.checkpoint.postgres": mock_module}):
            config = CheckpointerConfig(backend="postgres")
            with pytest.raises(ValueError, match="connection_string required"):
                get_checkpointer(config)

    def test_singleton_pattern(self):
        cp1 = get_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is cp2

    def test_reset(self):
        cp1 = get_checkpointer()
        reset_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is not cp2

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_OS_CHECKPOINTER_BACKEND", "memory")
        cp = get_checkpointer()
        assert isinstance(cp, MemorySaver)

    def test_unknown_backend(self):
        config = CheckpointerConfig.model_construct(
            backend="redis", connection_string=None, db_path=None
        )
        with pytest.raises(ValueError, match="Unknown backend: redis"):
            get_checkpointer(config)
