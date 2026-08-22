from pathlib import Path
import json
import shutil
import tempfile
import unittest

from tools.common import load_json, write_json
from tools.harness_check import check
from tools.project_intake import normalize_answer, render


ROOT = Path(__file__).resolve().parents[1]


def active_generic_copy(directory: str) -> Path:
    target = Path(directory) / "active"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".harness", ".venv", ".coverage", "__pycache__"),
    )
    base = load_json(target / "harness/project.yaml")
    base["template_mode"] = True
    base["project"]["profile"] = "generic"
    base["engineering"]["quality"]["required_checks"] = ["format_check", "lint", "unit"]
    raw = load_json(target / "harness/fixtures/intake.answers.json")
    answers = {
        key: normalize_answer(value, source="test", recorded_at="2026-08-22T00:00:00Z")
        for key, value in raw.items()
    }
    project, planning, missing = render(
        base,
        load_json(target / ".github/planning.json"),
        answers,
        profile_root=target / "harness/profiles",
    )
    if missing:
        raise AssertionError(f"active fixture has unresolved fields: {missing}")
    write_json(target / "harness/project.yaml", project)
    write_json(target / ".github/planning.json", planning)
    return target


class HarnessCheckTests(unittest.TestCase):
    def test_template_is_valid(self) -> None:
        result = check(ROOT)
        self.assertTrue(result.ok, result.errors)
        self.assertIn("7 skills", result.checked)
        self.assertIn("2 provider adapters", result.checked)
        self.assertIn("Pi adapter", result.checked)

    def test_pi_adapter_remains_thin_and_provider_neutral(self) -> None:
        settings = json.loads((ROOT / ".pi/settings.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "harness/adapters/pi.json").read_text(encoding="utf-8"))

        self.assertNotIn("packages", settings)
        self.assertNotIn("defaultModel", settings)
        self.assertEqual(["extensions/context-readiness.ts"], settings["extensions"])
        self.assertEqual("experimental", manifest["status"])
        self.assertEqual(
            "not supplied by Pi core adapter", manifest["capabilities"]["role_delegation"]
        )
        self.assertEqual(
            ".agents/skills",
            next(item for item in manifest["mappings"] if item["contract"] == "skills")[
                "canonical"
            ],
        )

    def test_active_contract_rejects_empty_exception_noop_and_symlink_lock(self) -> None:
        mutations = ("empty-exception", "noop", "symlink-lock")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                target = active_generic_copy(directory)
                project = load_json(target / "harness/project.yaml")
                if mutation == "empty-exception":
                    project["engineering"]["quality"]["dependency_lock"] = "not-applicable:"
                elif mutation == "noop":
                    project["engineering"]["command_contract"]["unit"] = "true"
                else:
                    lock = target / "locks/dependency.lock"
                    lock.parent.mkdir()
                    lock.symlink_to("/etc/hosts")
                    project["engineering"]["quality"]["dependency_lock"] = "locks/dependency.lock"
                write_json(target / "harness/project.yaml", project)
                result = check(target)
                self.assertFalse(result.ok)
                if mutation == "empty-exception":
                    self.assertTrue(any("requires a reason" in item for item in result.errors))
                elif mutation == "noop":
                    self.assertTrue(any("successful no-op" in item for item in result.errors))
                else:
                    self.assertTrue(any("symlink" in item for item in result.errors))


if __name__ == "__main__":
    unittest.main()
