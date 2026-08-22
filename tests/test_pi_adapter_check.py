import unittest

from tools.pi_adapter_check import REQUIRED_COMMANDS, command_errors


class PiAdapterCheckTests(unittest.TestCase):
    def test_expected_command_set_passes(self) -> None:
        payload = {
            "data": {
                "commands": [
                    {"name": name, "source": source} for name, source in REQUIRED_COMMANDS.items()
                ]
            }
        }
        self.assertEqual([], command_errors(payload))

    def test_missing_or_wrong_command_is_reported(self) -> None:
        payload = {"data": {"commands": [{"name": "harness-loop", "source": "skill"}]}}
        errors = command_errors(payload)
        self.assertIn("missing prompt command: harness-loop", errors)
        self.assertIn("missing extension command: harness-adapter", errors)


if __name__ == "__main__":
    unittest.main()
