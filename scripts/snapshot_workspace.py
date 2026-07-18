#!/usr/bin/env python3
"""Emit a bounded, read-only identity snapshot for a context handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(cwd), *args]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=5,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print the real directory and Git identity used by context-handoff."
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory to inspect")
    args = parser.parse_args()
    requested = Path(args.cwd).expanduser()
    try:
        cwd = requested.resolve(strict=True)
    except OSError as exc:
        print(json.dumps({"ok": False, "error": f"cwd cannot be resolved: {exc}"}))
        return 2
    if not cwd.is_dir():
        print(json.dumps({"ok": False, "error": f"cwd is not a directory: {cwd}"}))
        return 2

    top = git(cwd, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        identity = hashlib.sha256(str(cwd).encode("utf-8")).hexdigest()
        print(json.dumps({"ok": True, "cwd": str(cwd), "git": None, "workspace_id": identity}, indent=2))
        return 0

    repo_root = Path(decoded(top.stdout)).resolve(strict=False)
    branch_result = git(cwd, "branch", "--show-current")
    head_result = git(cwd, "rev-parse", "HEAD")
    git_dir_result = git(cwd, "rev-parse", "--absolute-git-dir")
    common_dir_result = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    status_result = git(cwd, "status", "--porcelain=v1", "-z", "--untracked-files=normal")

    branch = decoded(branch_result.stdout) if branch_result.returncode == 0 else ""
    head = decoded(head_result.stdout) if head_result.returncode == 0 else ""
    status = status_result.stdout if status_result.returncode == 0 else b""
    basis = "\0".join((str(cwd), str(repo_root), branch, head)).encode("utf-8")
    payload = {
        "ok": True,
        "cwd": str(cwd),
        "git": {
            "repo_root": str(repo_root),
            "branch": branch or None,
            "detached": not bool(branch),
            "head": head or None,
            "dirty": bool(status),
            "status_bytes": len(status),
            "status_sha256": hashlib.sha256(status).hexdigest(),
            "git_dir": decoded(git_dir_result.stdout) if git_dir_result.returncode == 0 else None,
            "git_common_dir": decoded(common_dir_result.stdout) if common_dir_result.returncode == 0 else None,
        },
        "workspace_id": hashlib.sha256(basis).hexdigest(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
