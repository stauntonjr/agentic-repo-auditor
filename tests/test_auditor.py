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
            (
                "jobs:\n  test:\n    steps:\n      - ? uses\n        : owner/repository@main\n"
            ): "fail",
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
            "env: { uses: this-is-an-env-value@main }\njobs:\n  test:\n    steps: []\n": "pass",
            (
                "jobs:\n  test:\n    steps:\n      - run: echo test\n"
                "        with: { uses: ordinary-input@main }\n"
            ): "pass",
            (
                "defaults: &action\n  uses: owner/repository@main\n"
                "jobs:\n  test:\n    steps:\n      - <<: *action\n"
            ): "fail",
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

    def test_instruction_coverage_recognizes_bounded_equivalent_vocabulary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "AGENTS.md").write_text(
                "Treat current code and contracts as authoritative.\n"
                "Run tests, follow safety limits, and record verification results.\n",
                encoding="utf-8",
            )
            report = audit_repository(root)

        finding = next(
            item for item in report.findings if item.finding_id == "agent-readiness.instructions"
        )
        self.assertEqual("pass", finding.status)
        self.assertEqual(
            "present=['source', 'test', 'safety', 'verification']; missing=[]; "
            "matches=['source:authoritative', 'test:tests', 'safety:safety', "
            "'verification:verification']",
            finding.evidence[0].value,
        )

    def test_instruction_coverage_keeps_incomplete_prose_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "AGENTS.md").write_text(
                "Authoritative contest results are documented.\n", encoding="utf-8"
            )
            report = audit_repository(root)

        finding = next(
            item for item in report.findings if item.finding_id == "agent-readiness.instructions"
        )
        self.assertEqual("warn", finding.status)
        self.assertIn("missing=['test', 'safety', 'verification']", finding.evidence[0].value)
        self.assertNotIn("test:contest", finding.evidence[0].value)

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
            (
                "example",
                "---\nname: example\ndescription: >\n  Valid folded\n  metadata\n---\n# Example\n",
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

    def test_skill_frontmatter_enforces_yaml_resource_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            extra = "".join(f"extra-{index}: value\n" for index in range(10_100))
            (root / ".agents/skills/example/SKILL.md").write_text(
                f"---\nname: example\ndescription: Bounded metadata\n{extra}---\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AuditError, "Skill frontmatter YAML exceeds"):
                audit_repository(root)

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

    def test_project_contract_supports_configured_path_and_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "harness/project.yaml").unlink()
            (root / "project-contract.json").write_text(
                json.dumps({"name": "portable fixture"}), encoding="utf-8"
            )
            path_config_file = boundary / "path-config.json"
            path_config_file.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "evidence": {"project_contract": {"path": "project-contract.json"}},
                    }
                ),
                encoding="utf-8",
            )
            path_config = load_config(path_config_file)
            first = audit_repository(root, path_config)
            second = audit_repository(root, path_config)

            disposition_config_file = boundary / "disposition-config.json"
            disposition_config_file.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "evidence": {
                            "project_contract": {
                                "not_applicable_reason": (
                                    "This repository is a single-purpose fixture with no delegated authority."
                                )
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            disposition_report = audit_repository(root, load_config(disposition_config_file))

        finding = next(
            item for item in first.findings if item.finding_id == "governance.project-contract"
        )
        self.assertEqual("pass", finding.status)
        self.assertEqual(
            ["project-contract.json"],
            [item.path for item in finding.evidence if item.kind == "configured-project-contract"],
        )
        self.assertEqual(render_json(first), render_json(second))
        self.assertEqual(
            {"path": "project-contract.json"},
            first.as_dict()["configuration"]["evidence"]["project_contract"],
        )
        self.assertIn("configured path `project-contract.json`", render_markdown(first))
        disposition = next(
            item
            for item in disposition_report.findings
            if item.finding_id == "governance.project-contract"
        )
        self.assertEqual("not-applicable", disposition.status)
        self.assertIn("single-purpose fixture", disposition.evidence[0].value)

    def test_project_contract_absent_and_malformed_automatic_evidence_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            contract = root / "harness/project.yaml"
            contract.unlink()
            absent_report = audit_repository(root)
            contract.write_text("[]\n", encoding="utf-8")
            malformed_report = audit_repository(root)

        absent = next(
            item
            for item in absent_report.findings
            if item.finding_id == "governance.project-contract"
        )
        malformed = next(
            item
            for item in malformed_report.findings
            if item.finding_id == "governance.project-contract"
        )
        self.assertEqual(("warn", "warn"), (absent.status, malformed.status))
        self.assertEqual("project-contract-error", malformed.evidence[0].kind)

    def test_configured_project_contract_rejects_malformed_and_unsafe_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "malformed.yaml").write_text("[]\n", encoding="utf-8")
            outside = boundary / "outside.json"
            outside.write_text('{"outside": true}\n', encoding="utf-8")
            os.symlink(outside, root / "linked.json")
            (root / "contract-dir.json").mkdir()
            outside_directory = boundary / "outside-directory"
            outside_directory.mkdir()
            (outside_directory / "contract.json").write_text(
                '{"outside": true}\n', encoding="utf-8"
            )
            os.symlink(outside_directory, root / "linked-directory")

            for relative, expected in (
                ("missing.json", "absent"),
                ("malformed.yaml", "non-empty object"),
                ("linked.json", "symlink"),
                ("contract-dir.json", "directory"),
                ("linked-directory/contract.json", "symlink"),
            ):
                with self.subTest(relative=relative):
                    config_file = boundary / f"{relative.replace('/', '-')}.config.json"
                    config_file.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.1",
                                "evidence": {"project_contract": {"path": relative}},
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(AuditError, expected):
                        audit_repository(root, load_config(config_file))

            for declaration in (
                {"path": "../outside.json"},
                {"path": "/absolute.json"},
                {"path": "contract.txt"},
                {"path": " contract.json"},
                {"path": ".git/project.json"},
                {"path": "contract\tname.json"},
                {"not_applicable_reason": ""},
                {"not_applicable_reason": "line one\nline two"},
                {"path": "contract.json", "not_applicable_reason": "conflict"},
            ):
                with self.subTest(declaration=declaration):
                    config_file = boundary / "invalid-config.json"
                    config_file.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.1",
                                "evidence": {"project_contract": declaration},
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaises(AuditError):
                        load_config(config_file)

            legacy_with_evidence = boundary / "legacy-with-evidence.json"
            legacy_with_evidence.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "evidence": {"project_contract": {"not_applicable_reason": "legacy"}},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AuditError, "requires schema_version 1.1"):
                load_config(legacy_with_evidence)

    def test_primary_check_supports_configured_command_source_and_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "harness/project.yaml").unlink()
            (root / "Makefile").write_text("check:\n\tpytest -q\n", encoding="utf-8")
            config_file = boundary / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2",
                        "evidence": {
                            "primary_check": {
                                "command": "make check",
                                "source": "Makefile",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(config_file)
            first = audit_repository(root, config)
            second = audit_repository(root, config)

            disposition_file = boundary / "disposition.json"
            disposition_file.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2",
                        "evidence": {
                            "primary_check": {
                                "not_applicable_reason": (
                                    "This repository stores one static fixture and has no executable checks."
                                )
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            disposition_report = audit_repository(root, load_config(disposition_file))

        finding = next(
            item for item in first.findings if item.finding_id == "testing.primary-check"
        )
        self.assertEqual("pass", finding.status)
        self.assertEqual(
            [("configured-primary-check", "Makefile", "make check")],
            [(item.kind, item.path, item.value) for item in finding.evidence],
        )
        self.assertEqual(render_json(first), render_json(second))
        self.assertEqual(
            {"command": "make check", "source": "Makefile"},
            first.as_dict()["configuration"]["evidence"]["primary_check"],
        )
        self.assertIn(
            "Primary-check evidence: `make check` from `Makefile`", render_markdown(first)
        )
        disposition = next(
            item
            for item in disposition_report.findings
            if item.finding_id == "testing.primary-check"
        )
        self.assertEqual("not-applicable", disposition.status)
        self.assertIn("static fixture", disposition.evidence[0].value)

    def test_primary_check_preserves_harness_compatibility_without_prose_inference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            root.mkdir()
            initialize_repository(root)
            automatic_report = audit_repository(root)
            contract = root / "harness/project.yaml"
            contract.unlink()
            (root / "README.md").write_text(
                "# Fixture\nRun `make check` as the authoritative test.\n", encoding="utf-8"
            )
            prose_report = audit_repository(root)
            contract.write_text(
                json.dumps({"engineering": {"command_contract": {"primary_check": "true"}}}),
                encoding="utf-8",
            )
            noop_report = audit_repository(root)

        automatic = next(
            item for item in automatic_report.findings if item.finding_id == "testing.primary-check"
        )
        prose = next(
            item for item in prose_report.findings if item.finding_id == "testing.primary-check"
        )
        noop = next(
            item for item in noop_report.findings if item.finding_id == "testing.primary-check"
        )
        self.assertEqual(
            ("pass", "automatic-primary-check"), (automatic.status, automatic.evidence[0].kind)
        )
        self.assertEqual("warn", prose.status)
        self.assertEqual(("warn", "primary-check-error"), (noop.status, noop.evidence[0].kind))
        self.assertIn("successful no-op", noop.evidence[0].value)

    def test_configured_primary_check_rejects_invalid_commands_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            root = boundary / "fixture"
            root.mkdir()
            initialize_repository(root)
            (root / "empty-source").write_text("", encoding="utf-8")
            (root / "source-directory").mkdir()
            outside = boundary / "outside"
            outside.write_text("external source\n", encoding="utf-8")
            os.symlink(outside, root / "linked-source")
            outside_directory = boundary / "outside-directory"
            outside_directory.mkdir()
            (outside_directory / "source").write_text("external source\n", encoding="utf-8")
            os.symlink(outside_directory, root / "linked-directory")

            for command in (
                "",
                " true",
                "true",
                "/bin/true",
                "exit 0",
                "echo passed",
                "sh -c true",
                "python3 -c pass",
                "sleep 0",
                "not-applicable: no tests",
                "pytest\nruff check .",
                "pytest\t-q",
                "pytest '",
            ):
                with self.subTest(command=command):
                    config_file = boundary / "invalid-command.json"
                    config_file.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.2",
                                "evidence": {
                                    "primary_check": {
                                        "command": command,
                                        "source": "README.md",
                                    }
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaises(AuditError):
                        load_config(config_file)

            for source, expected in (
                ("missing-source", "absent"),
                ("empty-source", "empty"),
                ("source-directory", "directory"),
                ("linked-source", "symlink"),
                ("linked-directory/source", "symlink"),
            ):
                with self.subTest(source=source):
                    config_file = boundary / f"{source.replace('/', '-')}.json"
                    config_file.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.2",
                                "evidence": {
                                    "primary_check": {
                                        "command": "make check",
                                        "source": source,
                                    }
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(AuditError, expected):
                        audit_repository(root, load_config(config_file))

            for source in (
                "../outside",
                "/outside",
                "./README.md",
                " linked-source",
                ".git/config",
                "source\tname",
            ):
                with self.subTest(source=source):
                    config_file = boundary / "escaping-source.json"
                    config_file.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.2",
                                "evidence": {
                                    "primary_check": {
                                        "command": "make check",
                                        "source": source,
                                    }
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaises(AuditError):
                        load_config(config_file)

            legacy = boundary / "schema-1.1-primary-check.json"
            legacy.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "evidence": {
                            "primary_check": {
                                "command": "make check",
                                "source": "README.md",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AuditError, "requires schema_version 1.2"):
                load_config(legacy)

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
