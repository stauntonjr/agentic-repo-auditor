from pathlib import Path
import unittest

from tools.common import load_json
from tools.evaluate_harness import forward_prompts, validate_scenarios


ROOT = Path(__file__).resolve().parents[1]


class EvaluateHarnessTests(unittest.TestCase):
    def test_scenarios_route_to_existing_skills(self) -> None:
        payload = load_json(ROOT / "harness/evals/scenarios.json")
        self.assertEqual([], validate_scenarios(ROOT, payload))
        prompts = forward_prompts(ROOT, payload)
        self.assertEqual(len(payload["scenarios"]), len(prompts))
        self.assertIsNone(prompts[-1]["skill_path"])
