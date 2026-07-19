---
name: context-handoff-goal
description: "Hand the minimum useful state of a Codex conversation, research result, or task to a fresh thread bound to the exact project, branch, or worktree, then start one concrete Goal there after ownership and workspace verification. Use when the user explicitly invokes $context-handoff-goal or explicitly asks to hand off and immediately execute a well-defined objective. Use $context-handoff when the target should wait. Do not execute merely because the skill name appears in documentation, quotation, or discussion."
---

# Context Handoff Goal

Run the shared context-handoff workflow with `mode: goal`. This is a separate discoverable skill; it is not a parameter added after `$context-handoff`.

## Workflow

1. Read the core skill completely from the first existing path: `../context-handoff/SKILL.md` for a sibling installation, then `../SKILL.md` for the public repository layout.
2. Build the same five-point state: current work, completed evidence, blockers, next action, and pitfalls. Add exact conversation and workspace identity.
3. Require a concrete objective and observable acceptance condition. Ask one concise question only when a missing fact materially changes direction, risk, cost, or acceptance.
4. Follow the core skill's exact target routing and registered-directory gate. Never treat a command-level `workdir` override as proof that the new task is bound to the expected worktree.
5. Inspect the source Goal before creating another one. If it is active and the runtime has no verified pause, cancel, or transfer capability, create no second native Goal. The target may preflight and wait as `awaiting_source_goal_release`; the user must release the old Goal before execution begins.
6. After the source Goal is inactive or truly transferred, create one native Goal in the verified target and confirm its active state.
7. Return the source ID -> target ID receipt. The source then performs zero business work: no monitoring, testing, review, edits, commits, pushes, Goal completion, or final verification.

If automatic target creation or exact binding is unavailable, return a paste-ready `mode: goal` package for a manually opened task at the exact path. Do not report a native Goal until the target actually creates and verifies it.

## Safety

- Default to context transfer only; handoff does not authorize push, cherry-pick, file copying, commit, stash, checkout, or worktree creation.
- Do not execute on detached HEAD, conflicts, an in-progress Git operation, an unknown or changed dirty snapshot, or a target with another active writer.
- Never complete the source Goal merely because it was delegated, and never run source and target Goals concurrently.
