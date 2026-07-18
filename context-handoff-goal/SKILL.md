---
name: context-handoff-goal
description: "Safely hand a long, slow, or reconnecting Codex conversation to a fresh thread and create/start a concrete goal after verifying the real workspace and Git branch. Use when the user invokes $context-handoff-goal or explicitly asks to hand off and immediately execute a well-defined objective. This is the directly discoverable goal-mode companion to $context-handoff. Do not use when requirements still need discussion."
---

# Context Handoff Goal

Run the shared context-handoff workflow in `direct_goal` mode. This companion has a separate skill name because Codex skill selectors list `$skill-name`; text after a space is prompt content, not another skill entry.

## Workflow

1. Read the core skill completely from the first existing relative path: `../context-handoff/SKILL.md` for sibling installation, then `../SKILL.md` for a nested public-repository installation. Follow its workspace snapshot, conversation-ID, fresh-thread, preflight, verification, and safety requirements.
2. Set `mode: direct_goal`. Never reinterpret this explicit skill as `continue`.
3. Confirm the objective and acceptance criteria are concrete enough to execute. If one missing fact would materially change the work, ask one concise question before creating the target.
4. Create a fresh target thread in the verified latest real directory and current branch. Do not fork the source history or create a branch/worktree unless explicitly requested.
5. After the target independently passes preflight, create/start the goal there. Return the source ID -> target ID receipt only after target verification succeeds.

If the runtime cannot create or inspect threads, return a paste-ready `direct_goal` handoff prompt and clearly state that automatic handoff and goal creation did not complete.

## Safety

- Never guess conversation IDs, directories, branches, or repository state.
- Never stash, commit, reset, clean, checkout, archive, or delete work merely to hand off.
- Never start the goal before the target workspace preflight passes.
