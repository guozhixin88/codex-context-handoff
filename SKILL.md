---
name: context-handoff
description: "Safely hand a long, slow, or reconnecting Codex conversation to a fresh thread that waits for the user while preserving source and target conversation IDs, the actual workspace, Git branch, decisions, and next action. Use when the user invokes $context-handoff, asks to hand off a conversation and continue discussing, reports Reconnecting 5/5 or a very large transcript, or accepts a recommendation to continue in a fresh thread. Use $context-handoff-goal instead when the new thread should create/start a goal."
---

# Context Handoff

Move the useful state of the current conversation into a fresh thread without copying the bloated transcript. Keep the target in the source thread's latest real directory and current Git branch unless the user explicitly requests isolation.

## Select the mode

- `$context-handoff` -> `continue`: create a fresh thread, present the received state, and wait for the user.
- `$context-handoff-goal` -> `direct_goal`: use the separately discoverable companion skill to create a fresh thread, verify it, then create/start the goal.

The explicit command `$context-handoff` always means `continue`; never upgrade it to goal mode from surrounding context. Codex skill selectors list skill names, so `$context-handoff goal` is not a second menu item. A bare approval authorizes handoff only when it immediately follows one unambiguous visible handoff recommendation.

## Workflow

1. Finish the nearest safe unit. Do not interrupt an in-flight write, deployment, migration, destructive command, or partially applied transaction.
2. Resolve the latest real project/tool working directory used in this conversation. Run the bundled `scripts/snapshot_workspace.py --cwd <path>`; common installations place it under `${CODEX_HOME:-$HOME/.codex}/skills/context-handoff/` or `$HOME/.agents/skills/context-handoff/`.
3. Stop and ask one concise question if the directory/repository is ambiguous. Dirty work is allowed and must be disclosed; never clean, stash, commit, reset, or switch branches just to hand off.
4. Record the exact source conversation/thread/session ID from available session metadata or thread tools. Use `null` if unavailable; never guess it.
5. Build one compact package. Do not paste the transcript. Generate one `handoff_id` and reuse it on retries.
6. Create a fresh target thread with available Codex thread/project tools. Do not fork the source history. Do not create a new branch or worktree unless the user explicitly asks for isolation.
7. In the target, independently verify `cwd`, repository root, branch/detached state, and `HEAD`. Stop on mismatch and show expected versus actual values.
8. Activate the selected mode only after preflight passes.
9. Verify the target received the same `handoff_id`, record its returned conversation/thread ID, and return a receipt mapping source ID -> target ID. Only then soft-freeze the source. Never archive or delete it automatically.

If the harness cannot create or inspect threads, produce a paste-ready target prompt with the complete package and preflight. Say that automatic target creation was unavailable; do not claim completion.

## Handoff package

```yaml
handoff_id: ctx-<stable-id>
mode: continue | direct_goal
source:
  conversation_id: <source thread/session id or null>
  cwd: <resolved absolute path>
  repo_root: <absolute path or null>
  branch: <branch name or null>
  detached: <true|false>
  head: <full commit or null>
  dirty: <true|false>
target:
  conversation_id: <target thread/session id after creation or null>
objective: <one sentence>
current_state:
  - <verified fact or completed work>
decisions:
  - <decision and reason>
remaining:
  - <unresolved item or next task>
constraints:
  - <safety, scope, or business boundary>
acceptance:
  - <observable completion condition>
first_action: <target's first useful action after preflight>
```

Include only facts that change the target's decisions. Mark uncertainty. Mention relevant files, commits, and tests, but never include secrets, cookies, tokens, `.env` contents, or a full dirty diff.

## Reminder behavior

An optional UserPromptSubmit hook can recommend this skill at 50/100/200/500 MB transcript buckets or when the user reports the exact sampling reconnect failure. The hook must remain advisory and lightweight: no daemon, polling, network request, model call, full transcript scan, or global log scan.

- 50 MB: soft signal; remind only with slowness/reconnect context.
- 100 MB: strong recommendation.
- 200 MB: high priority at the next safe stopping point.
- 500 MB: critical; avoid adding nonessential work to the source.
- `stream disconnected - retrying sampling request (5/5)`: strong signal, not proof of root cause.

## Safety checks

- Match verified live directory/branch state, not a remembered project name.
- Never invent source or target conversation IDs.
- Never auto-stash, auto-commit, reset, clean, checkout, or delete work.
- Never archive the source before target verification.
- Never call a handoff complete when only a document or prompt was generated.
