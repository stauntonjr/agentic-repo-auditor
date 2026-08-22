from pathlib import Path
from subprocess import CompletedProcess
import unittest
from unittest.mock import patch

from tools.common import load_json
from tools.github_planning import (
    diff_state,
    has_drift,
    project_bootstrap_plan,
    field_mismatches,
    flatten_pages,
    parse_json_values,
    read_live,
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

    def test_unaudited_project_fields_warn_without_false_drift(self) -> None:
        config = {
            "labels": [],
            "milestones": [],
            "fields": [{"name": "Status", "data_type": "SINGLE_SELECT"}],
            "project": {"views": []},
        }
        diff = diff_state(
            config,
            {
                "labels": [],
                "milestones": [],
                "fields": [],
                "project_audited": False,
            },
        )
        self.assertEqual([], diff["project"]["missing_fields"])
        self.assertEqual([], diff["project"]["mismatched_fields"])
        self.assertFalse(has_drift(diff))
        self.assertIn("not audited", diff["warnings"][0])

    def test_project_bootstrap_is_dry_run_and_includes_manual_views(self) -> None:
        config = load_json(ROOT / ".github/planning.json")
        plan = project_bootstrap_plan(config)
        self.assertTrue(plan["ok"])
        self.assertTrue(plan["dry_run"])
        self.assertEqual("create", plan["actions"][0]["action"])
        self.assertTrue(any(item["action"] == "ensure-field" for item in plan["actions"]))
        self.assertTrue(any(item["action"] == "manual-view" for item in plan["actions"]))

    def test_paginated_json_parser_accepts_zero_single_and_multiple_values(self) -> None:
        self.assertEqual([], parse_json_values("[]\n", command="gh api empty"))
        single = parse_json_values('[{"name":"one"}]\n', command="gh api single")
        self.assertEqual([{"name": "one"}], flatten_pages(single))
        multiple = parse_json_values(
            '[{"name":"one"}]\n[{"name":"two"}]\n',
            command="gh api multiple",
        )
        self.assertEqual([{"name": "one"}, {"name": "two"}], flatten_pages(multiple))

    def test_paginated_json_parser_rejects_empty_or_malformed_output(self) -> None:
        for output in ("", '[{"name":]'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(RuntimeError, "gh api labels"):
                    parse_json_values(output, command="gh api labels")

    def test_live_audit_uses_paginate_without_unsupported_slurp(self) -> None:
        config = {
            "repository": "stauntonjr/example",
            "project": {"number": None, "owner": "stauntonjr"},
        }
        command_results = [
            CompletedProcess([], 0, "stauntonjr\n", ""),
            CompletedProcess([], 0, "stauntonjr/example\n", ""),
        ]
        with (
            patch("tools.github_planning.run", side_effect=command_results),
            patch("tools.github_planning.gh_json", side_effect=[[], []]) as github_json,
        ):
            live = read_live(ROOT, config)

        self.assertEqual("stauntonjr/example", live["repository"])
        for call in github_json.call_args_list:
            self.assertIn("--paginate", call.args)
            self.assertNotIn("--slurp", call.args)


if __name__ == "__main__":
    unittest.main()
