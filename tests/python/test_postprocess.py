from __future__ import annotations

import unittest

import numpy as np

from edgeai_benchmark.postprocess import (
    DetectionConfig,
    box_iou,
    class_aware_nms,
    decode_yolov5_output,
    restore_and_clip_box,
)


CLASS_NAMES = ["zero", "one"]
LETTERBOX = {
    "scale": 0.5,
    "padding": {"left": 0, "top": 80, "right": 0, "bottom": 80},
    "original_size": {"width": 1280, "height": 960},
}
CONFIG = DetectionConfig(0.25, 0.45, True, 1000)


class IouTest(unittest.TestCase):
    def test_identical_boxes(self) -> None:
        box = np.array([1.0, 2.0, 11.0, 12.0], dtype=np.float32)
        self.assertEqual(float(box_iou(box, box[np.newaxis, :])[0]), 1.0)

    def test_disjoint_boxes(self) -> None:
        box = np.array([0.0, 0.0, 10.0, 10.0], dtype=np.float32)
        other = np.array([[20.0, 20.0, 30.0, 30.0]], dtype=np.float32)
        self.assertEqual(float(box_iou(box, other)[0]), 0.0)

    def test_partial_overlap(self) -> None:
        box = np.array([0.0, 0.0, 10.0, 10.0], dtype=np.float32)
        other = np.array([[5.0, 5.0, 15.0, 15.0]], dtype=np.float32)
        self.assertAlmostEqual(float(box_iou(box, other)[0]), 25.0 / 175.0, places=6)

    def test_degenerate_box_has_zero_iou(self) -> None:
        box = np.array([5.0, 5.0, 5.0, 10.0], dtype=np.float32)
        other = np.array([[0.0, 0.0, 10.0, 10.0]], dtype=np.float32)
        self.assertEqual(float(box_iou(box, other)[0]), 0.0)


class NmsTest(unittest.TestCase):
    def test_same_class_suppression_and_different_class_retention(self) -> None:
        boxes = np.array(
            [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 11.0, 11.0], [0.0, 0.0, 10.0, 10.0]],
            dtype=np.float32,
        )
        kept = class_aware_nms(
            boxes,
            np.array([0.9, 0.8, 0.85], dtype=np.float32),
            np.array([0, 0, 1], dtype=np.int64),
            np.array([5, 6, 7], dtype=np.int64),
            0.45,
            1000,
        )
        self.assertEqual(kept, [0, 2])

    def test_tie_order_is_candidate_then_maximum_limit(self) -> None:
        boxes = np.array(
            [[0.0, 0.0, 1.0, 1.0], [10.0, 10.0, 11.0, 11.0]],
            dtype=np.float32,
        )
        kept = class_aware_nms(
            boxes,
            np.array([0.5, 0.5], dtype=np.float32),
            np.array([0, 0], dtype=np.int64),
            np.array([9, 3], dtype=np.int64),
            0.45,
            1,
        )
        self.assertEqual(kept, [1])

    def test_iou_equal_to_threshold_is_retained(self) -> None:
        boxes = np.array(
            [[0.0, 0.0, 10.0, 10.0], [0.0, 0.0, 10.0, 10.0]],
            dtype=np.float32,
        )
        kept = class_aware_nms(
            boxes,
            np.array([0.9, 0.8], dtype=np.float32),
            np.array([0, 0], dtype=np.int64),
            np.array([0, 1], dtype=np.int64),
            1.0,
            1000,
        )
        self.assertEqual(kept, [0, 1])

    def test_empty_nms_input(self) -> None:
        kept = class_aware_nms(
            np.empty((0, 4), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0,), dtype=np.int64),
            np.empty((0,), dtype=np.int64),
            0.45,
            1000,
        )
        self.assertEqual(kept, [])


class MappingAndDecodeTest(unittest.TestCase):
    def test_forward_then_inverse_mapping(self) -> None:
        source = np.array([200.0, 100.0, 600.0, 500.0], dtype=np.float32)
        input_box = source.copy()
        input_box[[0, 2]] = input_box[[0, 2]] * 0.5
        input_box[[1, 3]] = input_box[[1, 3]] * 0.5 + 80.0
        restored = restore_and_clip_box(input_box, LETTERBOX)
        np.testing.assert_allclose(restored, source)

    def test_inverse_mapping_clips_to_source_bounds(self) -> None:
        restored = restore_and_clip_box(
            np.array([-10.0, -20.0, 700.0, 700.0], dtype=np.float32),
            LETTERBOX,
        )
        np.testing.assert_allclose(restored, [0.0, 0.0, 1280.0, 960.0])

    def test_confidence_threshold_is_inclusive(self) -> None:
        raw = np.array(
            [[[100.0, 100.0, 20.0, 20.0, 0.5, 0.5, 0.1]]],
            dtype=np.float32,
        )
        result = decode_yolov5_output(raw, CLASS_NAMES, LETTERBOX, CONFIG)
        self.assertEqual(result["threshold_candidate_count"], 1)
        self.assertEqual(result["detections"][0]["confidence"], 0.25)

    def test_empty_raw_candidates_are_preserved_as_empty(self) -> None:
        raw = np.empty((1, 0, 7), dtype=np.float32)
        result = decode_yolov5_output(raw, CLASS_NAMES, LETTERBOX, CONFIG)
        self.assertEqual(result["raw_candidate_count"], 0)
        self.assertEqual(result["detections"], [])


if __name__ == "__main__":
    unittest.main()
