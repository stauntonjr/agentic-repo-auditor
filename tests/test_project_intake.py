import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.common import load_json
from tools.project_intake import copy_template, normalize_answer, render


ROOT = Path(__file__).resolve().parents[1]


def subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("COV_CORE_"):
            environment.pop(key)
    return environment


def template_project() -> dict:
    project = load_json(ROOT / "harness/project.yaml")
    project["template_mode"] = True
    project["project"]["profile"] = "generic"
    project["engineering"]["command_contract"] = {
        "primary_check": "make smoke",
        "bootstrap": "TBD",
        "format_check": "TBD",
        "lint": "TBD",
        "typecheck": "TBD",
        "unit": "python3 -m unittest discover -s tests -v",
        "integration": "TBD",
        "package_smoke": "TBD",
    }
    project["engineering"]["quality"] = {
        "dependency_lock": "required-if-dependencies",
        "coverage_policy": "ratchet-or-explicit-exception",
        "required_checks": ["format_check", "lint", "unit"],
        "property_testing": "profile-selected",
    }
    project["engineering"]["versioning"].update(
        {"strategy": "TBD", "current": "TBD", "public_contract": [], "source": "TBD"}
    )
    return project


class ProjectIntakeTests(unittest.TestCase):
    def test_python_profile_overrides_template_placeholders(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "python-data", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        project, _, _ = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual("uv run pytest", project["engineering"]["test_commands"][0])
        self.assertEqual("uv.lock", project["engineering"]["quality"]["dependency_lock"])
        self.assertEqual("hypothesis", project["engineering"]["quality"]["property_testing"])
        self.assertIn("pytest", project["engineering"]["command_contract"]["unit"])

    def test_no_version_strategy_does_not_require_artificial_version_fields(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        raw["engineering.versioning.strategy"] = "none"
        for field in (
            "engineering.versioning.current",
            "engineering.versioning.public_contract",
            "engineering.versioning.source",
        ):
            raw.pop(field)
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
            for key, value in raw.items()
        }
        project, _, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual([], missing)
        self.assertFalse(project["template_mode"])
        self.assertEqual("none", project["engineering"]["versioning"]["strategy"])
        self.assertEqual("not-applicable", project["engineering"]["versioning"]["current"])
        self.assertEqual("not-applicable", project["engineering"]["versioning"]["source"])

    def test_profile_id_cannot_escape_profile_directory(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "../../outside", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        with self.assertRaisesRegex(ValueError, "invalid project profile ID"):
            render(
                template_project(),
                load_json(ROOT / ".github/planning.json"),
                answers,
                profile_root=ROOT / "harness/profiles",
            )

    def test_unknown_profile_cannot_report_context_ready(self) -> None:
        answers = {
            "project.profile": normalize_answer(
                "missing-profile", source="test", recorded_at="2026-08-22T00:00:00Z"
            )
        }
        with self.assertRaisesRegex(ValueError, "unknown project profile"):
            render(
                template_project(),
                load_json(ROOT / ".github/planning.json"),
                answers,
                profile_root=ROOT / "harness/profiles",
            )

    def test_copy_excludes_generated_dependency_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            target = Path(directory) / "target"
            source.mkdir()
            (source / "keep.txt").write_text("source\n", encoding="utf-8")
            (source / ".venv/lib").mkdir(parents=True)
            (source / ".venv/lib/dependency.py").write_text("generated\n", encoding="utf-8")
            (source / "node_modules/package").mkdir(parents=True)
            (source / "node_modules/package/index.js").write_text("generated\n", encoding="utf-8")
            copy_template(source, target)
            self.assertTrue((target / "keep.txt").is_file())
            self.assertFalse((target / ".venv").exists())
            self.assertFalse((target / "node_modules").exists())

    def test_unresolved_command_capability_keeps_intake_provisional(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        raw.pop("engineering.command_contract.typecheck")
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
            for key, value in raw.items()
        }
        project, _, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertTrue(project["template_mode"])
        self.assertIn("engineering.command_contract.typecheck", missing)

    def test_fixture_resolves_essential_context(self) -> None:
        raw = load_json(ROOT / "harness/fixtures/intake.answers.json")
        answers = {
            key: normalize_answer(value, source="test", recorded_at="2026-08-21T00:00:00Z")
            for key, value in raw.items()
        }
        project, planning, missing = render(
            template_project(),
            load_json(ROOT / ".github/planning.json"),
            answers,
            profile_root=ROOT / "harness/profiles",
        )
        self.assertEqual([], missing)
        self.assertFalse(project["template_mode"])
        self.assertEqual("Example Agent Project", project["project"]["name"])
        self.assertEqual("semver", project["engineering"]["versioning"]["strategy"])
        self.assertEqual("0.1.0", project["engineering"]["versioning"]["current"])
        self.assertEqual(
            ["CLI", "configuration schema"],
            project["engineering"]["versioning"]["public_contract"],
        )
        self.assertEqual("make smoke", project["engineering"]["command_contract"]["primary_check"])
        self.assertEqual("example/example-agent-project", planning["repository"])
        self.assertEqual("example", planning["project"]["owner"])

    def test_cli_creates_a_valid_derived_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "derived"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
                self.assertEqual(2, result.returncode)
                self.assertIn("cross-repository intake", result.stderr)
                return
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = subprocess.run(
                [sys.executable, str(target / "tools/harness_check.py"), "--json"],
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue((target / "harness/intake.json").is_file())
            self.assertTrue((target / ".pi/settings.json").is_file())
            self.assertTrue((target / "harness/adapters/pi.json").is_file())

    def test_python_fixture_creates_executable_profile_contract(self) -> None:
        if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
            self.skipTest("cross-repository bootstrap is template-only")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "python-derived"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/python-data.answers.json"),
                    "--target",
                    str(target),
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            contract = load_json(target / "harness/project.yaml")
            self.assertFalse(contract["template_mode"])
            self.assertEqual("python-data", contract["project"]["profile"])
            dry_run = subprocess.run(
                [sys.executable, str(target / "tools/run_quality.py"), "--dry-run"],
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stdout + dry_run.stderr)
            self.assertIn("project quality [typecheck]", dry_run.stdout)
            self.assertIn("project quality [unit]", dry_run.stdout)

    def test_adopt_preserves_existing_files_and_reports_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            (target / "README.md").write_text("existing readme\n", encoding="utf-8")
            (target / "AGENTS.md").write_text("# Existing rules\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/project_intake.py"),
                    "--answers",
                    str(ROOT / "harness/fixtures/intake.answers.json"),
                    "--target",
                    str(target),
                    "--mode",
                    "adopt",
                    "--apply",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=subprocess_environment(),
            )
            if not load_json(ROOT / "harness/project.yaml").get("template_mode", False):
                self.assertEqual(2, result.returncode)
                self.assertIn("cross-repository intake", result.stderr)
                return
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("existing readme\n", (target / "README.md").read_text())
            self.assertEqual("# Existing rules\n", (target / "AGENTS.md").read_text())
            self.assertTrue((target / "harness/project.yaml").is_file())
            self.assertTrue((target / ".pi/extensions/context-readiness.ts").is_file())
            gaps = (target / "docs/project/adoption-gaps.md").read_text()
            self.assertIn("README.md", gaps)
            self.assertIn("AGENTS.md", gaps)


if __name__ == "__main__":
    unittest.main()
