---
name: filetool-if-elif-dispatch
description: FileTool.execute uses if-elif dispatch on operation string, violating the no if-elif dispatch rule — flagged in Phase 1 review
metadata:
  type: project
---

`tools/file.py:22-38` uses an if-elif chain to dispatch on the `operation` parameter ("read", "write", "list_dir", "exists"). This violates CLAUDE.md rule 3: "No if-elif dispatch. Use the registry."

**Why:** The if-elif dispatch anti-pattern is specifically called out because it creates a closed routing pattern. Adding a new file operation requires modifying the existing method.

**How to apply:** When this comes up in review, flag it. The fix would be either (a) splitting FileTool into ReadFileTool, WriteFileTool, etc., each registered separately, or (b) using an internal operation registry/dispatch dict within the tool. Option (a) is cleaner given single-responsibility. Related: [[layer-violation-telemetry-crosscut]].
