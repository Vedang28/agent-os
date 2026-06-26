from typing import Literal, TypedDict


class AgentState(TypedDict, total=False):
    request: str
    lane: Literal["instant", "fast", "deep"]
    plan: list[str]
    department: str
    departments: list[str]
    project_path: str | None
    task: dict
    draft: str | None
    result: str | None
    critique: dict | None
    approved: bool
    revisions: int
    brain_context: list[dict]
    history: list[dict]
