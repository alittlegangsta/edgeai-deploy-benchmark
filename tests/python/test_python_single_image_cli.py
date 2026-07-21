from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from edgeai_benchmark.postprocess import (
    DetectionConfig,
    PostprocessError,
    box_iou,
    decode_yolov5_output,
)
from edgeai_benchmark.visualize import draw_detections


CLASS_NAMES = ["class-zero", "class-one"]
LETTERBOX = {
    "scale": 0.5,
    "padding": {"left": 0, "top": 80, "right": 0, "bottom": 80},
    "original_size": {"width": 1280, "height": 960},
}
CONFIG = DetectionConfig(
    confidence_threshold=0.25,
    iou_threshold=0.45,
    class_aware_nms=True,
    max_detections=1000,
)


def raw_output(rows: list[list[float]]) -> np.ndarray:
    return np.asarray([rows], dtype=np.float32)


class PythonSingleImageTest(unittest.TestCase):
    def test_iou_uses_continuous_xyxy_geometry(self) -> None:
        value = box_iou(
            np.array([0.0, 0.0, 10.0, 10.0], dtype=np.float32),
            np.array([[5.0, 5.0, 15.0, 15.0]], dtype=np.float32),
        )
        self.assertAlmostEqual(float(value[0]), 25.0 / 175.0, places=6)

    def test_combined_confidence_xywh_mapping_and_clipping(self) -> None:
        result = decode_yolov5_output(
            raw_output([[320.0, 320.0, 800.0, 800.0, 0.8, 0.25, 0.75]]),
            CLASS_NAMES,
            LETTERBOX,
            CONFIG,
        )
        detection = result["detections"][0]
        self.assertEqual(detection["class_id"], 1)
        self.assertEqual(detection["objectness"], 0.8)
        self.assertEqual(detection["class_score"], 0.75)
        self.assertEqual(detection["confidence"], 0.6)
        self.assertEqual(detection["box_xyxy_source"], [0.0, 0.0, 1280.0, 960.0])

    def test_class_aware_nms_suppresses_same_class_only(self) -> None:
        result = decode_yolov5_output(
            raw_output(
                [
                    [100.0, 100.0, 50.0, 50.0, 0.9, 0.9, 0.1],
                    [101.0, 101.0, 50.0, 50.0, 0.8, 0.9, 0.1],
                    [100.0, 100.0, 50.0, 50.0, 0.85, 0.1, 0.9],
                ]
            ),
            CLASS_NAMES,
            LETTERBOX,
            CONFIG,
        )
        self.assertEqual(result["threshold_candidate_count"], 3)
        self.assertEqual(result["nms_candidate_count"], 2)
        self.assertEqual([item["candidate_index"] for item in result["detections"]], [0, 2])

    def test_threshold_can_produce_explicit_empty_result(self) -> None:
        result = decode_yolov5_output(
            raw_output([[100.0, 100.0, 20.0, 20.0, 0.5, 0.4, 0.1]]),
            CLASS_NAMES,
            LETTERBOX,
            CONFIG,
        )
        self.assertEqual(result["threshold_candidate_count"], 0)
        self.assertEqual(result["detections"], [])

    def test_non_finite_raw_output_is_rejected(self) -> None:
        raw = raw_output([[100.0, 100.0, 20.0, 20.0, np.nan, 0.9, 0.1]])
        with self.assertRaisesRegex(PostprocessError, "non-finite"):
            decode_yolov5_output(raw, CLASS_NAMES, LETTERBOX, CONFIG)

    def test_visualizer_does_not_mutate_source(self) -> None:
        source = np.zeros((100, 100, 3), dtype=np.uint8)
        original = source.copy()
        detections = [
            {
                "class_id": 0,
                "class_name": "class-zero",
                "confidence": 0.9,
                "box_xyxy_source": [10.0, 20.0, 80.0, 90.0],
            }
        ]
        output = draw_detections(source, detections)
        np.testing.assert_array_equal(source, original)
        self.assertFalse(np.array_equal(output, original))

    def test_invalid_cli_input_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "input_size": [640, 640],
                        "confidence_threshold": 0.25,
                        "iou_threshold": 0.45,
                        "class_aware_nms": True,
                        "max_detections": 1000,
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "python/apps/ort_image.py",
                    "--model",
                    str(root / "missing.onnx"),
                    "--manifest",
                    "models/yolov5n-v7.0/manifest.json",
                    "--config",
                    str(config_path),
                    "--image",
                    "data/samples/images/pc_reference.jpg",
                    "--output-image",
                    str(root / "output.png"),
                    "--output-json",
                    str(root / "output.json"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": "python"},
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ONNX model is missing", completed.stderr)


if __name__ == "__main__":
    unittest.main()
