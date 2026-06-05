from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Note(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    backlinks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: list[float] | None = None
