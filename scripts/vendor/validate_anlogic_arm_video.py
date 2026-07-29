#!/usr/bin/env python3
"""Validate Task 020 video inference evidence independently of the ARM app."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import cv2


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "source_image": "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071",
    "param": "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4",
    "bin": "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0",
    "ncnn": "bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3",
    "libgomp": "87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91",
}
EXPECTED_FRAMES = 30
EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 960
EXPECTED_FPS = 5.0
MINIMUM_IOU = 0.99
MAXIMUM_CONFIDENCE_DELTA = 0.01


class ValidationError(RuntimeError):
    """Task 020 evidence violates the frozen video contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load JSON {path}: {error}") from error
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    require(path.is_file() and path.stat().st_size > 0, f"missing artifact: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def preserve_human_review(
    validation: dict[str, Any], existing: dict[str, Any]
) -> None:
    """Preserve only a complete, explicitly user-sourced approval record."""
    validation.update(
        {
            "human_video_review": "PENDING",
            "human_review_source": None,
            "candidate_approved": False,
        }
    )
    status = existing.get("human_video_review", "PENDING")
    if status == "PENDING":
        return
    require(status == "PASS", "human video review status is invalid")
    require(
        existing.get("human_review_source") == "user",
        "human video approval source must be user",
    )
    require(
        existing.get("candidate_approved") is True,
        "human video approval must explicitly approve the candidate",
    )
    recorded_at = existing.get("human_review_recorded_at")
    recorded_at_basis = existing.get("human_review_recorded_at_basis")
    require(
        isinstance(recorded_at, str) and bool(recorded_at),
        "human video approval record time is missing",
    )
    require(
        isinstance(recorded_at_basis, str) and bool(recorded_at_basis),
        "human video approval time basis is missing",
    )
    validation.update(
        {
            "human_video_review": "PASS",
            "human_review_source": "user",
            "candidate_approved": True,
            "human_review_recorded_at": recorded_at,
            "human_review_recorded_at_basis": recorded_at_basis,
        }
    )


def finite_number(value: Any, field: str) -> float:
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{field} must be numeric",
    )
    converted = float(value)
    require(math.isfinite(converted), f"{field} must be finite")
    return converted


def validate_detection(value: Any, width: int, height: int) -> dict[str, Any]:
    require(isinstance(value, dict), "detection must be an object")
    require(
        isinstance(value.get("class_id"), int) and value["class_id"] >= 0,
        "detection class_id is invalid",
    )
    require(
        isinstance(value.get("class_name"), str) and bool(value["class_name"]),
        "detection class_name is invalid",
    )
    confidence = finite_number(value.get("confidence"), "detection confidence")
    require(0.0 <= confidence <= 1.0, "detection confidence is outside [0,1]")
    box = value.get("box_xyxy_source")
    require(isinstance(box, list) and len(box) == 4, "detection box is invalid")
    coordinates = [
        finite_number(coordinate, "detection box coordinate") for coordinate in box
    ]
    require(
        0.0 <= coordinates[0] < coordinates[2] <= width
        and 0.0 <= coordinates[1] < coordinates[3] <= height,
        "detection box is outside the source frame",
    )
    return value


