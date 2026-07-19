---
name: context-handoff-goal
description: "Safely hand a Codex conversation, research result, or task state to a fresh thread in the current or user-directed project, branch, or existing worktree, then start a concrete goal after exact target verification. Use when the user invokes $context-handoff-goal or explicitly asks to move context and immediately execute a well-defined objective. Use $context-handoff when the new thread should wait for more discussion."
---

# Context Handoff Goal

Run the shared context-handoff workflow with `after.mode: goal`. This separate discoverable skill exists because Codex skill selectors list `$skill-name`; text after a space is prompt content, not a second skill entry.

## Workflow

1. Read the core skill completely from the first existing path: `../context-handoff/SKILL.md` for sibling installation, then `../SKILL.md` for a nested public-repository installation.
2. Keep `why`, `where`, and `after` independent. Both skills support the same source/target routing; this companion changes only `after.mode` from `wait` to `goal`.
3. Confirm the objective and observable acceptance criteria are concrete. Ask one concise question only when a missing fact would materially change direction, safety, cost, or acceptance.
4. Reach a safe stopping point and best-effort freeze the source before transferring write ownership.
5. Resolve an exact target and perform target-side preflight using the shared workflow. Never start execution in a guessed project, branch, or worktree.
6. Start a native Goal only when the target can activate and verify native Goal state. Otherwise return an explicit `goal_prompt_only_fallback`; never report it as a native Goal.
7. Return the source ID -> target ID receipt only after target verification succeeds. If creation or verification fails, do not leave the source falsely frozen.

## Safety

- Default to `transfer.mode: context_only`; handoff does not authorize Git push, cherry-pick, file copying, commit, stash, checkout, or worktree creation.
- Do not execute on detached HEAD, unresolved conflicts, an in-progress Git operation, an unknown/changed dirty snapshot, or a target with another active writer.
- Never guess conversation IDs, directories, branches, repositories, Goal state, or completion.
