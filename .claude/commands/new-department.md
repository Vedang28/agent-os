Create a new department named $ARGUMENTS following the Engineering pattern.

1. Read its agents and purposes in docs/AGENT_ROSTER.md.
2. Create ~4 agent class files: a lead + proposer + worker + critic, each one class, single responsibility.
3. Build a LangGraph sub-graph with the bounded conditional critic edge (approve → end / revise → worker, max_revisions = 3).
4. Add ONE registry line. No if-elif.
5. Add one eval test that runs in CI.
6. Run /log to record what you built.