def box_iou(left: list[float], right: list[float]) -> float:
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def compare_detections(
    reference: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> tuple[float, float]:
    require(len(reference) == len(candidate) == 5, "detection count must be five")
    for detection in reference + candidate:
        validate_detection(detection, EXPECTED_WIDTH, EXPECTED_HEIGHT)
    unmatched = set(range(len(candidate)))
    minimum_iou = 1.0
    maximum_confidence_delta = 0.0
    for expected in reference:
        matches = [
            index
            for index in unmatched
            if candidate[index]["class_id"] == expected["class_id"]
            and candidate[index]["class_name"] == expected["class_name"]
        ]
        require(bool(matches), f"missing class match for {expected['class_name']}")
        selected = max(
            matches,
            key=lambda index: box_iou(
                expected["box_xyxy_source"], candidate[index]["box_xyxy_source"]
            ),
        )
        overlap = box_iou(
            expected["box_xyxy_source"], candidate[selected]["box_xyxy_source"]
        )
        confidence_delta = abs(
            finite_number(expected["confidence"], "reference confidence")
            - finite_number(candidate[selected]["confidence"], "candidate confidence")
        )
        minimum_iou = min(minimum_iou, overlap)
        maximum_confidence_delta = max(maximum_confidence_delta, confidence_delta)
        unmatched.remove(selected)
    require(not unmatched, "unmatched candidate detections remain")
    return minimum_iou, maximum_confidence_delta


def decode_and_sample_video(
    path: Path, sample_directory: Path
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    capture = cv2.VideoCapture(str(path))
    require(capture.isOpened(), f"cannot open output video: {path}")
    metadata = {
        "width": int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH))),
        "height": int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))),
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "reported_frame_count": int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT))),
        "backend": capture.getBackendName(),
    }
    require(metadata["width"] == EXPECTED_WIDTH, "output video width differs")
    require(metadata["height"] == EXPECTED_HEIGHT, "output video height differs")
    require(
        math.isclose(metadata["fps"], EXPECTED_FPS, abs_tol=0.01),
        "output video FPS differs",
    )
    sample_directory.mkdir(parents=True, exist_ok=True)
    sample_indices = {
        0: "frame_first.png",
        EXPECTED_FRAMES // 2: "frame_middle.png",
        EXPECTED_FRAMES - 1: "frame_last.png",
    }
    samples: dict[str, dict[str, Any]] = {}
    decoded = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        require(
            frame.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3),
            f"output frame {decoded} geometry differs",
        )
        if decoded in sample_indices:
            destination = sample_directory / sample_indices[decoded]
            require(cv2.imwrite(str(destination), frame), f"cannot write {destination}")
            decoded_again = cv2.imread(str(destination), cv2.IMREAD_COLOR)
            require(
                decoded_again is not None
                and decoded_again.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3),
                f"sample image cannot be decoded: {destination}",
            )
            samples[str(decoded)] = {
                "path": display_path(destination),
                "sha256": sha256_file(destination),
                "shape_bgr": [EXPECTED_HEIGHT, EXPECTED_WIDTH, 3],
                "decode_status": "PASS",
            }
        decoded += 1
    capture.release()
    require(decoded == EXPECTED_FRAMES, "output decoded frame count differs")
    require(len(samples) == 3, "first/middle/last output samples are incomplete")
    metadata["decoded_frame_count"] = decoded
    return metadata, samples


