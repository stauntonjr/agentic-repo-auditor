import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from .test_auditor import initialize_repository
except ImportError:  # unittest discovery adds tests/ directly to sys.path.
    from test_auditor import initialize_repository


ROOT = Path(__file__).resolve().parents[1]


def snapshot_tree(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file() or item.is_symlink()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            content = os.readlink(path).encode("utf-8")
        else:
            content = path.read_bytes()
        snapshot[relative] = hashlib.sha256(content).hexdigest()
    return snapshot


class AuditorCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{ROOT / 'src'}{os.pathsep}{pythonpath}" if pythonpath else str(ROOT / "src")
        )
        return subprocess.run(
            [sys.executable, "-m", "agentic_repo_auditor", *arguments],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_cli_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fixture"
            target.mkdir()
            initialize_repository(target)
            before = snapshot_tree(target)
            first = self.run_cli("audit", str(target), "--format", "json")
            middle = snapshot_tree(target)
            second = self.run_cli("audit", str(target), "--format", "json")
            after = snapshot_tree(target)

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, middle)
        self.assertEqual(before, after)
        payload = json.loads(first.stdout)
        self.assertEqual("fixture", payload["target"]["name"])
        self.assertFalse(payload["target"]["dirty"])

    def test_markdown_and_failure_exit_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fixture"
            target.mkdir()
            initialize_repository(target, mutable_action=True)
            markdown = self.run_cli("audit", str(target), "--format", "markdown")
            advisory = self.run_cli("audit", str(target), "--format", "json", "--fail-on", "none")

        self.assertEqual(1, markdown.returncode)
        self.assertIn("# Repository audit report", markdown.stdout)
        self.assertIn("ci.immutable-actions", markdown.stdout)
        self.assertEqual(0, advisory.returncode)

    def test_version_and_usage_error_contract(self) -> None:
        version = self.run_cli("--version")
        missing = self.run_cli("audit", "/path/that/does/not/exist")
        self.assertEqual(0, version.returncode)
        self.assertIn("0.1.0", version.stdout)
        self.assertEqual(2, missing.returncode)
        self.assertIn("target is not a directory", missing.stderr)

    def test_invalid_utf8_inputs_return_two_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            target = boundary / "fixture"
            target.mkdir()
            initialize_repository(target)
            (target / ".github/workflows/check.yml").write_bytes(b"uses: \xff\n")
            workflow = self.run_cli("audit", str(target), "--format", "json")
            config_path = boundary / "config.json"
            config_path.write_bytes(b"\xff")
            config = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )

        self.assertEqual(2, workflow.returncode)
        self.assertNotIn("Traceback", workflow.stderr)
        self.assertIn("not valid UTF-8", workflow.stderr)
        self.assertEqual(2, config.returncode)
        self.assertNotIn("Traceback", config.stderr)
        self.assertIn("cannot read configuration", config.stderr)

    def test_configured_project_contract_is_deterministic_read_only_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            target = boundary / "fixture"
            target.mkdir()
            initialize_repository(target)
            (target / "harness/project.yaml").unlink()
            (target / "contract.yaml").write_text("name: portable fixture\n", encoding="utf-8")
            config_path = boundary / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "evidence": {"project_contract": {"path": "contract.yaml"}},
                    }
                ),
                encoding="utf-8",
            )
            before = snapshot_tree(target)
            first = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )
            middle = snapshot_tree(target)
            second = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )
            after = snapshot_tree(target)
            (target / "contract.yaml").write_text("[]\n", encoding="utf-8")
            malformed = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, middle)
        self.assertEqual(before, after)
        self.assertEqual(2, malformed.returncode)
        self.assertNotIn("Traceback", malformed.stderr)
        self.assertIn("non-empty object", malformed.stderr)

    def test_configured_primary_check_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            target = boundary / "fixture"
            target.mkdir()
            initialize_repository(target)
            (target / "harness/project.yaml").unlink()
            source = target / "dangerous.sh"
            source.write_text("#!/bin/sh\ntouch SHOULD_NOT_EXIST\n", encoding="utf-8")
            source.chmod(0o755)
            config_path = boundary / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2",
                        "evidence": {
                            "primary_check": {
                                "command": "./dangerous.sh",
                                "source": "dangerous.sh",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            before = snapshot_tree(target)
            first = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )
            middle = snapshot_tree(target)
            second = self.run_cli(
                "audit", str(target), "--config", str(config_path), "--format", "json"
            )
            after = snapshot_tree(target)
            sentinel_exists = (target / "SHOULD_NOT_EXIST").exists()

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, middle)
        self.assertEqual(before, after)
        self.assertFalse(sentinel_exists)
        payload = json.loads(first.stdout)
        finding = next(
            item for item in payload["findings"] if item["id"] == "testing.primary-check"
        )
        self.assertEqual("pass", finding["status"])
        self.assertEqual("dangerous.sh", finding["evidence"][0]["path"])


if __name__ == "__main__":
    unittest.main()
