import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_task030_benchmark_consolidation.py"


class Task030ConsolidationTests(unittest.TestCase):
    def test_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Task 030 consolidation validation: PASS", result.stdout)

    def test_required_evidence_and_npu_boundary(self):
        evidence = ROOT / "results" / "evidence" / "030"
        for name in (
            "benchmark_contract.json",
            "pc_ort_benchmark.json",
            "arm_ncnn_benchmark.json",
            "backend_status_matrix.json",
            "benchmark_comparison.json",
            "validation.json",
        ):
            with self.subTest(name=name):
                self.assertTrue((evidence / name).is_file())
        matrix = json.loads((evidence / "backend_status_matrix.json").read_text())
        statuses = {entry["backend"]: entry["status"] for entry in matrix["entries"]}
        self.assertEqual(statuses["DR1 vendor face NPU control"], "FUNCTIONAL_CONTROL_ONLY")
        self.assertEqual(statuses["DR1 YOLOv5n NPU"], "NOT_BENCHMARKED")

    def test_p95_is_present_and_resources_are_explicit(self):
        evidence = ROOT / "results" / "evidence" / "030"
        for name in ("pc_ort_benchmark.json", "arm_ncnn_benchmark.json"):
            row = json.loads((evidence / name).read_text())
            self.assertIn("p95_ms", row["stages"]["pipeline"])
            self.assertIn("cpu_utilization_one_core_basis_percent", row["resources"])
            self.assertIn("peak_rss_kib", row["resources"])
            self.assertIn("cpu_frequency_khz", row["sampled_frequency_temperature"])
            self.assertIn("temperature_millicelsius", row["sampled_frequency_temperature"])


if __name__ == "__main__":
    unittest.main()
