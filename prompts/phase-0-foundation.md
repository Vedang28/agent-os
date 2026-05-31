# Phase 0 — Foundation

> **Active phase.** Both tracks work together — no split yet.

You are building the foundation layer for **agent-os**, an autonomous multi-agent company. Read `CLAUDE.md` and `docs/EXECUTION_PLAN.md` first — they are the source of truth. Do NOT start Phase 1 work.

## How to run this phase

**Option A — Single session (simplest):**
Paste this prompt and work through each section sequentially.

**Option B — Workflow (recommended for speed):**
Say: `Run a workflow to execute Phase 0 of agent-os — build the foundation layer`
This fans out the independent pieces (folders, protocol, state, graph, telemetry, tests) in parallel.

**Option C — Agent view (parallel sessions):**
Open `claude agents` and dispatch:
1. `@spine-builder Build Phase 0: folders, Agent protocol, AgentState schema, empty LangGraph, telemetry`
2. `@edge-builder Build Phase 0: folders, Tool base + Permission enum, tool registry`
Then dispatch `@gate-checker Verify Phase 0 exit gate` when both finish.

---

## What to build

### 1. Monorepo + layered folders
Create the full folder structure with `__init__.py` files:
```
/core          — graph.py, state.py (+ empty dispatcher.py, orchestrator.py stubs)
/agents        — protocol.py, registry.py, /departments/engineering/ (empty for now)
/tools         — base.py (Permission enum), registry.py
/brain         — (empty __init__.py only — Phase 1)
/integrations  — (empty __init__.py only — Phase 6)
/io            — (empty __init__.py only — Phase 5)
/infra         — telemetry.py
/dashboard     — (empty — Phase 5)
/tests         — mirrors the layer folders: tests/test_core/, tests/test_agents/, tests/test_tools/, tests/test_infra/
```

### 2. Python environment
- `pyproject.toml` with Python 3.12, dependencies: `langgraph`, `langchain-core`, `pydantic`, `pytest`, `ruff`.
- Dev dependencies: `black`, `ruff`, `pre-commit`.
- A `.pre-commit-config.yaml` with ruff + black hooks.
- A basic `Makefile` with targets: `install`, `lint`, `test`, `run`.

### 3. Agent protocol + empty registry
In `agents/protocol.py`:
```python
from typing import Protocol, runtime_checkable
from core.state import AgentState

@runtime_checkable
class Agent(Protocol):
    name: str
    async def run(self, state: AgentState) -> AgentState: ...
```
In `agents/registry.py`: a dict-based registry that loads agents by name. No if-elif dispatch — use the registry pattern. It should work even with zero agents registered. Provide `register(name, agent)`, `get(name)`, and `list_agents()`.

### 4. Security Gate base class
In `agents/security_gate.py`: a base class for the Security Gate that will be wired into every code-producing department's sub-graph (after the Critic node). For Phase 0, just the interface:
```python
from abc import ABC, abstractmethod
from core.state import AgentState

class SecurityGate(ABC):
    @abstractmethod
    async def review(self, state: AgentState) -> AgentState:
        """Review output for security vulnerabilities. Return state with approved=False if issues found."""
        ...
```
This gets implemented fully in Phase 2 when sub-graphs are wired.

### 5. Tool base + Permission enum
In `tools/base.py`:
```python
from enum import Enum
from abc import ABC, abstractmethod

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    DESTRUCTIVE = "destructive"

class Tool(ABC):
    name: str
    permission: Permission

    @abstractmethod
    async def execute(self, **kwargs) -> str: ...
```
In `tools/registry.py`: a dict-based tool registry, same pattern as agents. Provide `register(name, tool)`, `get(name)`, and `list_tools()`.

### 5. AgentState typed schema
In `core/state.py`, define the full typed state:
```python
from typing import TypedDict, Literal

class AgentState(TypedDict, total=False):
    request: str
    lane: Literal["instant", "fast", "deep"]
    plan: list[str]
    department: str
    task: dict
    draft: str | None
    result: str | None
    critique: dict | None
    approved: bool
    revisions: int
    brain_context: list[dict]
    history: list[dict]
```
Use `total=False` so partial states work in tests and early phases. Simple dicts for `Task`, `Critique`, `Note`, `Step` for now — they'll become Pydantic models in Phase 2.

### 6. Empty LangGraph that compiles and runs
In `core/graph.py`: build a `StateGraph(AgentState)` with a single pass-through node that sets `approved = True`, then add `START → pass_through → END`. It must compile and run end-to-end with a minimal input state. This proves the LangGraph wiring works.

```python
from langgraph.graph import StateGraph, START, END
from core.state import AgentState

def pass_through(state: AgentState) -> dict:
    return {"approved": True}

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("pass_through", pass_through)
    graph.add_edge(START, "pass_through")
    graph.add_edge("pass_through", END)
    return graph.compile()
```

### 7. Telemetry skeleton
In `infra/telemetry.py`: structured logging setup using Python's `logging` module with JSON formatting. Provide a `get_logger(name)` function that returns a configured logger. No external dependencies — just stdlib.

### 8. CI + tests
- A `tests/` folder with at least:
  - `tests/test_core/test_state.py` — AgentState can be instantiated with defaults.
  - `tests/test_core/test_graph.py` — the empty graph compiles and runs end-to-end.
  - `tests/test_agents/test_registry.py` — agent registry: loads empty, register one, retrieve it.
  - `tests/test_tools/test_registry.py` — tool registry: loads empty, register one, retrieve it.
  - `tests/test_infra/test_telemetry.py` — logger emits structured JSON output.
- A `.github/workflows/ci.yml` that runs `pytest` on push/PR (Python 3.12).
- A `conftest.py` at the root that adds the project to `sys.path`.

### 9. Memory system bootstrap
The `.claude/memory/` system is already in place. Verify that `node .claude/memory/memory.js recent` runs without error.

---

## Exit gate (ALL must pass before you stop)
- [ ] Monorepo + layered folders exist with `__init__.py`
- [ ] `Agent` protocol defined + empty registry loads without error
- [ ] `Tool` base + `Permission` enum defined + tool registry loads
- [ ] `AgentState` typed schema defined and importable
- [ ] Empty LangGraph compiles and runs a no-op end-to-end
- [ ] `telemetry.py` skeleton works (structured logging)
- [ ] `pytest` green (all tests pass)
- [ ] CI workflow file exists at `.github/workflows/ci.yml`
- [ ] Memory system bootstrapped (`node .claude/memory/memory.js recent` runs)

## Verification
After building, run the full **Verification Protocol** from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` — all tests green
2. `@architect` + `/code-review high` — no layer violations, no bugs
3. `@security-auditor` + `/security-review` — no injection, no secrets, no SSRF
4. `@gate-checker Verify Phase 0 exit gate` — all criteria pass with evidence

## Rules (from CLAUDE.md — non-negotiable)
- Layer rule: a layer may only call the layer directly below it.
- One class = one agent. No god objects.
- No if-elif dispatch. Use the registry.
- Bounded critic loop: `max_revisions = 3`, then escalate.
- Permission-gated tools.
- Typed state only — nodes pass nothing outside `AgentState`.
- Do NOT build anything from Phase 1+. Stubs and empty `__init__.py` only for future layers.
