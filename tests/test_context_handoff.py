import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "scripts" / "snapshot_workspace.py"
RESOLVER = ROOT / "scripts" / "resolve_target_worktree.py"
MONITOR = ROOT / "hooks" / "context_handoff_monitor.py"
CORE_SKILL = ROOT / "SKILL.md"
GOAL_SKILL = ROOT / "context-handoff-goal" / "SKILL.md"
ROUTING = ROOT / "references" / "target-routing.md"


def run_json(command: list[str], **kwargs) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)
    return result, json.loads(result.stdout)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def make_repo(root: Path) -> tuple[Path, Path]:
    repo = root / "repo"
    feature = root / "feature-worktree"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Context Handoff Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "initial")
    git(repo, "branch", "feature")
    git(repo, "worktree", "add", str(feature), "feature")
    return repo, feature


class ContextHandoffTests(unittest.TestCase):
    def test_goal_mode_is_a_separate_discoverable_skill(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        goal = GOAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("name: context-handoff-goal", goal)
        self.assertIn("$context-handoff-goal", core)
        self.assertIn("`mode: goal`", goal)

    def test_core_uses_five_point_handoff_and_exact_identity(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        self.assertIn("doing:", core)
        self.assertIn("completed:", core)
        self.assertIn("blocked:", core)
        self.assertIn("next:", core)
        self.assertIn("pitfalls:", core)
        self.assertIn("source:", core)
        self.assertIn("target:", core)
        self.assertIn("workspace:", core)
        self.assertTrue(ROUTING.exists())

    def test_active_source_goal_never_creates_concurrent_goal(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        goal = GOAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("Use `get_goal`", core)
        self.assertIn("do not start a second native Goal", core)
        self.assertIn("awaiting_source_goal_release", core)
        self.assertIn("Never complete the source Goal merely because it was delegated", goal)
        self.assertIn("never run source and target Goals concurrently", goal)

    def test_target_binding_cannot_be_faked_by_command_workdir(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        routing = ROUTING.read_text(encoding="utf-8")
        self.assertIn("registered `cwd`", core)
        self.assertIn("without a `workdir` override", core)
        self.assertIn("does not prove the thread is bound there", core)
        self.assertIn("A parent repository project is not an exact match", routing)
        self.assertIn("stop automatic creation", routing)

    def test_source_has_zero_business_work_after_receipt(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        goal = GOAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("The source must not monitor the target", core)
        self.assertIn("performs zero business work", goal)

    def test_discussion_does_not_invoke_the_skill(self) -> None:
        core = CORE_SKILL.read_text(encoding="utf-8")
        goal = GOAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("Do not execute merely because", core)
        self.assertIn("Do not execute merely because", goal)

    def test_snapshot_supports_non_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, payload = run_json([sys.executable, str(SNAPSHOT), "--cwd", directory])
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["ok"])
            self.assertIsNone(payload["git"])
            self.assertIn("workspace_locator_id", payload)
            self.assertIn("snapshot_id", payload)

    def test_snapshot_content_hash_changes_when_status_shape_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = make_repo(Path(directory))
            tracked = repo / "tracked.txt"
            tracked.write_text("one!\n", encoding="utf-8")
            first_result, first = run_json([sys.executable, str(SNAPSHOT), "--cwd", str(repo)])
            tracked.write_text("two!\n", encoding="utf-8")
            second_result, second = run_json([sys.executable, str(SNAPSHOT), "--cwd", str(repo)])
            self.assertEqual(first_result.returncode, 0)
            self.assertEqual(second_result.returncode, 0)
            self.assertEqual(first["git"]["status_sha256"], second["git"]["status_sha256"])
            self.assertNotEqual(first["git"]["content_sha256"], second["git"]["content_sha256"])
            self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertTrue(second["git"]["content_hash_complete"])

    def test_snapshot_reports_linked_worktree_identity_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, feature = make_repo(Path(directory))
            (feature / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (feature / "new.txt").write_text("new\n", encoding="utf-8")
            _, main = run_json([sys.executable, str(SNAPSHOT), "--cwd", str(repo)])
            result, linked = run_json([sys.executable, str(SNAPSHOT), "--cwd", str(feature)])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(linked["git"]["worktree_type"], "linked")
            self.assertEqual(linked["git"]["branch"], "feature")
            self.assertTrue(linked["git"]["dirty"])
            self.assertEqual(linked["git"]["status_counts"]["modified"], 1)
            self.assertEqual(linked["git"]["status_counts"]["untracked"], 1)
            self.assertEqual(main["git"]["git_common_dir"], linked["git"]["git_common_dir"])
            self.assertNotEqual(main["git"]["git_dir"], linked["git"]["git_dir"])
            self.assertNotEqual(main["workspace_locator_id"], linked["workspace_locator_id"])

    def test_snapshot_expectation_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = make_repo(Path(directory))
            result, payload = run_json([
                sys.executable,
                str(SNAPSHOT),
                "--cwd",
                str(repo),
                "--expect-snapshot-id",
                "not-the-snapshot",
            ])
            self.assertEqual(result.returncode, 3)
            self.assertFalse(payload["ok"])
            self.assertIn("snapshot_id", payload["mismatches"])

    def test_snapshot_marks_bounded_content_hash_as_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = make_repo(Path(directory))
            (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
            result, payload = run_json([
                sys.executable,
                str(SNAPSHOT),
                "--cwd",
                str(repo),
                "--max-content-bytes",
                "0",
            ])
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["git"]["dirty"])
            self.assertFalse(payload["git"]["content_hash_complete"])

    def test_resolver_maps_exact_branch_to_existing_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, feature = make_repo(Path(directory))
            result, payload = run_json([
                sys.executable,
                str(RESOLVER),
                "--repo",
                str(repo),
                "--branch",
                "feature",
            ])
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["resolution"], "exact")
            self.assertEqual(payload["target"]["resolved_path"], str(feature.resolve()))

    def test_resolver_does_not_create_worktree_for_unoccupied_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = make_repo(Path(directory))
            git(repo, "branch", "not-checked-out")
            before = git(repo, "worktree", "list", "--porcelain").stdout
            result, payload = run_json([
                sys.executable,
                str(RESOLVER),
                "--repo",
                str(repo),
                "--branch",
                "not-checked-out",
            ])
            after = git(repo, "worktree", "list", "--porcelain").stdout
            self.assertEqual(result.returncode, 3)
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["local_branch_exists"])
            self.assertEqual(before, after)

    def test_resolver_rejects_remote_tracking_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = make_repo(Path(directory))
            result, payload = run_json([
                sys.executable,
                str(RESOLVER),
                "--repo",
                str(repo),
                "--branch",
                "refs/remotes/origin/main",
            ])
            self.assertEqual(result.returncode, 2)
            self.assertFalse(payload["ok"])
            self.assertIn("not local execution branches", payload["error"])

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

    def test_public_files_contain_no_machine_private_markers(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
        ).lower()
        private_markers = (
            "/users/" + "guozhixin",
            "codex" + "sync",
            ".env" + ".local",
        )
        for marker in private_markers:
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
