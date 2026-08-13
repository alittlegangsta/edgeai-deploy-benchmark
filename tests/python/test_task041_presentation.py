import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_task041_presentation.py"


class Task041PresentationTests(unittest.TestCase):
    def test_presentation_validator_passes(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status": "PASS"', result.stdout)

    def test_authoritative_rows_are_rendered(self):
        manifest = json.loads((ROOT / "results/final/authoritative_results.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        rows = manifest["authoritative_results"]["cross_platform_yolov5n_performance"]
        self.assertEqual(len(rows), 5)
        for row in rows:
            value = f"{row['metrics']['pipeline_ms']['mean']:.6f}"
            self.assertIn(value, readme)

    def test_npu_scope_is_not_overclaimed(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Alnpu | ALHardNPU", text)
        self.assertIn("WAITING_FOR_VENDOR_INPUT", text)
        self.assertIn("not a YOLOv5n performance result", text)


if __name__ == "__main__":
    unittest.main()
