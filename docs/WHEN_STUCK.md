# WHEN STUCK — error & escalation protocol

> Read this whenever something fails. The goal: fail loud, fail bounded, never fake success.

## The escalation ladder (do in order, stop as soon as it's resolved)
1. **Read the actual error.** Don't guess. Read the full message and the failing line.
2. **One targeted fix.** Make a single specific change aimed at the real cause. Re-run.
3. **Consult the docs.** Check `docs/EXECUTION_PLAN.md` (the active phase), `.claude/memory/DECISIONS.md` (why something is the way it is), and `CLAUDE.md` (the rules) before changing architecture.
4. **Search memory.** `node .claude/memory/memory.js search "<error>"` — have we hit this before?
5. **Log a blocker and STOP.** If still failing after step 2 has been retried once, write the blocker to `docs/PHASE_STATUS.md` (Notes/blockers) and ask the human. Do not keep flailing.

## Hard rules when stuck
- **Bounded retries.** Maximum 2 attempts at the same fix. A third identical attempt is forbidden — escalate instead.
- **Never fake success.** Do not mark an exit gate passed, a test green, or a task done unless it actually is. Run the real check.
- **Never swallow errors silently.** No bare `except: pass`, no empty catch. Log every failure with context.
- **Never delete or rewrite working code** to make a failing test pass. Fix the cause.
- **Never widen scope to escape a blocker.** If Phase 2 is stuck, do not "just start Phase 3". Stop and report.
- **Never invent an API.** If unsure a function or flag exists, check the docs or the source. Do not hallucinate it.
- **Respect the layer rule even under pressure.** A quick hack that calls across layers is still forbidden.

## When genuinely unsure (a judgment call, not an error)
State the options and the tradeoff, pick the one that matches `CLAUDE.md` principles, and record it with `/reflect` or a decision. Don't silently guess.

## Loop safety (runtime)
- The critic revise loop is capped at `max_revisions = 3`. After the cap, escalate to Guardian / human. Never loop forever.
- Every deep task has a token + wall-clock budget. Exceed it → stop and report partial progress.
