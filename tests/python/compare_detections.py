#!/usr/bin/env python3
"""Compare real C++ ORT detections with the approved Python semantic golden."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


FROZEN_MINIMUM_IOU = 0.99
FROZEN_MAXIMUM_CONFIDENCE_DELTA = 0.001


class ComparisonError(RuntimeError):
    """Raised when detection artifacts cannot be compared safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--min-iou", required=True, type=float)
    parser.add_argument("--max-confidence-delta", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ComparisonError(f"failed to load JSON {path}: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ComparisonError(f"required artifact is missing or empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_detection(detection: dict[str, Any]) -> None:
    if not isinstance(detection.get("class_id"), int) or detection["class_id"] < 0:
        raise ComparisonError("detection class_id is invalid")
    if not isinstance(detection.get("class_name"), str) or not detection["class_name"]:
        raise ComparisonError("detection class_name is invalid")
    confidence = detection.get("confidence")
    if not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
        raise ComparisonError("detection confidence is not finite")
    if not 0.0 <= confidence <= 1.0:
        raise ComparisonError("detection confidence is outside [0, 1]")
    box = detection.get("box_xyxy_source")
    if (
        not isinstance(box, list)
        or len(box) != 4
        or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in box)
        or box[2] <= box[0]
        or box[3] <= box[1]
    ):
        raise ComparisonError("detection source box is invalid")


def box_iou(left: list[float], right: list[float]) -> float:
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def compare(
    reference: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    minimum_iou: float,
    maximum_confidence_delta: float,
) -> list[dict[str, Any]]:
    if len(reference) != len(candidate):
        raise ComparisonError(
            f"detection count mismatch: reference={len(reference)} candidate={len(candidate)}"
        )
    for detection in reference + candidate:
        validate_detection(detection)
    unmatched = set(range(len(candidate)))
    matches = []
    for expected in reference:
        class_matches = [
            index
            for index in unmatched
            if candidate[index]["class_id"] == expected["class_id"]
            and candidate[index]["class_name"] == expected["class_name"]
        ]
        if not class_matches:
            raise ComparisonError(f"no candidate detection for class {expected['class_name']}")
        best_index = max(
            class_matches,
            key=lambda index: box_iou(
                expected["box_xyxy_source"], candidate[index]["box_xyxy_source"]
            ),
        )
        overlap = box_iou(
            expected["box_xyxy_source"], candidate[best_index]["box_xyxy_source"]
        )
        confidence_delta = abs(expected["confidence"] - candidate[best_index]["confidence"])
        if overlap < minimum_iou:
            raise ComparisonError(
                f"class {expected['class_name']} IoU {overlap} is below {minimum_iou}"
            )
        if confidence_delta > maximum_confidence_delta:
            raise ComparisonError(
                f"class {expected['class_name']} confidence delta {confidence_delta} "
                f"exceeds {maximum_confidence_delta}"
            )
        unmatched.remove(best_index)
        matches.append(
            {
                "reference_rank": expected["rank"],
                "candidate_rank": candidate[best_index]["rank"],
                "class_id": expected["class_id"],
                "class_name": expected["class_name"],
                "iou": overlap,
                "absolute_confidence_difference": confidence_delta,
            }
        )
    if unmatched:
        raise ComparisonError(f"unmatched candidate detections remain: {sorted(unmatched)}")
    return matches


def main() -> int:
    args = parse_args()
    if args.min_iou != FROZEN_MINIMUM_IOU:
        raise ComparisonError(f"--min-iou must remain frozen at {FROZEN_MINIMUM_IOU}")
    if args.max_confidence_delta != FROZEN_MAXIMUM_CONFIDENCE_DELTA:
        raise ComparisonError(
            "--max-confidence-delta must remain frozen at "
            f"{FROZEN_MAXIMUM_CONFIDENCE_DELTA}"
        )
    reference_payload = load_json(args.reference)
    candidate_payload = load_json(args.candidate)
    reference = reference_payload.get("detections")
    candidate = candidate_payload.get("detections")
    if not isinstance(reference, list) or not isinstance(candidate, list):
        raise ComparisonError("both artifacts must contain a detections list")
    matches = compare(reference, candidate, args.min_iou, args.max_confidence_delta)
    minimum_observed_iou = min((match["iou"] for match in matches), default=1.0)
    maximum_observed_delta = max(
        (match["absolute_confidence_difference"] for match in matches), default=0.0
    )
    evidence = {
        "schema_version": 1,
        "application": "edgeai_compare_detections",
        "reference": {
            "path": str(args.reference),
            "sha256": sha256_file(args.reference),
            "detection_count": len(reference),
        },
        "candidate": {
            "path": str(args.candidate),
            "sha256": sha256_file(args.candidate),
            "detection_count": len(candidate),
            "model_sha256": candidate_payload.get("model", {}).get("sha256"),
            "runtime_version": candidate_payload.get("model", {}).get("runtime_version"),
            "execution_provider": candidate_payload.get("model", {}).get(
                "execution_provider"
            ),
        },
        "tolerances": {
            "minimum_iou": args.min_iou,
            "maximum_absolute_confidence_difference": args.max_confidence_delta,
        },
        "matches": matches,
        "minimum_observed_iou": minimum_observed_iou,
        "maximum_observed_confidence_difference": maximum_observed_delta,
        "status": "PASS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Reference detections: {len(reference)}")
    print(f"Candidate detections: {len(candidate)}")
    print(f"Minimum matched IoU: {minimum_observed_iou:.12g}")
    print(f"Maximum confidence delta: {maximum_observed_delta:.12g}")
    print("Comparison status: PASS")
    print(f"Evidence: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ComparisonError as error:
        raise SystemExit(f"detection comparison error: {error}") from error
