"""Shared Task 009 benchmark configuration, correctness, and statistics helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence


STAGES = ("preprocess", "inference", "postprocess", "pipeline_total")


class BenchmarkError(RuntimeError):
    """Raised when benchmark configuration or evidence is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise BenchmarkError(f"required JSON is missing or invalid: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BenchmarkError(f"failed to read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise BenchmarkError(f"JSON root must be an object: {path}")
    return value


def require_exact(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise BenchmarkError(f"{description}: expected {expected!r}, observed {value!r}")


def validate_benchmark_config(value: dict[str, Any]) -> None:
    require_exact(value.get("schema_version"), 1, "benchmark schema")
    require_exact(value.get("methodology_id"), "task009-pc-ort-v1", "methodology")
    runtime = value.get("runtime", {})
    frozen_runtime = {
        "execution_mode": "ORT_SEQUENTIAL",
        "execution_provider": "CPUExecutionProvider",
        "graph_optimization": "ORT_ENABLE_ALL",
        "inter_op_threads": 1,
        "intra_op_threads": 1,
        "onnxruntime_version": "1.18.1",
        "opencv_threads": 1,
    }
    require_exact(runtime, frozen_runtime, "runtime settings")
    workload = value.get("workload", {})
    require_exact(workload.get("input_size"), [640, 640], "input size")
    require_exact(workload.get("batch"), 1, "batch")
    require_exact(workload.get("precision"), "FP32", "precision")
    rounds = value.get("rounds", {})
    require_exact(rounds.get("count"), 5, "round count")
    require_exact(rounds.get("warmup"), 10, "warmup count")
    require_exact(rounds.get("repeat"), 100, "repeat count")
    require_exact(
        rounds.get("order"),
        [
            ["python_ort", "cpp_ort"],
            ["cpp_ort", "python_ort"],
            ["python_ort", "cpp_ort"],
            ["cpp_ort", "python_ort"],
            ["python_ort", "cpp_ort"],
        ],
        "round order",
    )
    environment = value.get("environment", {})
    require_exact(environment.get("platform"), "WSL2", "platform")
    require_exact(environment.get("cpu_affinity"), "scheduler managed", "CPU affinity")
    require_exact(environment.get("cpu_pinning"), "disabled", "CPU pinning")
    require_exact(
        environment.get("required_environment_variables"),
        {
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
        },
        "thread environment",
    )
    require_exact(
        value.get("timing", {}).get("pipeline_total_formula"),
        "preprocess_ns + inference_ns + postprocess_ns",
        "pipeline formula",
    )
    require_exact(
        value.get("statistics", {}).get("percentile_method"),
        "nearest-rank",
        "percentile method",
    )
    require_exact(
        value.get("statistics", {}).get("maximum_round_mean_relative_difference_percent"),
        10.0,
        "stability limit",
    )


def nearest_rank(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise BenchmarkError("cannot calculate a percentile of an empty sequence")
    if not 0.0 < percentile <= 1.0:
        raise BenchmarkError("percentile must be in (0, 1]")
    checked = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0.0 for value in checked):
        raise BenchmarkError("statistics require finite nonnegative values")
    ordered = sorted(checked)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def summarize_ns(values: Sequence[int | float]) -> dict[str, float | int]:
    if not values:
        raise BenchmarkError("cannot summarize an empty sequence")
    checked: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BenchmarkError("raw nanoseconds must be numeric integers")
        if not math.isfinite(float(value)) or float(value) < 0 or int(value) != value:
            raise BenchmarkError("raw nanoseconds must be finite nonnegative integers")
        checked.append(int(value))
    milliseconds = [value / 1_000_000.0 for value in checked]
    return {
        "count": len(milliseconds),
        "mean_ms": sum(milliseconds) / len(milliseconds),
        "p50_ms": nearest_rank(milliseconds, 0.50),
        "p90_ms": nearest_rank(milliseconds, 0.90),
        "min_ms": min(milliseconds),
        "max_ms": max(milliseconds),
    }


def maximum_relative_difference(values: Sequence[float]) -> float:
    if not values:
        raise BenchmarkError("round means are empty")
    checked = [float(value) for value in values]
    if any(not math.isfinite(value) or value <= 0.0 for value in checked):
        raise BenchmarkError("round means must be finite and positive")
    return (max(checked) - min(checked)) / min(checked) * 100.0


def sample_from_boundaries(
    preprocess_ns: int, inference_ns: int, postprocess_ns: int
) -> dict[str, int]:
    values = (preprocess_ns, inference_ns, postprocess_ns)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise BenchmarkError("stage durations must be nonnegative integer nanoseconds")
    return {
        "preprocess_ns": preprocess_ns,
        "inference_ns": inference_ns,
        "postprocess_ns": postprocess_ns,
        "pipeline_total_ns": sum(values),
    }


def box_iou(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != 4 or len(right) != 4:
        raise BenchmarkError("IoU boxes must contain four values")
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def compare_detections(
    reference: Sequence[dict[str, Any]],
    candidate: Sequence[dict[str, Any]],
    minimum_iou: float,
    maximum_confidence_difference: float,
) -> dict[str, Any]:
    if len(reference) != len(candidate):
        raise BenchmarkError(
            f"detection count differs: expected {len(reference)}, observed {len(candidate)}"
        )
    unmatched = set(range(len(candidate)))
    matches = []
    for expected in reference:
        class_matches = [
            index
            for index in unmatched
            if candidate[index].get("class_id") == expected.get("class_id")
            and candidate[index].get("class_name") == expected.get("class_name")
        ]
        if not class_matches:
            raise BenchmarkError(f"missing class-matched detection: {expected.get('class_name')}")
        best = max(
            class_matches,
            key=lambda index: box_iou(
                expected["box_xyxy_source"], candidate[index]["box_xyxy_source"]
            ),
        )
        overlap = box_iou(
            expected["box_xyxy_source"], candidate[best]["box_xyxy_source"]
        )
        confidence_difference = abs(
            float(expected["confidence"]) - float(candidate[best]["confidence"])
        )
        if overlap < minimum_iou:
            raise BenchmarkError(f"class-matched IoU {overlap} is below {minimum_iou}")
        if confidence_difference > maximum_confidence_difference:
            raise BenchmarkError(
                f"confidence difference {confidence_difference} exceeds "
                f"{maximum_confidence_difference}"
            )
        unmatched.remove(best)
        matches.append(
            {
                "class_id": expected["class_id"],
                "class_name": expected["class_name"],
                "iou": overlap,
                "absolute_confidence_difference": confidence_difference,
            }
        )
    return {
        "status": "PASS",
        "detection_count": len(candidate),
        "minimum_class_matched_iou": min((item["iou"] for item in matches), default=1.0),
        "maximum_absolute_confidence_difference": max(
            (item["absolute_confidence_difference"] for item in matches), default=0.0
        ),
    }
