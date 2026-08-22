import json
import os
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

    def test_workflow_extraction_handles_yaml_forms_and_fails_closed(self) -> None:
        cases = {
            'jobs:\n  test:\n    "uses": owner/repository@main\n': "fail",
            "jobs:\n  test:\n    'uses': owner/repository@main\n": "fail",
            "jobs:\n  test: { uses: owner/repository@main }\n": "fail",
            "jobs:\n  test:\n    - ? uses\n      : owner/repository@main\n": "fail",
            "jobs:\n  test:\n    uses : owner/repository@main\n": "fail",
            "jobs:\n  test:\n    uses: docker://alpine@sha256:not-a-digest\n": "fail",
            (
                "jobs:\n  test:\n    steps:\n      - run: |\n"
                "          echo 'uses: owner/repository@main'\n"
                "      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n"
            ): "pass",
            (
                'jobs:\n  test:\n    steps:\n      - run: "hello\n'
                '          uses: shell-text@main"\n'
            ): "pass",
            (
                "jobs:\n  test:\n    uses: "
                "docker://alpine@sha256:0123456789abcdef0123456789abcdef"
                "0123456789abcdef0123456789abcdef\n"
            ): "pass",
        }
        for content, expected in cases.items():
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "fixture"
                    root.mkdir()
                    initialize_repository(root)
                    (root / ".github/workflows/check.yml").write_text(content, encoding="utf-8")
                    report = audit_repository(root).as_dict()
                finding = next(
                    item for item in report["findings"] if item["id"] == "ci.immutable-actions"
                )
                self.assertEqual(expected, finding["status"])

    def test_codeql_requires_an_extracted_action_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            workflow = root / ".github/workflows/check.yml"
            for content in (
                "# uses: github/codeql-action/init@main\n",
                "jobs:\n  test:\n    steps:\n      - run: echo github/codeql-action/init\n",
            ):
                workflow.write_text(content, encoding="utf-8")
                report = audit_repository(root).as_dict()
                finding = next(
                    item for item in report["findings"] if item["id"] == "security.code-scanning"
                )
                self.assertEqual("warn", finding["status"])
            workflow.write_text(
                "jobs:\n  test:\n    steps:\n"
                "      - uses: github/codeql-action/init@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            report = audit_repository(root).as_dict()
        finding = next(
            item for item in report["findings"] if item["id"] == "security.code-scanning"
        )
        self.assertEqual("pass", finding["status"])

    def test_state_identity_binds_dirty_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            workflow = root / ".github/workflows/check.yml"
            workflow.write_text(
                "jobs:\n  test:\n    uses: owner/repository@main\n", encoding="utf-8"
            )
            first = audit_repository(root)
            workflow.write_text(
                "jobs:\n  test:\n    uses: "
                "actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            second = audit_repository(root)

        self.assertNotEqual(first.target.state_id, second.target.state_id)
        first_action = next(
            item for item in first.findings if item.finding_id == "ci.immutable-actions"
        )
        second_action = next(
            item for item in second.findings if item.finding_id == "ci.immutable-actions"
        )
        self.assertEqual(("fail", "pass"), (first_action.status, second_action.status))

    def test_state_identity_binds_hidden_and_nested_repository_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            subprocess.run(
                ["git", "update-index", "--assume-unchanged", "AGENTS.md"],
                cwd=root,
                check=True,
            )
            (root / "AGENTS.md").write_text("hidden version one\n", encoding="utf-8")
            hidden_first = audit_repository(root).target.state_id
            (root / "AGENTS.md").write_text("hidden version two\n", encoding="utf-8")
            hidden_second = audit_repository(root).target.state_id

            nested = root / "vendor/nested"
            nested.mkdir(parents=True)
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=nested,
                check=True,
                stdout=subprocess.PIPE,
            )
            (nested / "payload.txt").write_text("nested version one\n", encoding="utf-8")
            subprocess.run(["git", "add", "payload.txt"], cwd=nested, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "nested fixture",
                ],
                cwd=nested,
                check=True,
                stdout=subprocess.PIPE,
            )
            nested_first = audit_repository(root).target.state_id
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "--allow-empty",
                    "-m",
                    "head only",
                ],
                cwd=nested,
                check=True,
                stdout=subprocess.PIPE,
            )
            nested_head_second = audit_repository(root).target.state_id
            object_id = subprocess.run(
                ["git", "hash-object", "-w", "--stdin"],
                cwd=nested,
                check=True,
                input="index-only version\n",
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            subprocess.run(
                ["git", "update-index", "--cacheinfo", "100644", object_id, "payload.txt"],
                cwd=nested,
                check=True,
            )
            nested_index_second = audit_repository(root).target.state_id
            (nested / "payload.txt").write_text("nested version two\n", encoding="utf-8")
            nested_worktree_second = audit_repository(root).target.state_id

        self.assertNotEqual(hidden_first, hidden_second)
        self.assertNotEqual(nested_first, nested_head_second)
        self.assertNotEqual(nested_head_second, nested_index_second)
        self.assertNotEqual(nested_index_second, nested_worktree_second)

    def test_state_identity_binds_dirty_gitlink_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            nested = root / "vendor/nested"
            nested.mkdir(parents=True)
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=nested,
                check=True,
                stdout=subprocess.PIPE,
            )
            (nested / "payload.txt").write_text("stable worktree\n", encoding="utf-8")
            (nested / ".gitattributes").write_text("*.txt filter=evil\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitattributes", "payload.txt"], cwd=nested, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "nested fixture",
                ],
                cwd=nested,
                check=True,
                stdout=subprocess.PIPE,
            )
            child_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=nested,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    "160000",
                    child_head,
                    "vendor/nested",
                ],
                cwd=root,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "track gitlink",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            clean_gitlink = audit_repository(root).target.state_id
            subprocess.run(
                ["git", "update-index", "--assume-unchanged", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            clean_assume_unchanged = audit_repository(root).target.state_id
            subprocess.run(
                ["git", "update-index", "--no-assume-unchanged", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            subprocess.run(
                ["git", "update-index", "--skip-worktree", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            clean_skip_worktree = audit_repository(root).target.state_id
            subprocess.run(
                ["git", "update-index", "--no-skip-worktree", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            sentinel = Path(directory) / "nested-filter-fired"
            driver = nested / "filter.sh"
            driver.write_text(f"#!/bin/sh\ntouch '{sentinel}'\ncat\n", encoding="utf-8")
            driver.chmod(0o755)
            subprocess.run(
                ["git", "config", "filter.evil.clean", str(driver)], cwd=nested, check=True
            )
            subprocess.run(
                ["git", "config", "filter.evil.process", str(driver)], cwd=nested, check=True
            )
            subprocess.run(
                ["git", "config", "filter.evil.required", "true"], cwd=nested, check=True
            )
            (nested / "payload.txt").write_text("dirty stable worktree\n", encoding="utf-8")
            first = ""
            second = ""
            for message in ("head one", "head two"):
                subprocess.run(
                    [
                        "git",
                        "-c",
                        "user.name=Fixture",
                        "-c",
                        "user.email=fixture@example.invalid",
                        "commit",
                        "--allow-empty",
                        "-m",
                        message,
                    ],
                    cwd=nested,
                    check=True,
                    stdout=subprocess.PIPE,
                )
                state_id = audit_repository(root).target.state_id
                if message == "head one":
                    first = state_id
                else:
                    second = state_id
            subprocess.run(
                ["git", "update-index", "--assume-unchanged", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            assume_unchanged = audit_repository(root).target.state_id
            subprocess.run(
                ["git", "update-index", "--no-assume-unchanged", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            subprocess.run(
                ["git", "update-index", "--skip-worktree", ".gitattributes"],
                cwd=nested,
                check=True,
            )
            skip_worktree = audit_repository(root).target.state_id
            self.assertFalse(sentinel.exists())

        self.assertNotEqual(first, second)
        self.assertNotEqual(clean_gitlink, clean_assume_unchanged)
        self.assertNotEqual(clean_assume_unchanged, clean_skip_worktree)
        self.assertNotEqual(second, assume_unchanged)
        self.assertNotEqual(assume_unchanged, skip_worktree)

    def test_repository_configured_fsmonitor_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            sentinel = Path(directory) / "fsmonitor-fired"
            monitor = root / "monitor.sh"
            monitor.write_text(f"#!/bin/sh\ntouch '{sentinel}'\n", encoding="utf-8")
            monitor.chmod(0o755)
            subprocess.run(["git", "config", "core.fsmonitor", str(monitor)], cwd=root, check=True)
            audit_repository(root)
            self.assertFalse(sentinel.exists())

    def test_repository_configured_clean_filter_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            attributes = root / ".gitattributes"
            payload = root / "payload.txt"
            attributes.write_text("*.txt filter=evil\n", encoding="utf-8")
            payload.write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitattributes", "payload.txt"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-m",
                    "filter fixture",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            sentinel = Path(directory) / "filter-fired"
            driver = root / "filter.sh"
            driver.write_text(f"#!/bin/sh\ntouch '{sentinel}'\ncat\n", encoding="utf-8")
            driver.chmod(0o755)
            subprocess.run(
                ["git", "config", "extensions.worktreeConfig", "true"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "config", "--worktree", "filter.evil.clean", str(driver)],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "--worktree", "filter.evil.process", str(driver)],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "--worktree", "filter.evil.required", "true"],
                cwd=root,
                check=True,
            )
            payload.write_text("changed\n", encoding="utf-8")
            audit_repository(root)
            self.assertFalse(sentinel.exists())

    def test_symlinked_evidence_is_not_followed_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            external = boundary / "external-agents.md"
            external.write_text("source test safety verification\n", encoding="utf-8")
            (root / "AGENTS.md").unlink()
            os.symlink(external, root / "AGENTS.md")
            first = audit_repository(root)
            external.write_text("changed outside the repository\n", encoding="utf-8")
            second = audit_repository(root)

        first_finding = next(
            item for item in first.findings if item.finding_id == "agent-readiness.instructions"
        )
        second_finding = next(
            item for item in second.findings if item.finding_id == "agent-readiness.instructions"
        )
        self.assertEqual(first_finding, second_finding)
        self.assertEqual("warn", first_finding.status)

    def test_quoted_skill_metadata_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / ".agents/skills/example/SKILL.md").write_text(
                '---\nname: "example"\ndescription: "Valid quoted metadata"\n---\n# Example\n',
                encoding="utf-8",
            )
            report = audit_repository(root)

        finding = next(
            item for item in report.findings if item.finding_id == "agent-readiness.skills"
        )
        self.assertEqual("pass", finding.status)

    def test_skill_frontmatter_enforces_portable_spec_constraints(self) -> None:
        cases = (
            (
                "example",
                "---\nmetadata:\n  name: example\n  description: Nested only\n---\n",
                "fail",
            ),
            (
                "example",
                "---\nname: different\ndescription: Parent mismatch\n---\n",
                "fail",
            ),
            (
                "a" * 65,
                f"---\nname: {'a' * 65}\ndescription: Too long a name\n---\n",
                "fail",
            ),
            (
                "example",
                f"---\nname: example\ndescription: {'d' * 1025}\n---\n",
                "fail",
            ),
            (
                "example",
                "---\r\nname: example\r\ndescription: CRLF metadata\r\n---\r\n# Skill\r\n",
                "pass",
            ),
        )
        for directory_name, content, expected in cases:
            with self.subTest(directory_name=directory_name, expected=expected):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "fixture"
                    root.mkdir()
                    initialize_repository(root)
                    if directory_name != "example":
                        skill = root / ".agents/skills" / directory_name / "SKILL.md"
                        skill.parent.mkdir()
                    else:
                        skill = root / ".agents/skills/example/SKILL.md"
                    skill.write_text(content, encoding="utf-8", newline="")
                    report = audit_repository(root)
                finding = next(
                    item for item in report.findings if item.finding_id == "agent-readiness.skills"
                )
                self.assertEqual(expected, finding.status)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / ".agents/skills/example/SKILL.md").write_text(
                "---\nname: example\ndescription: >\n  Valid folded\n  metadata\n---\n# Example\n",
                encoding="utf-8",
            )
            report = audit_repository(root)
        finding = next(
            item for item in report.findings if item.finding_id == "agent-readiness.skills"
        )
        self.assertEqual("pass", finding.status)

    def test_presence_checks_reject_directories_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            dependabot = root / ".github/dependabot.yml"
            dependabot.unlink()
            dependabot.mkdir()
            security = root / "SECURITY.md"
            security.unlink()
            external = boundary / "SECURITY.md"
            external.write_text("external policy\n", encoding="utf-8")
            os.symlink(external, security)
            report = audit_repository(root)

        statuses = {
            item.finding_id: item.status
            for item in report.findings
            if item.finding_id in {"security.dependency-updates", "security.policy"}
        }
        self.assertEqual(
            {"security.dependency-updates": "warn", "security.policy": "warn"}, statuses
        )

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
            duplicate = root / "duplicate.json"
            duplicate.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "disabled_checks": ["git.clean-worktree", "git.clean-worktree"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AuditError, "unique check IDs"):
                load_config(duplicate)

        self.assertEqual(frozenset({"git.clean-worktree"}), config.disabled_checks)

    def test_non_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AuditError):
                audit_repository(Path(directory))


if __name__ == "__main__":
    unittest.main()
