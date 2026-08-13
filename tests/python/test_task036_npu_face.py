"""Offline tests for the Task 036 vendor-face closed-loop evidence."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/vendor/validate_task036_npu_face.py"
SPEC = importlib.util.spec_from_file_location("validate_task036_npu_face", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class Task036NpuFaceEvidenceTests(unittest.TestCase):
    def test_real_evidence_passes(self):
        report = VALIDATOR.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["assignment_count"], 1)
        self.assertEqual(report["benchmark_repeats"], 10)

    def test_scope_does_not_claim_yolov5n_benchmark(self):
        manifest = VALIDATOR.load_json(VALIDATOR.EVIDENCE / "artifact_manifest.json")
        self.assertEqual(manifest["scope"]["yolov5n_comparison"], "NOT_PERFORMED")


if __name__ == "__main__":
    unittest.main()
