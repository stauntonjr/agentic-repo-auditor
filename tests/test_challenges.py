from pathlib import Path
import sys
import unittest

from tools.run_challenges import replay, validate_challenge


class ChallengeTests(unittest.TestCase):
    def test_current_oracle_passes_and_known_bad_fails_for_signature(self) -> None:
        challenge = {
            "id": "C001",
            "title": "Example",
            "escaped_defect": {"description": "example"},
            "affected_surfaces": ["public-interface"],
            "oracle": {
                "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                "success_exit_code": 0,
            },
            "known_bad": {
                "argv": [
                    sys.executable,
                    "-c",
                    "import sys; print('semantic mismatch'); raise SystemExit(1)",
                ]
            },
            "expected_failure": {"exit_code": 1, "signature": "semantic mismatch"},
        }
        self.assertEqual([], validate_challenge(challenge, Path("C001.json")))
        result = replay(Path.cwd(), challenge)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
