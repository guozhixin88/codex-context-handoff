import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "scripts" / "snapshot_workspace.py"
MONITOR = ROOT / "hooks" / "context_handoff_monitor.py"
CORE_SKILL = ROOT / "SKILL.md"
GOAL_SKILL = ROOT / "context-handoff-goal" / "SKILL.md"


class ContextHandoffTests(unittest.TestCase):
    def test_goal_mode_is_a_separate_discoverable_skill(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        goal = GOAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("name: context-handoff-goal", goal)
        self.assertIn("$context-handoff-goal", core)
        self.assertIn("mode: direct_goal", goal)

    def test_snapshot_supports_non_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SNAPSHOT), "--cwd", directory],
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["ok"])
            self.assertIsNone(payload["git"])

    def test_monitor_reminds_once_and_accepts_immediate_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "rollout.jsonl"
            with transcript.open("wb") as stream:
                stream.seek(100_000_000)
                stream.write(b"\0")
            env = os.environ.copy()
            env["HOME"] = str(root / "home")
            env["XDG_STATE_HOME"] = str(root / "state")

            def run(prompt: str) -> subprocess.CompletedProcess[str]:
                payload = json.dumps({
                    "prompt": prompt,
                    "cwd": directory,
                    "session_id": "session-test",
                    "transcript_path": str(transcript),
                })
                return subprocess.run(
                    [sys.executable, str(MONITOR)],
                    input=payload,
                    text=True,
                    capture_output=True,
                    check=False,
                    env=env,
                )

            first = run("continue")
            self.assertIn("$context-handoff-goal", first.stdout)
            repeated = run("keep going")
            self.assertEqual(repeated.stdout, "")

            state = root / "state" / "codex-context-handoff" / "session-test.json"
            data = json.loads(state.read_text(encoding="utf-8"))
            data["pending_confirmation"] = True
            state.write_text(json.dumps(data), encoding="utf-8")
            accepted = run("yes")
            self.assertIn("immediately preceding visible handoff", accepted.stdout)


if __name__ == "__main__":
    unittest.main()
