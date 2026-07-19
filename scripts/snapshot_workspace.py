#!/usr/bin/env python3
"""Emit a bounded, fail-closed, read-only workspace snapshot for a handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_MAX_CONTENT_BYTES = 256 * 1024 * 1024


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


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def failure(message: str, *, probe: str | None = None, result: subprocess.CompletedProcess[bytes] | None = None) -> int:
    payload: dict[str, Any] = {"ok": False, "error": message}
    if probe:
        payload["probe"] = probe
    if result is not None:
        payload["returncode"] = result.returncode
        payload["stderr"] = decoded(result.stderr)[:1000]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2


def parse_status(status: bytes) -> tuple[list[tuple[str, bytes]], dict[str, int], bool]:
    entries: list[tuple[str, bytes]] = []
    counts = {"staged": 0, "modified": 0, "untracked": 0, "deleted": 0}
    conflicted = False
    tokens = status.split(b"\0")
    index = 0
    conflict_pairs = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4:
            continue
        code = token[:2].decode("ascii", errors="replace")
        path = token[3:]
        entries.append((code, path))
        if code == "??":
            counts["untracked"] += 1
        else:
            if code[0] not in (" ", "?"):
                counts["staged"] += 1
            if code[1] not in (" ", "?"):
                counts["modified"] += 1
            if "D" in code:
                counts["deleted"] += 1
            if "U" in code or code in conflict_pairs:
                conflicted = True
        if "R" in code or "C" in code:
            index += 1  # The following NUL field is the original path.
    return entries, counts, conflicted


def dirty_content_manifest(
    repo_root: Path,
    entries: list[tuple[str, bytes]],
    max_bytes: int,
) -> tuple[str, bool, int, int]:
    digest = hashlib.sha256()
    total_bytes = 0
    hashed_paths = 0
    complete = True
    for code, raw_path in sorted(entries, key=lambda item: (item[1], item[0])):
        digest.update(code.encode("ascii", errors="replace") + b"\0" + raw_path + b"\0")
        path = repo_root / os.fsdecode(raw_path)
        try:
            info = path.lstat()
        except OSError as exc:
            digest.update(f"missing:{exc.errno}".encode("ascii", errors="replace") + b"\0")
            continue
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            raw_target = os.fsencode(target)
            digest.update(b"symlink\0" + raw_target + b"\0")
            total_bytes += len(raw_target)
            hashed_paths += 1
            continue
        if not stat.S_ISREG(info.st_mode):
            digest.update(
                f"special:{info.st_mode}:{info.st_size}:{info.st_mtime_ns}".encode("ascii") + b"\0"
            )
            complete = False
            continue
        if total_bytes + info.st_size > max_bytes:
            digest.update(
                f"bounded:{info.st_size}:{info.st_mtime_ns}:{info.st_ino}".encode("ascii") + b"\0"
            )
            complete = False
            continue
        try:
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                    total_bytes += len(chunk)
            digest.update(b"\0")
            hashed_paths += 1
        except OSError as exc:
            digest.update(f"unreadable:{exc.errno}".encode("ascii", errors="replace") + b"\0")
            complete = False
    return digest.hexdigest(), complete, total_bytes, hashed_paths


def operation_state(git_dir: Path, common_dir: Path) -> tuple[list[str], list[str]]:
    operations: list[str] = []
    checks = (
        ("merge", git_dir / "MERGE_HEAD"),
        ("rebase", git_dir / "rebase-merge"),
        ("rebase", git_dir / "rebase-apply"),
        ("cherry-pick", git_dir / "CHERRY_PICK_HEAD"),
        ("revert", git_dir / "REVERT_HEAD"),
        ("bisect", git_dir / "BISECT_LOG"),
        ("sequencer", git_dir / "sequencer"),
    )
    for name, path in checks:
        if path.exists() and name not in operations:
            operations.append(name)
    locks: list[str] = []
    for path in (
        git_dir / "index.lock",
        git_dir / "HEAD.lock",
        common_dir / "packed-refs.lock",
        common_dir / "config.lock",
    ):
        if path.exists():
            locks.append(str(path))
    return operations, locks


def check_expectations(payload: dict[str, Any], locator: str | None, snapshot: str | None) -> int:
    mismatches: dict[str, dict[str, str | None]] = {}
    if locator and locator != payload.get("workspace_locator_id"):
        mismatches["workspace_locator_id"] = {
            "expected": locator,
            "actual": payload.get("workspace_locator_id"),
        }
    if snapshot and snapshot != payload.get("snapshot_id"):
        mismatches["snapshot_id"] = {
            "expected": snapshot,
            "actual": payload.get("snapshot_id"),
        }
    if mismatches:
        payload["ok"] = False
        payload["error"] = "workspace preflight mismatch"
        payload["mismatches"] = mismatches
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a deterministic identity and content snapshot for context-handoff."
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory to inspect")
    parser.add_argument(
        "--max-content-bytes",
        type=int,
        default=DEFAULT_MAX_CONTENT_BYTES,
        help="Maximum dirty file bytes to hash exactly (default: 256 MiB)",
    )
    parser.add_argument("--expect-locator-id")
    parser.add_argument("--expect-snapshot-id")
    args = parser.parse_args()
    if args.max_content_bytes < 0:
        return failure("--max-content-bytes must be non-negative")

    requested = Path(args.cwd).expanduser()
    try:
        cwd = requested.resolve(strict=True)
    except OSError as exc:
        return failure(f"cwd cannot be resolved: {exc}")
    if not cwd.is_dir():
        return failure(f"cwd is not a directory: {cwd}")

    top = git(cwd, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        stderr = decoded(top.stderr).lower()
        if top.returncode != 128 or "not a git repository" not in stderr:
            return failure("cannot determine whether cwd is a Git workspace", probe="repo_root", result=top)
        info = cwd.stat()
        locator_basis = {
            "kind": "directory",
            "resolved_cwd": str(cwd),
            "device": info.st_dev,
            "inode": info.st_ino,
        }
        locator_id = sha256_json(locator_basis)
        payload = {
            "ok": True,
            "cwd": str(cwd),
            "requested_cwd": str(requested),
            "resolved_cwd": str(cwd),
            "git": None,
            "workspace_id": locator_id,
            "workspace_locator_id": locator_id,
            "snapshot_id": sha256_json({**locator_basis, "mtime_ns": info.st_mtime_ns}),
        }
        return check_expectations(payload, args.expect_locator_id, args.expect_snapshot_id)

    try:
        repo_root = Path(decoded(top.stdout)).resolve(strict=True)
    except OSError as exc:
        return failure(f"repository root cannot be resolved: {exc}")

    probes = {
        "branch": git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD"),
        "head": git(cwd, "rev-parse", "--verify", "HEAD"),
        "git_dir": git(cwd, "rev-parse", "--path-format=absolute", "--git-dir"),
        "git_common_dir": git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"),
        "status": git(cwd, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        "index": git(cwd, "ls-files", "--stage", "-z"),
    }
    for name in ("git_dir", "git_common_dir", "status", "index"):
        result = probes[name]
        if result.returncode != 0:
            return failure(f"critical Git probe failed: {name}", probe=name, result=result)

    branch_result = probes["branch"]
    head_result = probes["head"]
    branch = decoded(branch_result.stdout) if branch_result.returncode == 0 else None
    head = decoded(head_result.stdout) if head_result.returncode == 0 else None
    if branch_result.returncode not in (0, 1):
        return failure("cannot determine branch/detached state", probe="branch", result=branch_result)
    if head is None and branch is None:
        return failure("workspace has neither a readable branch nor HEAD", probe="head", result=head_result)

    try:
        git_dir = Path(decoded(probes["git_dir"].stdout)).resolve(strict=True)
        common_dir = Path(decoded(probes["git_common_dir"].stdout)).resolve(strict=True)
    except OSError as exc:
        return failure(f"Git directory identity cannot be resolved: {exc}")

    status = probes["status"].stdout
    entries, counts, conflicted = parse_status(status)
    content_sha, content_complete, content_bytes, hashed_paths = dirty_content_manifest(
        repo_root, entries, args.max_content_bytes
    )
    operations, locks = operation_state(git_dir, common_dir)

    upstream = None
    ahead = None
    behind = None
    if branch:
        upstream_result = git(
            cwd,
            "for-each-ref",
            "--format=%(upstream:short)",
            f"refs/heads/{branch}",
        )
        if upstream_result.returncode == 0:
            upstream = decoded(upstream_result.stdout) or None
        if upstream:
            divergence = git(cwd, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
            if divergence.returncode == 0:
                parts = decoded(divergence.stdout).split()
                if len(parts) == 2:
                    behind, ahead = (int(parts[0]), int(parts[1]))

    locator_basis = {
        "resolved_cwd": str(cwd),
        "repo_root": str(repo_root),
        "git_dir": str(git_dir),
        "git_common_dir": str(common_dir),
    }
    locator_id = sha256_json(locator_basis)
    status_sha = hashlib.sha256(status).hexdigest()
    index_sha = hashlib.sha256(probes["index"].stdout).hexdigest()
    snapshot_basis = {
        "workspace_locator_id": locator_id,
        "branch": branch,
        "head": head,
        "status_sha256": status_sha,
        "index_sha256": index_sha,
        "content_sha256": content_sha,
        "content_hash_complete": content_complete,
        "operations": operations,
        "locks": locks,
    }
    payload = {
        "ok": True,
        "cwd": str(cwd),
        "requested_cwd": str(requested),
        "resolved_cwd": str(cwd),
        "git": {
            "repo_root": str(repo_root),
            "git_dir": str(git_dir),
            "git_common_dir": str(common_dir),
            "worktree_type": "main" if git_dir == common_dir else "linked",
            "branch": branch,
            "branch_ref": f"refs/heads/{branch}" if branch else None,
            "detached": branch is None,
            "head": head,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "status_known": True,
            "dirty": bool(status),
            "conflicted": conflicted,
            "status_counts": counts,
            "status_bytes": len(status),
            "status_sha256": status_sha,
            "index_sha256": index_sha,
            "content_sha256": content_sha,
            "content_hash_complete": content_complete,
            "content_bytes_hashed": content_bytes,
            "content_paths_hashed": hashed_paths,
            "operations_in_progress": operations,
            "locks": locks,
        },
        "workspace_id": locator_id,
        "workspace_locator_id": locator_id,
        "snapshot_id": sha256_json(snapshot_basis),
    }
    return check_expectations(payload, args.expect_locator_id, args.expect_snapshot_id)


if __name__ == "__main__":
    raise SystemExit(main())
