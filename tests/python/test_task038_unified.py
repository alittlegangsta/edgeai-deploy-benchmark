"""Focused offline tests for Task 038 unified C++ application evidence."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/validate_task038_unified.py"
SPEC = importlib.util.spec_from_file_location("validate_task038_unified", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class Task038UnifiedTests(unittest.TestCase):
    def test_unified_evidence_is_self_consistent(self):
        report = VALIDATOR.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["no_fallback"])

    def test_three_fp32_backends_pass_the_frozen_contract(self):
        runs = VALIDATOR.load("backend_runs.json")["runs"]
        for name in ("ort_fp32", "ncnn_fp32", "tensorrt_fp32"):
            self.assertEqual(runs[name]["exit_code"], 0)
            self.assertEqual(runs[name]["correctness"]["status"], "PASS_TARGET")
            self.assertEqual(runs[name]["correctness"]["detections"], 5)

    def test_fp16_secondary_diagnostic_is_not_silently_called_strict_pass(self):
        fp16 = VALIDATOR.load("backend_runs.json")["runs"]["tensorrt_fp16"]
        self.assertIn("SECONDARY_SINGLE_GOLDEN_FAIL", fp16["correctness"]["status"])
        self.assertGreater(fp16["correctness"]["single_image_confidence_delta"], 0.001)


if __name__ == "__main__":
    unittest.main()
