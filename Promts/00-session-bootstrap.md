# Session Bootstrap Prompt

Use this as your first message in every new AI session.

---

Please read guide.md, changelog.md, and plan.md first, then continue from the current state.

Do not scaffold from scratch.
Do not recreate files that already exist.

After reading, return the following before making changes:

1. Current implementation status (what is complete and what is pending).
2. Gaps against plan.md by phase.
3. Exact next 3 actions you will execute.
4. Files you plan to edit.

Execution rules for this session:

1. Implement directly in existing codebase.
2. After each major change, update changelog.md.
3. If setup or architecture changes, update guide.md.
4. If blocked, explain blocker and provide the smallest viable workaround.

Current task:

next task which is pending on implementation.

Before ending this session, add a handoff note to changelog.md with:

1. What changed.
2. What is pending.
3. Any blockers.
4. Exact next command to run.
