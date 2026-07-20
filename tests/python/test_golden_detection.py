from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest

import numpy as np

from edgeai_benchmark.postprocess import box_iou


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = ROOT / "tests/fixtures/reference_inputs.json"
GOLDEN_PATH = ROOT / "tests/fixtures/python_ort_golden.json"
REPLAY_PATH = ROOT / "results/evidence/005/python_ort_replay.json"


class GoldenValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GoldenValidationError(f"failed to load JSON {path}: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise GoldenValidationError(f"required artifact is missing or empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_reference_hashes(reference: dict[str, object]) -> None:
    model = reference["model"]
    image = reference["image"]
    config = reference["configuration"]
    approved = reference["approved_task_004"]
    checks = [
        (model["manifest_path"], model["manifest_sha256"]),
        (model["source_weights_path"], model["source_weights_sha256"]),
        (model["onnx_path"], model["onnx_sha256"]),
        (image["path"], image["sha256"]),
        (config["path"], config["sha256"]),
        (approved["annotated_image_path"], approved["annotated_image_sha256"]),
        (approved["evidence_path"], approved["evidence_sha256"]),
    ]
    for relative_path, expected_hash in checks:
        actual_hash = sha256_file(ROOT / relative_path)
        if actual_hash != expected_hash:
            raise GoldenValidationError(
                f"SHA256 mismatch for {relative_path}: "
                f"expected {expected_hash}, observed {actual_hash}"
            )


def validate_result_schema(
    result: dict[str, object],
    reference: dict[str, object],
) -> None:
    model = reference["model"]
    image = reference["image"]
    config = reference["configuration"]
    if result["model"]["sha256"] != model["onnx_sha256"]:
        raise GoldenValidationError("replay model hash differs from the pinned ONNX")
    if result["source_image"]["sha256"] != image["sha256"]:
        raise GoldenValidationError("replay image hash differs from the pinned image")
    if result["source_image"]["shape_bgr"] != [image["height"], image["width"], 3]:
        raise GoldenValidationError("replay source dimensions are invalid")
    if result["configuration"] != config["values"]:
        raise GoldenValidationError("replay configuration differs from the pinned values")
    if result["configuration_file"]["sha256"] != config["sha256"]:
        raise GoldenValidationError("replay configuration hash differs")
    detections = result.get("detections")
    if not isinstance(detections, list):
        raise GoldenValidationError("replay detections are not a list")
    manifest = load_json(ROOT / model["manifest_path"])
    class_names = manifest["onnx"]["contract"]["class_names"]
    previous_confidence = math.inf
    for expected_rank, detection in enumerate(detections, start=1):
        if detection.get("rank") != expected_rank:
            raise GoldenValidationError("detection ranks are not contiguous and ordered")
        class_id = detection.get("class_id")
        if not isinstance(class_id, int) or not 0 <= class_id < len(class_names):
            raise GoldenValidationError("detection class ID is invalid")
        if detection.get("class_name") != class_names[class_id]:
            raise GoldenValidationError("detection class name does not match class ID")
        confidence = detection.get("confidence")
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
            raise GoldenValidationError("detection confidence is not finite")
        if not 0.0 <= confidence <= 1.0 or confidence > previous_confidence:
            raise GoldenValidationError("detection confidences are invalid or unordered")
        previous_confidence = confidence
        box = detection.get("box_xyxy_source")
        if not isinstance(box, list) or len(box) != 4:
            raise GoldenValidationError("detection box is not xyxy")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in box):
            raise GoldenValidationError("detection box contains non-finite values")
        x1, y1, x2, y2 = box
        if not (0.0 <= x1 < x2 <= image["width"]):
            raise GoldenValidationError("detection x coordinates are invalid")
        if not (0.0 <= y1 < y2 <= image["height"]):
            raise GoldenValidationError("detection y coordinates are invalid")


