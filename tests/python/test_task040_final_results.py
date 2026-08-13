import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_task040_final_results.py"
MANIFEST = ROOT / "results" / "final" / "authoritative_results.json"


class Task040FinalResultsTests(unittest.TestCase):
    def test_validator_passes(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Task 040 final results validation: PASS", result.stdout)

    def test_formal_rows_and_scope_boundaries(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows = manifest["authoritative_results"]["cross_platform_yolov5n_performance"]
        self.assertEqual({row["id"] for row in rows}, {"pc_ort_fp32", "rtx4060ti_tensorrt_fp32", "rtx4060ti_tensorrt_fp16", "dr1_ncnn_fp32", "dr1_ncnn_eq"})
        self.assertTrue(all(row["classification"] == "formal_benchmark" for row in rows))
        self.assertFalse(manifest["provenance_policy"]["cross_platform_speedup_claimed"])
        integration = manifest["integration_evidence"]
        self.assertTrue(all(item["not_formal_benchmark"] for item in integration))
        self.assertTrue(any(item["classification"] == "CAMERA_INTEGRATION_EVIDENCE" for item in integration))

    def test_accuracy_and_npu_statuses(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        matrix = {item["backend"]: item["status"] for item in manifest["authoritative_results"]["deployment_capability_matrix"]}
        self.assertEqual(matrix["Alnpu | ALHardNPU"], "FUNCTIONAL_CONTROL_ONLY")
        self.assertEqual(matrix["Alnpu"], "WAITING_FOR_VENDOR_INPUT")
        for item in manifest["authoritative_results"]["accuracy_performance_tradeoff"]:
            self.assertEqual(item["accuracy"]["gate"]["status"], "PASS")

    def test_tensorrt_timing_boundaries_are_distinct(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in manifest["authoritative_results"]["cross_platform_yolov5n_performance"]}
        fp32 = rows["rtx4060ti_tensorrt_fp32"]["metrics"]
        fp16 = rows["rtx4060ti_tensorrt_fp16"]["metrics"]
        self.assertAlmostEqual(fp32["backend_inference_ms"]["mean"], 3.71244466, places=8)
        self.assertAlmostEqual(fp16["backend_inference_ms"]["mean"], 3.71610421, places=8)
        self.assertAlmostEqual(fp32["gpu_execution_ms"]["mean"], 1.6742607927322388, places=8)
        self.assertAlmostEqual(fp16["gpu_execution_ms"]["mean"], 1.37037856, places=8)
        self.assertLess(fp16["gpu_execution_ms"]["mean"], fp32["gpu_execution_ms"]["mean"])
        self.assertGreater(fp16["pipeline_ms"]["mean"], fp32["pipeline_ms"]["mean"])
        policy = manifest["timing_boundary_policy"]
        self.assertEqual(policy["cross_backend_main_field"], "backend_inference_ms")
        self.assertAlmostEqual(policy["task038_integration_values_ms"]["fp32_backend_call"], 4.2555388, places=7)
        self.assertAlmostEqual(policy["task038_integration_values_ms"]["fp16_backend_call"], 7.3970642, places=7)


if __name__ == "__main__":
    unittest.main()
