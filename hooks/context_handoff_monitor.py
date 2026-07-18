#!/usr/bin/env python3
"""Optional lightweight UserPromptSubmit hook for context-handoff."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


AFFIRMATIVE_RE = re.compile(r"^\s*(?:同意|可以|好|好的|执行|开始|ok|yes)\s*[。.!！]?\s*$", re.I)
SLOW_RE = re.compile(r"(?:very slow|lagging|很慢|变慢|卡顿|很卡|卡住|上下文.{0,8}(?:太多|过大|挤爆)|对话.{0,8}(?:太长|太大))", re.I)
RECONNECT_RE = re.compile(
    r"(?:stream disconnected\s*-\s*retrying sampling request\s*\(5/5\)|reconnecting\D{0,12}(?:5/5|5\s*次))",
    re.I,
)
THRESHOLDS = (
    (500_000_000, 500, "critical"),
    (200_000_000, 200, "high"),
    (100_000_000, 100, "strong"),
    (50_000_000, 50, "soft"),
)


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}


def session_key(payload: dict) -> str:
    for key in ("session_id", "thread_id", "conversation_id", "rollout_id"):
        if payload.get(key):
            return str(payload[key])
    cwd = str(payload.get("cwd") or os.getcwd())
    return "cwd-" + hashlib.sha256(cwd.encode("utf-8")).hexdigest()[:16]


def state_path(payload: dict) -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_key(payload))[:120]
    return root / "codex-context-handoff" / f"{safe}.json"


def load_state(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.loads(stream.read(16_384))
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def transcript_size(payload: dict) -> int | None:
    raw = payload.get("transcript_path")
    if not raw:
        return None
    try:
        return os.stat(os.path.expanduser(str(raw))).st_size
    except OSError:
        return None


def size_signal(size: int | None) -> tuple[int, str] | None:
    if size is None:
        return None
    for minimum, bucket, severity in THRESHOLDS:
        if size >= minimum:
            return bucket, severity
    return None


def emit(note: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "- " + note,
        }
    }, ensure_ascii=False))


def main() -> int:
    try:
        payload = load_payload()
        prompt = str(payload.get("prompt") or "")
        if not prompt.strip():
            return 0
        path = state_path(payload)
        state = load_state(path)
        was_pending = bool(state.get("pending_confirmation"))
        if was_pending:
            state["pending_confirmation"] = False
            save_state(path, state)
            if AFFIRMATIVE_RE.fullmatch(prompt):
                emit(
                    "The user may have accepted the immediately preceding visible handoff recommendation. "
                    "Invoke the exact command recommended there only if it was unambiguous; otherwise treat this as ordinary approval."
                )
                return 0

        size = transcript_size(payload)
        signal = size_signal(size)
        reconnect = bool(RECONNECT_RE.search(prompt))
        slow = bool(SLOW_RE.search(prompt))
        highest = int(state.get("highest_size_bucket") or 0)
        should_remind = reconnect
        reason = "the user reported sampling reconnect 5/5"
        severity = "strong"

        if signal:
            bucket, severity = signal
            if bucket > highest and (bucket >= 100 or slow or reconnect):
                should_remind = True
                reason = f"the transcript is about {size / 1_000_000:.1f} MB and entered the {bucket} MB bucket"
                state["highest_size_bucket"] = bucket

        if reconnect:
            fingerprint = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:16]
            if fingerprint == state.get("last_reconnect_fingerprint") and not (signal and signal[0] > highest):
                should_remind = False
            else:
                state["last_reconnect_fingerprint"] = fingerprint

        if not should_remind:
            return 0

        state["pending_confirmation"] = True
        save_state(path, state)
        urgency = {
            "critical": "Treat this as critical and hand off after the current safe unit.",
            "high": "Treat this as high priority at the next safe stopping point.",
        }.get(severity, "Treat this as a strong signal, not proof of root cause.")
        emit(
            f"{reason}. {urgency} Recommend exactly one command at the end of the response: "
            "`$context-handoff` to continue discussing, or `$context-handoff-goal` when the objective is ready for execution. "
            "Do not interrupt critical work and do not scan transcript or log contents."
        )
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
