import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "quota-handoff" / "scripts" / "check_usage.py"
GENERATE = ROOT / "quota-handoff" / "scripts" / "generate_handoff.py"


class QuotaHandoffTests(unittest.TestCase):
    def run_check(self, snapshot):
        result = subprocess.run(
            [sys.executable, str(CHECK), "--input", "-", "--threshold", "5"],
            input=json.dumps(snapshot), text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_low_remaining_triggers(self):
        result = self.run_check({"provider": "demo", "window": "weekly", "remaining_percent": 4.9})
        self.assertEqual(result["status"], "low")
        self.assertTrue(result["should_handoff"])

    def test_exact_threshold_does_not_trigger(self):
        result = self.run_check({"remaining": 5, "limit": 100})
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["should_handoff"])

    def test_missing_usage_is_unknown(self):
        result = self.run_check({"provider": "codex", "window": "weekly"})
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["should_handoff"])

    def test_used_limit_normalizes(self):
        result = self.run_check({"used": 96, "limit": 100})
        self.assertEqual(result["status"], "low")
        self.assertAlmostEqual(result["remaining_percent"], 4.0)

    def test_out_of_range_usage_is_unknown(self):
        result = self.run_check({"remaining_percent": 101})
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["should_handoff"])

    def test_generator_writes_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n\nTODO: verify deploy\n", encoding="utf-8")
            output = root / "HANDOFF.md"
            result = subprocess.run(
                [sys.executable, str(GENERATE), "--project-root", str(root), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            text = output.read_text(encoding="utf-8")
            self.assertIn("# Project Handoff", text)
            self.assertIn("TODO", text)


if __name__ == "__main__":
    unittest.main()
