from pathlib import Path
import unittest

from tools.common import load_json
from tools.github_planning import (
    diff_state,
    has_drift,
    project_bootstrap_plan,
    field_mismatches,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class GitHubPlanningTests(unittest.TestCase):
    def test_contract_is_valid(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        self.assertEqual([], validate_contract(config))

    def test_diff_is_non_destructive_and_precise(self) -> None:
        config = {
            "labels": [{"name": "type:feature", "color": "ffffff", "description": "feature"}],
            "milestones": [{"title": "M0", "description": "zero"}],
            "fields": [{"name": "Status", "data_type": "SINGLE_SELECT"}],
            "project": {"views": []},
        }
        live = {
            "labels": [{"name": "type:feature", "color": "000000", "description": "old"}],
            "milestones": [],
            "fields": [{"name": "Status"}],
            "project_audited": True,
        }
        diff = diff_state(config, live)
        self.assertEqual(1, len(diff["labels"]["update"]))
        self.assertEqual([{"title": "M0", "description": "zero"}], diff["milestones"]["create"])
        self.assertEqual([], diff["project"]["missing_fields"])
        self.assertTrue(has_drift(diff))
        self.assertNotIn("delete", diff["labels"])

    def test_field_options_are_audited(self) -> None:
        desired = [
            {
                "name": "Status",
                "data_type": "SINGLE_SELECT",
                "options": ["Todo", "In Progress", "Done"],
            }
        ]
        live = [
            {
                "name": "Status",
                "type": "ProjectV2SingleSelectField",
                "options": [{"name": "Todo"}, {"name": "Done"}],
            }
        ]
        self.assertEqual("Status", field_mismatches(desired, live)[0]["name"])

    def test_project_bootstrap_is_dry_run_and_includes_manual_views(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        plan = project_bootstrap_plan(config)
        self.assertTrue(plan["ok"])
        self.assertTrue(plan["dry_run"])
        self.assertEqual("create", plan["actions"][0]["action"])
        self.assertTrue(any(item["action"] == "ensure-field" for item in plan["actions"]))
        self.assertTrue(any(item["action"] == "manual-view" for item in plan["actions"]))


if __name__ == "__main__":
    unittest.main()
