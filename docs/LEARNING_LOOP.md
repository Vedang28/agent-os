# LEARNING LOOP

> How the system gets better over time — at two levels: the dev workflow (Claude Code sessions) and the runtime agents.

## Level 1 — Dev session learning (you + Claude Code)
1. **Every session ends with `/log`** — a 2-3 line summary to `.claude/memory/SESSION_LOG.md`.
2. **Every architectural choice gets recorded** — `/reflect` or `node .claude/memory/memory.js decide "<title>" "<why>"` to `.claude/memory/DECISIONS.md`, so it is never re-litigated.
3. **Every session starts with `/start-phase`** — loads recent logs so Claude Code has continuity instead of starting cold.
4. **Repeated failures** surface via `node .claude/memory/memory.js search "<error>"` — if the same blocker appears twice, fix the root cause, don't patch it again.

## Level 2 — Runtime agent learning (the Reflector)
The Reflector runs on the daemon tick and:
1. Reads recent **outcomes** every department wrote to the brain (what worked, what the critic rejected, what the user accepted).
2. Finds patterns ("question-style subject lines got 2x replies"; "the Scaffolder keeps producing N+1 queries").
3. Writes **improved playbooks** back to the brain.
4. Next run, every Proposer reads the improved playbook via read-before-act.

The system improves by improving its **notes**, not by retraining a model.

## What counts as an outcome (log these)
- task succeeded / failed
- critic verdict (approved, and how many revisions it took)
- user accepted / rejected / corrected
- tool errors and how they were resolved
- wall-clock + token cost vs budget

## Cadence
- Session log: every dev session.
- Reflector: every daemon tick with ≥5 new outcomes (runtime).
- Decision record: whenever a choice would be expensive to reverse.
