#!/usr/bin/env python3
"""Resolve an exact existing Git worktree without mutating repository state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(cwd), *args]
    try:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        return subprocess.run(
            command, capture_output=True, check=False, timeout=10, env=environment
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=b"",
            stderr=str(exc).encode("utf-8", errors="replace"),
        )


def decoded(value: bytes) -> str:
    return value.decode("utf-8", errors="replace").strip()


def emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def parse_worktrees(raw: bytes) -> list[dict[str, Any]]:
    worktrees: list[dict[str, Any]] = []
    for raw_record in raw.split(b"\0\0"):
        if not raw_record:
            continue
        record: dict[str, Any] = {"locked": False, "prunable": False, "detached": False}
        for raw_field in raw_record.split(b"\0"):
            if not raw_field:
                continue
            key, _, value = raw_field.partition(b" ")
            name = key.decode("ascii", errors="replace")
            text = os.fsdecode(value)
            if name == "worktree":
                record["path"] = text
            elif name == "HEAD":
                record["head"] = text
            elif name == "branch":
                record["branch_ref"] = text
                record["branch"] = text.removeprefix("refs/heads/")
            elif name in ("locked", "prunable"):
                record[name] = True
                if text:
                    record[f"{name}_reason"] = text
            elif name in ("detached", "bare"):
                record[name] = True
        if record.get("path"):
            try:
                record["resolved_path"] = str(Path(record["path"]).resolve(strict=True))
            except OSError:
                record["resolved_path"] = None
                record["prunable"] = True
            worktrees.append(record)
    return worktrees


def normalize_branch(branch: str | None) -> str | None:
    if branch is None:
        return None
    if branch.startswith("refs/remotes/") or branch.startswith("remotes/"):
        raise ValueError("remote-tracking refs are not local execution branches")
    if branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/") :]
    if not branch or branch.startswith("-"):
        raise ValueError("branch must be an exact local branch name")
    return branch


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a path/branch selector to exactly one existing Git worktree."
    )
    parser.add_argument("--repo", required=True, help="Exact repository or worktree path")
    parser.add_argument("--branch", help="Exact local branch name")
    parser.add_argument("--worktree", help="Exact existing worktree path")
    args = parser.parse_args()

    try:
        repo = Path(args.repo).expanduser().resolve(strict=True)
    except OSError as exc:
        return emit({"ok": False, "resolution": "unavailable", "error": f"repo cannot be resolved: {exc}"}, 2)
    if not repo.is_dir():
        return emit({"ok": False, "resolution": "unavailable", "error": "repo is not a directory"}, 2)
    try:
        branch = normalize_branch(args.branch)
    except ValueError as exc:
        return emit({"ok": False, "resolution": "unavailable", "error": str(exc)}, 2)

    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    listing = git(repo, "worktree", "list", "--porcelain", "-z")
    if common.returncode != 0 or listing.returncode != 0:
        failed = common if common.returncode != 0 else listing
        return emit({
            "ok": False,
            "resolution": "unavailable",
            "error": "cannot inspect repository worktrees",
            "stderr": decoded(failed.stderr)[:1000],
        }, 2)
    common_dir = str(Path(decoded(common.stdout)).resolve(strict=False))
    worktrees = parse_worktrees(listing.stdout)

    requested_worktree = None
    if args.worktree:
        try:
            requested_worktree = str(Path(args.worktree).expanduser().resolve(strict=True))
        except OSError as exc:
            return emit({"ok": False, "resolution": "unavailable", "error": f"worktree cannot be resolved: {exc}"}, 2)

    candidates = worktrees
    if requested_worktree:
        candidates = [item for item in candidates if item.get("resolved_path") == requested_worktree]
    elif branch is None:
        repo_path = str(repo)
        candidates = [item for item in candidates if item.get("resolved_path") == repo_path]
    if branch:
        candidates = [item for item in candidates if item.get("branch") == branch]

    selector = {"repo": str(repo), "branch": branch, "worktree": requested_worktree}
    if len(candidates) != 1:
        local_exists = None
        if branch:
            exists = git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
            local_exists = exists.returncode == 0
        return emit({
            "ok": False,
            "resolution": "ambiguous" if len(candidates) > 1 else "unavailable",
            "selector": selector,
            "local_branch_exists": local_exists,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "all_worktrees": worktrees,
            "error": "selector did not resolve to exactly one existing worktree",
        }, 3)

    target = candidates[0]
    if target.get("locked") or target.get("prunable") or not target.get("resolved_path"):
        return emit({
            "ok": False,
            "resolution": "unavailable",
            "selector": selector,
            "target": target,
            "error": "resolved worktree is locked, prunable, or unavailable",
        }, 4)
    if branch and target.get("branch") != branch:
        return emit({
            "ok": False,
            "resolution": "unavailable",
            "selector": selector,
            "target": target,
            "error": "requested path and live branch disagree",
        }, 4)

    return emit({
        "ok": True,
        "resolution": "exact",
        "selector": selector,
        "git_common_dir": common_dir,
        "target": target,
        "evidence": [
            "exact repository identity",
            "git worktree list exact match",
            "exact local branch" if branch else "exact worktree path",
        ],
    }, 0)


if __name__ == "__main__":
    raise SystemExit(main())
