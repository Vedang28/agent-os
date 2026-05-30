# Phase 4 — Learning Loop + Guardian

> **Prerequisite:** Phase 3 exit gate must pass.
> **Parallel tracks.** Track A = Reflector. Track B = Guardian.

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
1. `@spine-builder Build Phase 4 Track A: Reflector agent — reviews outcomes, updates playbooks in /brain`
2. `@edge-builder Build Phase 4 Track B: Guardian — permission gates, human-in-the-loop interrupt, kill switch`
3. `@gate-checker Verify Phase 4 exit gate`

---

## Track A — Reflector (Learning)

### `/brain/reflector.py`
- Triggered after every daemon tick with ≥5 new outcomes
- **Reviews outcomes** in the brain:
  - Task success/failure rates
  - Critic verdicts (approval rate, avg revisions)
  - User corrections
  - Tool errors
  - Cost vs budget
- **Finds patterns**: repeated failures, successful strategies
- **Writes playbook notes** back to the brain via `obsidian.py`
  - Playbooks are notes tagged `#playbook`
  - Example: "When generating API code, always check for existing error handlers first"
- **Proposers read playbooks** via `librarian.query()` during read-before-act

### Outcome schema
```python
class Outcome(BaseModel):
    task_id: str
    department: str
    success: bool
    revisions: int
    critic_verdict: str
    user_feedback: str | None
    tool_errors: list[str]
    tokens_used: int
    wall_clock_seconds: float
```

---

## Track B — Guardian (Safety)

### `/agents/guardian.py`
- **Permission gate enforcement:**
  - Before any tool execution, check if the tool's `Permission` level is allowed
  - `READ` → always allowed
  - `WRITE` → allowed with logging
  - `SHELL` → requires approval (human-in-the-loop)
  - `DESTRUCTIVE` → requires explicit approval + confirmation

- **Human-in-the-loop interrupt:**
  - Uses LangGraph's `interrupt()` for pause/resume
  - When a destructive action is requested, the graph pauses
  - Human reviews and approves/rejects
  - Graph resumes from the interrupt point

- **Kill switch:**
  - `Guardian.kill()` → immediately stops all running graphs
  - Saves state before stopping (graceful)
  - Can be triggered by: cost ceiling breach, time ceiling breach, or manual trigger

### Integration
Wire Guardian into the tool execution path — every tool call flows through Guardian's permission check.

---

## Merge point
1. A low-scoring outcome produces an improved playbook on the next Reflector run
2. No destructive action executes without an approval step

---

## Exit gate (ALL must pass)
- [ ] Reflector reads outcomes from brain
- [ ] Reflector identifies patterns and writes playbook notes
- [ ] Proposers read playbooks via brain query (measurable: different behavior with/without playbook)
- [ ] **Measurable improvement** on a repeated task after reflection
- [ ] Guardian enforces permission levels on all tools
- [ ] `READ` tools execute without approval
- [ ] `SHELL` tools pause for approval
- [ ] `DESTRUCTIVE` tools pause for explicit approval + confirmation
- [ ] Human-in-the-loop interrupt works (pause → approve → resume)
- [ ] Kill switch stops all running graphs and saves state
- [ ] **No destructive action executes without an approval step**
- [ ] All `pytest` green