def validate(
    contract: dict[str, Any],
    environment: dict[str, Any],
    result: dict[str, Any],
    golden: dict[str, Any],
    input_video: Path,
    output_video: Path,
    sample_directory: Path,
) -> dict[str, Any]:
    require(contract.get("task") == "020", "video contract task differs")
    require(contract.get("status") == "PASS", "video contract is not PASS")
    source = contract.get("source_image")
    video = contract.get("video")
    require(isinstance(source, dict) and isinstance(video, dict), "contract assets differ")
    require(source.get("sha256") == EXPECTED["source_image"], "source hash differs")
    require(video.get("frame_count") == EXPECTED_FRAMES, "contract frame count differs")
    require(video.get("decoded_frame_count") == EXPECTED_FRAMES, "fixture decode differs")
    require(video.get("requested_fourcc") == "FFV1", "input fixture codec differs")
    require(video.get("container") == "AVI", "input fixture container differs")
    require(video.get("width") == EXPECTED_WIDTH, "input width differs")
    require(video.get("height") == EXPECTED_HEIGHT, "input height differs")
    require(
        math.isclose(float(video.get("fps")), EXPECTED_FPS, abs_tol=0.01),
        "input FPS differs",
    )
    require(sha256_file(input_video) == video.get("sha256"), "input video hash differs")

    require(environment.get("task") == "020", "environment task differs")
    require(environment.get("board_model") == "MLK-F3P-CZ02-DR1M90", "board differs")
    require(environment.get("architecture") == "aarch64", "architecture differs")
    require(environment.get("system_modified") is False, "board system was modified")
    hashes = environment.get("artifact_hashes")
    require(isinstance(hashes, dict), "environment artifact hashes are missing")
    require(hashes.get("libncnn_a") == EXPECTED["ncnn"], "libncnn hash differs")
    require(hashes.get("private_libgomp") == EXPECTED["libgomp"], "libgomp hash differs")

    require(result.get("schema_version") == 2, "video result schema differs")
    require(result.get("task") == "020", "video result task differs")
    require(
        result.get("runtime_profile") == "recommended-dual-thread",
        "runtime profile differs",
    )
    model = result.get("model")
    require(isinstance(model, dict), "model result is missing")
    require(model.get("param_sha256") == EXPECTED["param"], "param hash differs")
    require(model.get("bin_sha256") == EXPECTED["bin"], "bin hash differs")
    require(model.get("ncnn_library_sha256") == EXPECTED["ncnn"], "ncnn hash differs")
    require(
        model.get("private_libgomp_sha256") == EXPECTED["libgomp"],
        "private libgomp hash differs",
    )
    require(model.get("configured_threads") == 2, "configured threads differ")
    require(model.get("observed_process_threads", 0) >= 2, "two threads not observed")
    require(model.get("ncnn_openmp_compiled") == 1, "OpenMP is not compiled")
    require(model.get("ncnn_threads_compiled") == 1, "NCNN_THREADS is not compiled")
    require(model.get("ncnn_simpleomp_compiled") == 0, "simpleomp must be off")
    require(model.get("effective_parallel_backend") == "openmp", "backend differs")
    for field in ("vulkan", "fp16", "bf16", "int8"):
        require(model.get(field) == 0, f"{field} must be disabled")

    counts = result.get("counts")
    require(isinstance(counts, dict), "frame counts are missing")
    for field in (
        "reported_input_frames",
        "decoded_frames",
        "processed_frames",
        "written_frames",
        "verified_output_frames",
    ):
        require(counts.get(field) == EXPECTED_FRAMES, f"{field} differs")
    require(counts.get("failed_frames") == 0, "failed frame count is nonzero")
    require(result.get("exit_code") == 0, "application exit code differs")

    golden_detections = golden.get("detections")
    frames = result.get("frames")
    require(isinstance(golden_detections, list), "golden detections are missing")
    require(isinstance(frames, list) and len(frames) == EXPECTED_FRAMES, "frames differ")
    minimum_golden_iou = 1.0
    maximum_golden_confidence_delta = 0.0
    minimum_cross_frame_iou = 1.0
    maximum_cross_frame_confidence_delta = 0.0
    first_detections: list[dict[str, Any]] | None = None
    for index, frame in enumerate(frames):
        require(isinstance(frame, dict), "frame result must be an object")
        require(frame.get("frame_index") == index, "frame indices are not contiguous")
        candidate = frame.get("detections")
        require(isinstance(candidate, list), "frame detections are missing")
        golden_iou, golden_delta = compare_detections(golden_detections, candidate)
        minimum_golden_iou = min(minimum_golden_iou, golden_iou)
        maximum_golden_confidence_delta = max(
            maximum_golden_confidence_delta, golden_delta
        )
        counts_value = frame.get("candidate_counts")
        require(
            isinstance(counts_value, dict)
            and counts_value.get("nms") == 5
            and counts_value.get("invalid_boxes") == 0,
            "frame candidate counts differ",
        )
        timings = frame.get("timings_ms")
        require(isinstance(timings, dict), "frame timings are missing")
        for stage in (
            "video_read",
            "preprocess",
            "inference",
            "postprocess",
            "visualization",
            "video_write",
            "pipeline_total",
        ):
            require(finite_number(timings.get(stage), f"{stage} timing") >= 0.0, "timing < 0")
        require(
            math.isclose(
                float(timings["pipeline_total"]),
                float(timings["preprocess"])
                + float(timings["inference"])
                + float(timings["postprocess"]),
                abs_tol=0.01,
            ),
            "pipeline timing boundary differs",
        )
        if first_detections is None:
            first_detections = candidate
        cross_iou, cross_delta = compare_detections(first_detections, candidate)
        minimum_cross_frame_iou = min(minimum_cross_frame_iou, cross_iou)
        maximum_cross_frame_confidence_delta = max(
            maximum_cross_frame_confidence_delta, cross_delta
        )
    require(minimum_golden_iou >= MINIMUM_IOU, "per-frame golden IoU is below target")
    require(
        maximum_golden_confidence_delta <= MAXIMUM_CONFIDENCE_DELTA,
        "per-frame golden confidence delta exceeds target",
    )
    require(minimum_cross_frame_iou >= MINIMUM_IOU, "cross-frame IoU is below target")
    require(
        maximum_cross_frame_confidence_delta <= MAXIMUM_CONFIDENCE_DELTA,
        "cross-frame confidence delta exceeds target",
    )

    decoded_metadata, samples = decode_and_sample_video(output_video, sample_directory)
    output_record = result.get("output_video")
    require(isinstance(output_record, dict), "output video record is missing")
    output_hash = sha256_file(output_video)
    require(output_record.get("sha256") == output_hash, "output video hash differs")
    return {
        "schema_version": 1,
        "task": "020",
        "automated_validation": "PASS_TARGET",
        "runtime_profile": "recommended-dual-thread",
        "input_video": {
            "path": display_path(input_video),
            "sha256": sha256_file(input_video),
            "codec": "FFV1 lossless",
            "container": "AVI",
        },
        "output_video": {
            "path": display_path(output_video),
            "sha256": output_hash,
            "decode": decoded_metadata,
        },
        "frame_counts": {
            "declared": EXPECTED_FRAMES,
            "decoded": EXPECTED_FRAMES,
            "processed": EXPECTED_FRAMES,
            "written": EXPECTED_FRAMES,
            "verified": EXPECTED_FRAMES,
            "failed": 0,
        },
        "correctness": {
            "status": "PASS_TARGET",
            "frames_validated": EXPECTED_FRAMES,
            "detections_per_frame": 5,
            "classes_match": "PASS",
            "finite_values": "PASS",
            "valid_boxes": "PASS",
            "minimum_class_matched_iou": minimum_golden_iou,
            "maximum_absolute_confidence_difference":
                maximum_golden_confidence_delta,
            "minimum_cross_frame_iou": minimum_cross_frame_iou,
            "maximum_cross_frame_confidence_difference":
                maximum_cross_frame_confidence_delta,
        },
        "representative_frames": samples,
        "scope": {
            "timings_are_diagnostic_only": True,
            "formal_video_benchmark": False,
            "camera": False,
            "vulkan": False,
            "quantization": False,
            "npu": "HOLD",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir", type=Path, default=ROOT / "results/evidence/020"
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=ROOT / "results/acceptance/cpp_ncnn_reference.json",
    )
    parser.add_argument(
        "--input-video",
        type=Path,
        default=ROOT / "data/samples/videos/anlogic_arm_reference.avi",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        default=ROOT / "results/videos/anlogic_arm_ncnn_reference.avi",
    )
    parser.add_argument(
        "--samples-dir", type=Path, default=ROOT / "results/images/020"
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    output = arguments.output or arguments.evidence_dir / "video_validation.json"
    try:
        existing_validation = load_json(output) if output.is_file() else {}
        validation = validate(
            load_json(arguments.evidence_dir / "video_contract.json"),
            load_json(arguments.evidence_dir / "video_environment.json"),
            load_json(arguments.evidence_dir / "video_frame_detections.json"),
            load_json(arguments.golden),
            arguments.input_video,
            arguments.output_video,
            arguments.samples_dir,
        )
        preserve_human_review(validation, existing_validation)
    except (ValidationError, OSError, cv2.error) as error:
        print(f"Task 020 video validation: FAIL: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(json.dumps(validation, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
