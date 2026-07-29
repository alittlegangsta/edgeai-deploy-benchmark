"""Synthetic tests for the Task 020 independent video validator."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest

import cv2
import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/vendor/validate_anlogic_arm_video.py"
SPEC = importlib.util.spec_from_file_location("validate_anlogic_arm_video", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def detections() -> list[dict]:
    values = []
    for rank, (class_id, class_name) in enumerate(
        ((66, "keyboard"), (62, "tv"), (41, "cup"), (64, "mouse"), (64, "mouse")),
        1,
    ):
        left = 100.0 + rank * 20.0
        top = 120.0 + rank * 15.0
        values.append(
            {
                "rank": rank,
                "class_id": class_id,
                "class_name": class_name,
                "confidence": 0.9 - rank * 0.1,
                "box_xyxy_source": [left, top, left + 50.0, top + 40.0],
            }
        )
    return values


class AnlogicArmVideoTests(unittest.TestCase):
    def test_user_video_approval_is_preserved(self) -> None:
        validation = {}
        VALIDATOR.preserve_human_review(
            validation,
            {
                "human_video_review": "PASS",
                "human_review_source": "user",
                "candidate_approved": True,
                "human_review_recorded_at": "2026-07-29T11:18:31+08:00",
                "human_review_recorded_at_basis":
                    "WSL approval record time; not board run time",
            },
        )
        self.assertEqual(validation["human_video_review"], "PASS")
        self.assertEqual(validation["human_review_source"], "user")
        self.assertTrue(validation["candidate_approved"])

    def test_incomplete_video_approval_is_rejected(self) -> None:
        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.preserve_human_review(
                {},
                {
                    "human_video_review": "PASS",
                    "human_review_source": "user",
                    "candidate_approved": False,
                },
            )

    def test_detection_comparison_passes(self) -> None:
        minimum_iou, maximum_delta = VALIDATOR.compare_detections(
            detections(), detections()
        )
        self.assertEqual(minimum_iou, 1.0)
        self.assertEqual(maximum_delta, 0.0)

    def test_detection_comparison_rejects_class_change(self) -> None:
        candidate = detections()
        candidate[0] = dict(candidate[0], class_name="person", class_id=0)
        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.compare_detections(detections(), candidate)

    def test_detection_comparison_rejects_invalid_box(self) -> None:
        candidate = detections()
        candidate[0] = dict(candidate[0], box_xyxy_source=[10.0, 10.0, 5.0, 20.0])
        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.compare_detections(detections(), candidate)

    def test_decode_and_sample_video(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            video = root / "sample.avi"
            writer = cv2.VideoWriter(
                str(video),
                cv2.VideoWriter_fourcc(*"MJPG"),
                VALIDATOR.EXPECTED_FPS,
                (VALIDATOR.EXPECTED_WIDTH, VALIDATOR.EXPECTED_HEIGHT),
            )
            self.assertTrue(writer.isOpened())
            frame = np.full(
                (VALIDATOR.EXPECTED_HEIGHT, VALIDATOR.EXPECTED_WIDTH, 3),
                127,
                dtype=np.uint8,
            )
            for _ in range(VALIDATOR.EXPECTED_FRAMES):
                writer.write(frame)
            writer.release()
            metadata, samples = VALIDATOR.decode_and_sample_video(video, root / "images")
            self.assertEqual(metadata["decoded_frame_count"], 30)
            self.assertEqual(set(samples), {"0", "15", "29"})


if __name__ == "__main__":
    unittest.main()