def match_golden(
    golden: dict[str, object],
    replay: dict[str, object],
) -> list[dict[str, float | int]]:
    expected = golden["detections"]
    actual = replay["detections"]
    if len(expected) != len(actual):
        raise GoldenValidationError(
            f"detection count mismatch: expected {len(expected)}, observed {len(actual)}"
        )
    tolerances = golden["tolerances"]
    minimum_iou = tolerances["minimum_class_matched_iou"]
    maximum_confidence_delta = tolerances["maximum_absolute_confidence_difference"]
    unmatched = set(range(len(actual)))
    comparisons = []
    for expected_detection in expected:
        candidates = [
            index
            for index in unmatched
            if actual[index]["class_id"] == expected_detection["class_id"]
            and actual[index]["class_name"] == expected_detection["class_name"]
        ]
        if not candidates:
            raise GoldenValidationError(
                f"no unmatched replay detection for class {expected_detection['class_name']}"
            )
        expected_box = np.asarray(expected_detection["box_xyxy_source"], dtype=np.float32)
        candidate_boxes = np.asarray(
            [actual[index]["box_xyxy_source"] for index in candidates],
            dtype=np.float32,
        )
        overlaps = box_iou(expected_box, candidate_boxes)
        best_position = int(np.argmax(overlaps))
        actual_index = candidates[best_position]
        overlap = float(overlaps[best_position])
        confidence_delta = abs(
            float(actual[actual_index]["confidence"])
            - float(expected_detection["confidence"])
        )
        if overlap < minimum_iou:
            raise GoldenValidationError(
                f"class-matched IoU {overlap} is below {minimum_iou}"
            )
        if confidence_delta > maximum_confidence_delta:
            raise GoldenValidationError(
                f"confidence delta {confidence_delta} exceeds {maximum_confidence_delta}"
            )
        unmatched.remove(actual_index)
        comparisons.append(
            {
                "golden_rank": expected_detection["rank"],
                "replay_rank": actual[actual_index]["rank"],
                "class_id": expected_detection["class_id"],
                "iou": overlap,
                "absolute_confidence_difference": confidence_delta,
            }
        )
    if unmatched:
        raise GoldenValidationError(f"unmatched replay detections remain: {sorted(unmatched)}")
    return comparisons


class GoldenDetectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = load_json(REFERENCE_PATH)
        self.golden = load_json(GOLDEN_PATH)

    def test_fixed_input_hashes_and_approved_artifact(self) -> None:
        validate_reference_hashes(self.reference)
        self.assertEqual(
            self.golden["approved_artifact"]["sha256"],
            self.reference["approved_task_004"]["evidence_sha256"],
        )
        self.assertEqual(
            self.reference["approved_task_004"]["human_review_status"],
            "APPROVED_WITH_KNOWN_MODEL_FALSE_POSITIVE",
        )

    def test_replay_schema_and_golden_match(self) -> None:
        replay = load_json(REPLAY_PATH)
        validate_result_schema(replay, self.reference)
        comparisons = match_golden(self.golden, replay)
        self.assertEqual(len(comparisons), 5)
        self.assertTrue(all(item["iou"] >= 0.99 for item in comparisons))
        self.assertTrue(
            all(item["absolute_confidence_difference"] <= 0.001 for item in comparisons)
        )
        self.assertEqual(
            sha256_file(ROOT / replay["output_image"]["path"]),
            self.reference["approved_task_004"]["annotated_image_sha256"],
        )

    def test_hash_mismatch_fails(self) -> None:
        changed = deepcopy(self.reference)
        changed["model"]["onnx_sha256"] = "0" * 64
        with self.assertRaisesRegex(GoldenValidationError, "SHA256 mismatch"):
            validate_reference_hashes(changed)

    def test_malformed_result_fails(self) -> None:
        replay = load_json(REPLAY_PATH)
        malformed = deepcopy(replay)
        malformed["detections"][0]["box_xyxy_source"] = [10.0, 10.0, 5.0, 5.0]
        with self.assertRaisesRegex(GoldenValidationError, "coordinates are invalid"):
            validate_result_schema(malformed, self.reference)


if __name__ == "__main__":
    unittest.main()
