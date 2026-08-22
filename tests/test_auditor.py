import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_repo_auditor.audit import AuditError, audit_repository, load_config  # noqa: E402
from agentic_repo_auditor.model import CATEGORIES, SCHEMA_VERSION  # noqa: E402
from agentic_repo_auditor.render import render_json, render_markdown  # noqa: E402


def initialize_repository(root: Path, *, mutable_action: bool = False) -> None:
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".agents/skills/example").mkdir(parents=True)
    (root / "harness").mkdir()
    (root / "tests").mkdir()
    files = {
        "AGENTS.md": "# Rules\nSources, tests, safety, and verification are required.\n",
        "README.md": "# Fixture\n",
        "CONTRIBUTING.md": "# Contributing\n",
        "LICENSE": "MIT\n",
        "SECURITY.md": "# Security\n",
        ".github/dependabot.yml": "version: 2\nupdates: []\n",
        ".github/workflows/check.yml": (
            "name: check\npermissions:\n  contents: read\njobs:\n  test:\n"
            "    uses: owner/repository@main\n"
            if mutable_action
            else "name: check\npermissions:\n  contents: read\njobs:\n  test:\n"
            "    uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n"
            "    # github/codeql-action\n"
        ),
        ".agents/skills/example/SKILL.md": (
            "---\nname: example\ndescription: Example portable skill.\n---\n# Example\n"
        ),
        "harness/project.yaml": json.dumps(
            {"engineering": {"command_contract": {"primary_check": "make smoke"}}}
        ),
        "tests/test_fixture.py": "def test_fixture():\n    assert True\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )


class AuditorTests(unittest.TestCase):
    def test_report_is_deterministic_complete_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            first = audit_repository(root)
            second = audit_repository(root)

        self.assertEqual(SCHEMA_VERSION, first.as_dict()["schema_version"])
        self.assertEqual(render_json(first), render_json(second))
        self.assertEqual(render_markdown(first), render_markdown(second))
        findings = first.as_dict()["findings"]
        self.assertEqual(sorted(item["id"] for item in findings), [item["id"] for item in findings])
        self.assertEqual(set(CATEGORIES), {item["category"] for item in findings})
        self.assertTrue(all(item["evidence"] for item in findings))
        self.assertEqual(len(findings), first.as_dict()["summary"]["total"])

    def test_mutable_action_is_a_high_severity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root, mutable_action=True)
            report = audit_repository(root).as_dict()

        finding = next(item for item in report["findings"] if item["id"] == "ci.immutable-actions")
        self.assertEqual("fail", finding["status"])
        self.assertEqual("high", finding["severity"])
        self.assertEqual("owner/repository@main", finding["evidence"][1]["value"])

    def test_config_disables_known_check_and_rejects_unknown_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.json"
            valid.write_text(
                json.dumps({"schema_version": "1.0", "disabled_checks": ["git.clean-worktree"]}),
                encoding="utf-8",
            )
            invalid = root / "invalid.json"
            invalid.write_text(
                json.dumps({"schema_version": "1.0", "disabled_checks": ["missing.check"]}),
                encoding="utf-8",
            )
            config = load_config(valid)
            with self.assertRaisesRegex(AuditError, "unknown disabled checks"):
                load_config(invalid)

        self.assertEqual(frozenset({"git.clean-worktree"}), config.disabled_checks)

    def test_non_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AuditError):
                audit_repository(Path(directory))


if __name__ == "__main__":
    unittest.main()
