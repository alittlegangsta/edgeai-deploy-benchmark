"""Focused offline tests for Task 039 video/camera evidence."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/validate_task039_video_camera.py"
SPEC = importlib.util.spec_from_file_location("validate_task039_video_camera", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class Task039VideoCameraTests(unittest.TestCase):
    def test_video_matrix_and_frame_accounting(self):
        report = VALIDATOR.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["frame_accounting"])

    def test_no_unbounded_queue_is_claimed(self):
        for name in ("pc_ort_fp32_video.json", "pc_ncnn_fp32_video.json", "pc_tensorrt_fp16_video.json"):
            evidence = VALIDATOR.load(name)
            self.assertEqual(evidence["queue"]["mode"], "synchronous")
            self.assertEqual(evidence["queue"]["capacity"], 0)

    def test_fp16_single_image_diagnostic_remains_scoped(self):
        evidence = VALIDATOR.load("pc_tensorrt_fp16_video.json")
        self.assertEqual(evidence["first_frame_golden"]["status"], "NOT_REQUESTED")
        self.assertEqual(
            VALIDATOR.load("validation.json")["tensorrt_fp16_diagnostic"]["source"],
            "results/evidence/037/correctness.json",
        )

    def test_board_camera_int8_run_is_bounded_and_explicit(self):
        evidence = VALIDATOR.load("dr_camera_ncnn_int8.json")
        self.assertEqual(evidence["mode"], "camera")
        self.assertEqual(evidence["backend"]["precision"], "int8")
        self.assertEqual(evidence["backend"]["fallback"], "none")
        self.assertEqual(evidence["counts"]["processed_frames"], 3)
        self.assertEqual(evidence["queue"]["capacity"], 0)


if __name__ == "__main__":
    unittest.main()
