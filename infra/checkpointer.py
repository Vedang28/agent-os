from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from infra.telemetry import get_logger

logger = get_logger("infra.checkpointer")


class CheckpointerConfig(BaseModel):
    backend: Literal["memory", "sqlite", "postgres"] = "memory"
    connection_string: str | None = Field(default=None, repr=False)
    db_path: str | None = None


_checkpointer = None


def get_checkpointer(config: CheckpointerConfig | None = None):
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    if config is None:
        config = CheckpointerConfig(
            backend=os.environ.get("AGENT_OS_CHECKPOINTER_BACKEND", "memory"),
            connection_string=os.environ.get("AGENT_OS_CHECKPOINTER_DSN"),
            db_path=os.environ.get("AGENT_OS_CHECKPOINTER_DB_PATH"),
        )

    if config.backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        _checkpointer = MemorySaver()
    elif config.backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError:
            raise ImportError(
                "langgraph-checkpoint-sqlite is required for SQLite backend. "
                "Install with: pip install langgraph-checkpoint-sqlite"
            )
        _checkpointer = SqliteSaver.from_conn_string(config.db_path or ":memory:")
    elif config.backend == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            raise ImportError(
                "langgraph-checkpoint-postgres is required for Postgres backend. "
                "Install with: pip install langgraph-checkpoint-postgres"
            )
        if not config.connection_string:
            raise ValueError("connection_string required for postgres backend")
        _checkpointer = PostgresSaver.from_conn_string(config.connection_string)
    else:
        raise ValueError(f"Unknown backend: {config.backend}")

    logger.info("checkpointer backend=%s", config.backend)
    return _checkpointer


def reset_checkpointer() -> None:
    global _checkpointer
    _checkpointer = None
