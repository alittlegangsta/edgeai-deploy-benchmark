import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_task043_career_package.py"


class Task043CareerPackageTests(unittest.TestCase):
    def test_validator_passes(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status": "PASS"', result.stdout)

    def test_facts_include_authoritative_formal_rows(self):
        manifest = json.loads((ROOT / "results/final/authoritative_results.json").read_text(encoding="utf-8"))
        facts = (ROOT / "docs/career/FINAL_PROJECT_FACTS.md").read_text(encoding="utf-8")
        for row in manifest["authoritative_results"]["cross_platform_yolov5n_performance"]:
            self.assertIn(f"{row['metrics']['pipeline_ms']['mean']:.6f}", facts)
            self.assertIn(f"{row['metrics']['fps']:.6f}", facts)

    def test_npu_boundary_is_explicit(self):
        facts = (ROOT / "docs/career/FINAL_PROJECT_FACTS.md").read_text(encoding="utf-8")
        self.assertIn("Alnpu | ALHardNPU", facts)
        self.assertIn("FUNCTIONAL_CONTROL_ONLY", facts)
        self.assertIn("WAITING_FOR_VENDOR_INPUT", facts)
        self.assertIn("不能说 custom YOLOv5n 已经运行在 DR1 NPU", facts)
        self.assertIn("不能说 vendor face 与 YOLOv5n CPU/GPU 有任何倍数加速关系", facts)


if __name__ == "__main__":
    unittest.main()
