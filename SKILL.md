---
name: context-handoff
description: "Safely hand a Codex conversation, research result, or task state to a fresh thread that waits for the user. Preserve source and target conversation IDs, resolve either the current workspace or a user-directed project, branch, or existing worktree, and verify the target before completing the handoff. Use when the user invokes $context-handoff, asks to move analysis or decisions into a new conversation, changes project or task phase, reports a long/slow/reconnecting conversation, or accepts a visible handoff recommendation. Use $context-handoff-goal when the target should immediately execute a concrete goal."
---

# Context Handoff

Transfer task ownership and decision state to a fresh thread without copying the bloated transcript. Keep three decisions independent:

- `why`: why the handoff is useful, such as context pressure, a task or workspace transition, recovery, or an explicit request.
- `where`: the exact target workspace, an explicitly requested project/branch/worktree, or `conversation_only` when no project is involved.
- `after`: `$context-handoff` always means `wait`; `$context-handoff-goal` always means `goal` through the companion skill.

Never choose a target merely because it was the most recently inspected directory. A read-only reference repository, external open-source checkout, temporary evidence directory, or comparison worktree is a source of evidence unless it is also the verified execution target.

## Resolve the target

1. Finish the nearest safe unit. Do not interrupt an in-flight write, deployment, migration, destructive command, or partially applied transaction.
2. Determine `after` from the explicit skill name. If surrounding words directly conflict with the selected mode, ask one concise question instead of silently changing modes.
3. Resolve `where` in this order:
   1. Exact worktree or absolute path explicitly named by the user.
   2. Exact project path plus exact local branch.
   3. A project and branch that uniquely map to one existing worktree.
   4. The workspace that owns the current goal, uncommitted work, or task result.
   5. The source's last verified workspace only when this is the same task moving to a fresh thread.
   6. `conversation_only` for discussion with no real project.
4. If two candidates remain equally plausible, list their exact branch/task-line names neutrally and ask exactly one question. Never use recency, the main checkout, a nickname, or a bare `main` as a suggested default.
5. For a directed Git handoff, read [references/target-routing.md](references/target-routing.md), then use the bundled read-only tools:

   ```bash
   python3 scripts/resolve_target_worktree.py --repo <exact-repo-or-worktree> --branch <exact-local-branch>
   python3 scripts/snapshot_workspace.py --cwd <resolved-target>
   ```

   Run bundled scripts from the active skill directory. They resolve and inspect only; they never create, switch, clean, or remove worktrees.

## Build and transfer the package

1. Record the exact source conversation/thread/session ID from available metadata or thread tools. Use `null` if unavailable; never guess.
2. Snapshot source and target separately. Generate one stable `handoff_id` and a new `attempt_id` for each retry.
3. Default `transfer.mode` to `context_only`. A handoff does not itself push, cherry-pick, copy files, commit, stash, or move dirty work. Record source commits/files as evidence only. Any later code transfer requires explicit scope and the target project's normal Git safety rules.
4. Summarize only facts that change the target's decisions: objective, verified state, decisions and reasons, rejected options worth preserving, remaining work, constraints, acceptance, provenance, and first action. Never include secrets, cookies, tokens, `.env` contents, hidden reasoning, or a full dirty diff.
5. Enter a best-effort source `handoff-freeze` at the safe stopping point before transferring write ownership. This is a coordination state, not a platform lock. If target creation or verification fails, report failure and allow the source to resume.
6. Create a fresh target thread using available Codex thread/project tools. Do not fork the long source history. Do not create or switch a branch/worktree unless the user explicitly authorizes isolation.
7. The first target action must independently re-run the snapshot and compare `workspace_locator_id` and `snapshot_id`. Also check detached state, conflicts, Git operations/locks, and any known active writer. Stop on mismatch and report expected versus actual.
8. In `wait` mode, acknowledge the received state and wait. Do not begin implementation.
9. Verify that the target received the same `handoff_id`, passed preflight, and returned a real target conversation/thread ID. Return a source ID -> target ID receipt, then leave the source soft-frozen. Never archive or delete it automatically.

If the runtime cannot create or inspect threads, produce a paste-ready target prompt with the complete package and exact preflight. Say automatic creation was unavailable; do not claim completion.

## Compact package

```yaml
schema_version: 2
handoff_id: ctx-<stable-id>
attempt_id: attempt-<unique-id>
why:
  kind: context_pressure | task_transition | workspace_transition | recovery | explicit_request
  summary: <one sentence>
source:
  conversation_id: <source ID or null>
  workspace: <source snapshot or null>
  evidence_refs: []
where:
  selector: <same_workspace | exact_path | project_branch | existing_worktree | conversation_only>
  requested: <user wording or null>
  resolution: exact | ambiguous | unavailable
  evidence: []
target:
  conversation_id: <target ID after creation or null>
  workspace: <independent target snapshot or null>
transfer:
  mode: context_only
after:
  mode: wait | goal
  objective: <one sentence>
  current_state: []
  decisions: []
  remaining: []
  constraints: []
  acceptance: []
  first_action: <first useful action after preflight>
```

## Stop conditions

Stop and ask one concise question, or report a blocked preflight, when:

- A project name, branch nickname, or `main` maps to multiple plausible repositories/worktrees.
- The requested path and live branch disagree, a branch is remote-only, or an existing worktree is locked/prunable.
- A new worktree would be required but the user did not authorize creating one.
- Goal mode targets detached HEAD, an in-progress Git operation, conflicts, a Git lock, an unknown or incomplete dirty-content snapshot, or another active writer.
- The target changes between resolution and target-side preflight.
- Files or commits must enter another repository but the transfer method was not explicitly defined.
- The same `handoff_id` already has an active target/goal and idempotency cannot be verified.

## Reminder behavior

The optional hook may recommend a handoff from transcript size buckets or a reported reconnect signal. Keep this separate from target routing and lightweight: no daemon, polling, network request, model call, full transcript scan, or global log scan. A reminder is advisory and a one-word approval applies only to the immediately preceding unambiguous recommendation.

## Non-goals

- Do not use this skill merely to find an old session ID, write a colleague-facing handoff document, or perform cross-device project synchronization.
- Do not claim to transfer browser login state, running processes, ports, hidden reasoning, or unpersisted tool state.
- Do not call a prompt-only fallback a completed handoff or a native Goal unless the target's Goal state can be activated and verified.
