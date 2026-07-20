# Target routing

Read this reference only for a directed handoff to a project, branch, or worktree.

## Exact evidence order

1. Exact absolute worktree path supplied by the user.
2. Exact project path plus exact local branch.
3. Registered project identity plus canonical repository root and exact local branch.
4. Canonical repository identity plus exact branch when it resolves to one existing worktree.

A nickname, recency, similarly named directory, bare `main`, remote-tracking ref, or last inspected checkout is not exact evidence.

When a project-only selector produces multiple candidates, present the exact branch/task-line candidates neutrally and ask which one owns the next action. Do not recommend the main checkout merely because it is the canonical project path.

## Branch and worktree rules

- If an exact local branch is checked out in one existing worktree, use that worktree.
- If the supplied path is a worktree and its current branch differs from the requested branch, stop. Never checkout to make it fit.
- If the branch exists locally but has no worktree, ask before creating an isolated worktree.
- If a branch is already occupied, reuse that exact worktree after preflight; do not switch the main checkout.
- Treat `main`, `origin/main`, and another remote's `main` as different refs. A remote-only branch is not a local execution target.
- Do not execute in locked, prunable, conflicted, or Git-operation-in-progress worktrees.
- `wait` may open an exact dirty target, disclose it, and wait. `goal` requires known provenance, a stable content snapshot, compatible scope, and no competing writer.

## Source, target, and transfer

Source and target are independent:

- An external repository or website can be the evidence source while a product worktree is the execution target.
- Carry the external URL, version/commit, license, and clean-room or attribution constraints when relevant.
- Default transfer is `context_only`. Uncommitted files do not move between worktrees or repositories just because the conversation moved.
- Treat Git push, cherry-pick, merge, file copy, and branch/worktree creation as separate operations requiring explicit scope and normal project safety checks.

## Preflight order

Before creating the target, snapshot its locator and content state. In the target, verify the exact real path, repository root, Git directory/common directory, local branch, HEAD, dirty manifest, operation/lock state, and worktree occupancy before reading project instructions or starting a Goal. A mismatch keeps the handoff incomplete.

## Codex task-binding capability gate

Resolve workspace identity separately from task-creation capability:

- An exact existing worktree is a valid destination only when the new Codex task can register that exact path as its native `cwd`.
- Match the resolved path against the paths returned by the available project-listing tool. A parent repository project is not an exact match for its linked worktree.
- Do not hide a binding mismatch by running the target's commands with an explicit `workdir`. The first target probe must run from the task's native directory, and thread metadata must report the same path.
- If the runtime can only create a task at the parent checkout, stop automatic creation and return a paste-ready prompt for a manually opened task at the exact worktree.
- Creating a new worktree is a separate operation and requires explicit user authorization. It is not a fallback for reusing an existing worktree.
