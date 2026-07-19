---
name: context-handoff
description: "Hand the minimum useful state of a Codex conversation, research result, or task to a fresh thread that waits for the user, while preserving one execution owner and the exact project, branch, or worktree identity. Use when the user explicitly invokes $context-handoff, asks to hand off or continue in a new conversation, changes project/task phase, reports a long/slow/reconnecting conversation, or explicitly accepts a visible handoff recommendation. Use $context-handoff-goal when the target should execute a concrete goal. Do not execute merely because the skill name appears in documentation, quotation, or a discussion about the skill."
---

# Context Handoff

Hand off the smallest complete task state to a fresh thread and make that thread the sole future owner. Do not copy the full transcript or turn the source into a coordinator.

`$context-handoff` always means: verify the destination, transfer context, then wait in the target. `$context-handoff-goal` is the separate execution mode.

## Core handoff state

Center the package on five questions:

1. What is being done now?
2. What is already complete, with evidence?
3. What is blocked or uncertain?
4. What should happen next?
5. What mistakes, rejected paths, or constraints must not be repeated?

Add only the identity needed to resume safely: source and target conversation IDs, exact workspace/worktree path, repository root, local branch, HEAD, dirty state, and one stable `handoff_id`. A conversation ID is a navigation reference, not a substitute for this state.

## Workflow

1. **Require real invocation.** Quoted commands, screenshots, README wording, or discussion about this skill are not requests to run it. A one-word approval is valid only when it immediately answers one visible, unambiguous handoff recommendation.
2. **Reach a safe stopping point.** Finish any in-flight write, migration, deployment, destructive command, or partially applied transaction before handing off.
3. **Inspect the source Goal.** Use `get_goal` when available. Record whether the source has an active native Goal. Never mark that Goal complete merely because work was delegated.
4. **Resolve the exact destination.** Prefer an explicit absolute path or exact local branch. Otherwise use the workspace that owns the task result, active Goal, or dirty work. Use recency only when the same task is merely moving to a fresh thread. If two candidates remain, ask one concise question. For directed Git routing, read [references/target-routing.md](references/target-routing.md).
5. **Snapshot without mutation.** Run the bundled resolver and snapshot tools as needed. Never switch, create, clean, stash, commit, reset, or move work merely to make the handoff fit.
6. **Apply the thread-binding gate.** List available Codex projects before creating a target. Automatic creation is allowed only when the target thread can be registered to the exact expected directory or to an explicitly authorized new worktree. An existing linked worktree that is not itself a registered project is not automatically bindable. In that case, return a paste-ready prompt for a manually opened task at that exact path; do not create the target in the parent project checkout.
7. **Create a fresh target, never a history fork.** Forking carries old history and defeats context relief. If exact fresh-thread binding is unavailable, use the manual fallback and report the handoff as incomplete.
8. **Verify the registered target directory.** Inspect target thread metadata and require its registered `cwd` to equal the expected resolved path. The target's first workspace probe must run from its native task directory without a `workdir` override, then compare the live snapshot with the package. A command that merely sets `workdir` to the expected path does not prove the thread is bound there.
9. **Handle an active source Goal safely.** If the source Goal is active, use a real pause, cancel, or transfer tool only when the runtime actually provides one. If none exists, do not claim the old task stopped and do not start a second native Goal. The target may verify receipt but must wait in `awaiting_source_goal_release` until the user releases the old Goal through the product UI.
10. **Transfer ownership once.** After target receipt and preflight, return only the source ID -> target ID receipt. The source must not monitor the target, rerun tests, review, edit, commit, push, close the delegated Goal, or announce business completion. If the source is automatically awakened later, it performs no task work and only points to the target receipt.

If thread creation, inspection, exact binding, or Goal release cannot be verified, provide the complete paste-ready package and state precisely which step remains manual. Never call that a completed automatic handoff.

## Compact package

```yaml
schema_version: 3
handoff_id: ctx-<stable-id>
mode: wait
source:
  conversation_id: <source ID or null>
  goal_state: none | inactive | active | unavailable
target:
  conversation_id: <target ID or null>
  binding: verified | awaiting_source_goal_release | manual_required | unavailable
workspace:
  cwd: <exact resolved path or null>
  repo_root: <absolute path or null>
  branch: <exact local branch or null>
  head: <full commit or null>
  dirty: <true | false | null>
doing: <what is being done now>
completed:
  - <verified result and evidence>
blocked:
  - <blocker or uncertainty>
next:
  - <next useful action>
pitfalls:
  - <constraint, rejected path, or mistake not to repeat>
```

Include only facts that change the target's decisions. Mark uncertainty explicitly. Never include secrets, cookies, tokens, `.env` contents, hidden reasoning, or a full dirty diff.

Keep ordinary handoffs inline. Create a durable Hand-off Markdown file only when the task is complex, the state must survive outside Codex, or the user explicitly asks for one.

## Target behavior

- In `wait` mode, acknowledge the five-point state and wait. Do not implement, create a Goal, or continue analysis beyond the minimum receipt.
- If the package says `awaiting_source_goal_release`, never begin task work until the user explicitly confirms the old Goal was stopped or the runtime verifies a real transfer.
- Stop on registered-directory, repository, worktree, branch, HEAD, dirty-snapshot, conflict, Git-operation, lock, or active-writer mismatch.
- Preserve the same `handoff_id` on retries so duplicate targets can be detected.

## Reminder behavior

The optional hook may recommend a handoff from transcript size buckets or a reported reconnect signal. Keep it lightweight: no daemon, polling, network request, model call, transcript-content scan, or global log scan. A reminder is advisory and never starts a handoff by itself.

## Non-goals

- Do not use this skill merely to find an old session ID, synchronize across devices, transfer files/commits, or write a colleague-facing document.
- Do not claim to transfer browser login state, running processes, ports, hidden reasoning, or unpersisted tool state.
- Do not call a prompt-only fallback, command-level directory override, or unverified target a completed handoff.
