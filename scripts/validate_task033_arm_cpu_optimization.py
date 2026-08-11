#!/usr/bin/env python3
"""Validate Task 033 profiler evidence without trusting its summary fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import statistics
import sys
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {
    "param_sha256": "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4",
    "bin_sha256": "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0",
    "input_sha256": "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071",
    "ncnn_version": "1.0.20240410",
}


def fail(message: str) -> None:
    raise ValueError(message)


def finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        fail(f"{label} is not finite")
    return float(value)


def nearest(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def validate(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("task") != "033" or data.get("status") != "PASS_TARGET":
        fail(f"{path}: not a PASS_TARGET Task 033 profiler result")
    identity = data.get("identity", {})
    for key in ("manifest_sha256", "param_sha256", "bin_sha256", "input_sha256", "config_sha256", "reference_sha256"):
        if not HEX64.fullmatch(str(identity.get(key, ""))):
            fail(f"{path}: invalid identity hash {key}")
    for key, expected in EXPECTED.items():
        if identity.get(key) != expected:
            fail(f"{path}: {key} differs from frozen contract")
    experiment = data.get("experiment", {})
    threads = experiment.get("threads")
    if not isinstance(threads, int) or not 1 <= threads <= 4:
        fail(f"{path}: thread option outside [1,4]")
    if experiment.get("affinity") not in {"default", "cpu0", "cpu1", "both"}:
        fail(f"{path}: invalid affinity")
    if not isinstance(experiment.get("warmup"), int) or experiment["warmup"] < 0:
        fail(f"{path}: invalid warmup")
    if not isinstance(experiment.get("repeat"), int) or experiment["repeat"] < 1:
        fail(f"{path}: invalid repeat")
    workload = data.get("workload", {})
    if workload.get("input_shape") != [1, 3, 640, 640] or workload.get("output_shape") != [1, 25200, 85]:
        fail(f"{path}: frozen tensor shape differs")
    if workload.get("input_dtype") != "float32" or workload.get("output_dtype") != "float32":
        fail(f"{path}: frozen tensor dtype differs")
    samples = data.get("samples")
    if not isinstance(samples, list) or len(samples) != experiment["repeat"]:
        fail(f"{path}: raw sample count does not equal repeat")
    stage_names = ("preprocess", "inference", "decode", "nms", "postprocess", "pipeline", "end_to_end")
    stage_values: dict[str, list[float]] = {name: [] for name in stage_names}
    for index, sample in enumerate(samples):
        for key in ("preprocess_ns", "inference_ns", "decode_ns", "nms_ns", "postprocess_ns", "pipeline_ns", "end_to_end_ns"):
            if not isinstance(sample.get(key), int) or sample[key] < 0:
                fail(f"{path}: sample {index} has invalid {key}")
        if sample["pipeline_ns"] != sample["preprocess_ns"] + sample["inference_ns"] + sample["postprocess_ns"]:
            fail(f"{path}: sample {index} pipeline does not reconcile")
        if sample["decode_ns"] + sample["nms_ns"] > sample["postprocess_ns"]:
            fail(f"{path}: sample {index} decode+nms exceeds postprocess")
        correctness = sample.get("correctness", {})
        if correctness.get("status") != "PASS_TARGET" or correctness.get("detection_count") != 5:
            fail(f"{path}: sample {index} correctness failed")
        if finite(correctness.get("minimum_class_matched_iou"), "minimum IoU") < 0.99:
            fail(f"{path}: sample {index} IoU below gate")
        if finite(correctness.get("maximum_absolute_confidence_difference"), "confidence delta") > 0.01:
            fail(f"{path}: sample {index} confidence delta above gate")
        for name, key in (
            ("preprocess", "preprocess_ns"), ("inference", "inference_ns"),
            ("decode", "decode_ns"), ("nms", "nms_ns"), ("postprocess", "postprocess_ns"),
            ("pipeline", "pipeline_ns"), ("end_to_end", "end_to_end_ns"),
        ):
            stage_values[name].append(sample[key] / 1_000_000.0)
    summary = data.get("summary", {})
    if summary.get("sample_count") != len(samples):
        fail(f"{path}: summary sample count differs")
    for name in stage_names:
        row = summary.get("stages", {}).get(name)
        if not isinstance(row, dict):
            fail(f"{path}: missing summary stage {name}")
        values = stage_values[name]
        if abs(finite(row.get("mean_ms"), f"{name} mean") - statistics.fmean(values)) > 1e-6:
            fail(f"{path}: {name} mean was not independently recomputed")
        if abs(finite(row.get("p50_ms"), f"{name} p50") - nearest(values, 0.50)) > 1e-6:
            fail(f"{path}: {name} p50 was not nearest-rank")
        if abs(finite(row.get("p95_ms"), f"{name} p95") - nearest(values, 0.95)) > 1e-6:
            fail(f"{path}: {name} p95 was not nearest-rank")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=pathlib.Path)
    args = parser.parse_args()
    for path in args.paths:
        validate(path)
        print(f"PASS {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
