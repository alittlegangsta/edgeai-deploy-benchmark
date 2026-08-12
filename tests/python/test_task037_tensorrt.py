"""Offline validation for Task 037 TensorRT evidence."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/validate_task037_tensorrt.py"
SPEC = importlib.util.spec_from_file_location("validate_task037_tensorrt", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class Task037TensorRTEvidenceTests(unittest.TestCase):
    def test_evidence_is_self_consistent(self):
        report = VALIDATOR.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["fp32"], "PASS_TARGET")
        self.assertEqual(report["fp16"], "TENSORRT_FP16_READY")

    def test_fp16_single_image_diagnostic_is_retained(self):
        evidence = VALIDATOR.load("correctness.json")
        fp16 = evidence["results"]["fp16"]
        self.assertIn("SECONDARY_DIAGNOSTIC", fp16["status"])
        self.assertGreater(fp16["maximum_confidence_delta"], 0.001)

    def test_fp16_coco_gate_is_accepted(self):
        evidence = VALIDATOR.load("coco_accuracy.json")
        self.assertEqual(evidence["comparison"]["gate"], "PASS")
        self.assertLessEqual(abs(evidence["comparison"]["fp16_delta_mAP50"]), 0.01)
        self.assertLessEqual(abs(evidence["comparison"]["fp16_delta_mAP50_95"]), 0.01)


if __name__ == "__main__":
    unittest.main()
