#!/usr/bin/env python3
"""Independent validation for real Task 028 ArmNN runner output."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

EXPECTED_MODEL = "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
EXPECTED_FLOOR_IDENTITY_MODEL = "755fb5adc596eee7a7255bc29c48b86f1895df1e8fa1577d785cb431d233bcf2"
EXPECTED_FLOOR_CONSTANT_MODEL = "e6066c047c2fc6bd37bd3ffa5322fa85a62873c5c9751e57ac8a569faf6201b7"
EXPECTED_FLOOR_REMOVED_MODEL = "e0720ffe896ed1919dba35699e703025b0bfad906bdcf97e4f2ab81e66df92e0"
EXPECTED_FLOOR_ADD_ZERO_MODEL = "9f330839f3130f0af0fb7c5ab4c3f761ff6fd7f625c46298ef17a99caab40811"
EXPECTED_FLOOR_FIXED_RESIZE_MODEL = "a8cd7290ee2d592ffd994d79dfceee3bf9dfd0eebe6a58b77624e2b6019a9de8"
EXPECTED_FLOOR_FIXED_RESIZE_INFERRED_MODEL = "f29c4b85f4d2ebc16095ac9849319bc1e0ff3863001b1d38f4f28db508e86ead"
EXPECTED_FLOOR_FIXED_RESIZE_SCALES_MODEL = "acfad8dbd631d61f47458a6a5639ed6804c3f1c53f6a177e2af08c7078b034da"
EXPECTED_QUANTIZED_FLOOR_REMOVED_MODEL = "3ce1e58b3d024ac890eef24e0704265aae12a7c58d005aeed288ff4c4aba4b76"
EXPECTED_INPUT = "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
EXPECTED_CONFIG = "82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d"
EXPECTED_INPUT_SHAPE = [1, 3, 640, 640]
EXPECTED_OUTPUT_SHAPE = [1, 25200, 85]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def finite_positive(value: object) -> bool:
    return finite_number(value) and float(value) > 0.0


def box_iou(left: list[float], right: list[float]) -> float:
    ix1 = max(left[0], right[0])
    iy1 = max(left[1], right[1])
    ix2 = min(left[2], right[2])
    iy2 = min(left[3], right[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_left = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    area_right = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = area_left + area_right - inter
    return 0.0 if union <= 0.0 else inter / union


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=pathlib.Path)
    parser.add_argument("--golden", required=True, type=pathlib.Path)
    parser.add_argument("--mode", choices=("correctness", "benchmark"), default="correctness")
    args = parser.parse_args()
    try:
        result = json.loads(args.result.read_text())
        golden = json.loads(args.golden.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read JSON: {error}")
    if result.get("status") != "PASS_ALNPU_BACKEND_LOAD":
        fail(f"runner status is {result.get('status')!r}")
    runtime = result.get("runtime", {})
    if runtime.get("requested_backend") != "Alnpu":
        fail("requested backend is not Alnpu")
    if runtime.get("fallback_allowed") is not False:
        fail("CPU fallback was not disabled")
    if runtime.get("requested_backend_registered") is not True:
        fail("Alnpu was not registered")
    if runtime.get("load_status") != "Success":
        fail("ArmNN LoadNetwork did not succeed")
    model = result.get("model", {})
    source = result.get("input", {})
    config = result.get("configuration", {})
    model_variant = model.get("variant", "frozen")
    if model_variant == "frozen":
        if model.get("sha256") != EXPECTED_MODEL:
            fail("model SHA256 differs from frozen YOLOv5n contract")
        if model.get("repair") != "none":
            fail("frozen model unexpectedly carries a repair marker")
    elif model_variant == "floor-identity":
        if model.get("sha256") != EXPECTED_FLOOR_IDENTITY_MODEL:
            fail("Floor-identity model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("Floor-identity source SHA256 differs from frozen YOLOv5n")
        if not str(model.get("repair", "")).startswith("constant FLOAT Floor nodes replaced"):
            fail("Floor-identity repair marker is missing")
    elif model_variant == "floor-constant":
        if model.get("sha256") != EXPECTED_FLOOR_CONSTANT_MODEL:
            fail("Floor-constant model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("Floor-constant source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "constant FLOAT Floor nodes replaced with equivalent Constant nodes":
            fail("Floor-constant repair marker is missing")
    elif model_variant == "floor-removed":
        if model.get("sha256") != EXPECTED_FLOOR_REMOVED_MODEL:
            fail("Floor-removed model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("Floor-removed source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "constant FLOAT Floor nodes removed and consumers rewired to Constant inputs":
            fail("Floor-removed repair marker is missing")
    elif model_variant == "floor-add-zero":
        if model.get("sha256") != EXPECTED_FLOOR_ADD_ZERO_MODEL:
            fail("Floor-add-zero model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("Floor-add-zero source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "constant FLOAT Floor nodes replaced with exact-value Add-zero nodes":
            fail("Floor-add-zero repair marker is missing")
    elif model_variant == "floor-fixed-resize":
        if model.get("sha256") != EXPECTED_FLOOR_FIXED_RESIZE_MODEL:
            fail("fixed-resize model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("fixed-resize source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "dynamic Resize shape subgraphs folded to fixed [1,C,H,W] sizes":
            fail("fixed-resize repair marker is missing")
    elif model_variant == "floor-fixed-resize-inferred":
        if model.get("sha256") != EXPECTED_FLOOR_FIXED_RESIZE_INFERRED_MODEL:
            fail("shape-inferred fixed-resize model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("shape-inferred fixed-resize source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "dynamic Resize shape subgraphs folded to fixed sizes with ONNX shape inference":
            fail("shape-inferred fixed-resize repair marker is missing")
    elif model_variant == "floor-fixed-resize-scales":
        if model.get("sha256") != EXPECTED_FLOOR_FIXED_RESIZE_SCALES_MODEL:
            fail("scales fixed-resize model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("scales fixed-resize source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "dynamic Resize shape subgraphs folded to fixed scales with explicit non-empty ROI":
            fail("scales fixed-resize repair marker is missing")
    elif model_variant == "quantized-floor-removed":
        if model.get("sha256") != EXPECTED_QUANTIZED_FLOOR_REMOVED_MODEL:
            fail("quantized Floor-removed model SHA256 differs from the reproducible repair")
        if model.get("source_sha256") != EXPECTED_MODEL:
            fail("quantized Floor-removed source SHA256 differs from frozen YOLOv5n")
        if model.get("repair") != "Conv-only QDQ INT8 calibration followed by constant FLOAT Floor removal":
            fail("quantized Floor-removed repair marker is missing")
    else:
        fail(f"unknown model variant: {model_variant!r}")
    if source.get("sha256") != EXPECTED_INPUT:
        fail("input SHA256 differs from frozen golden")
    if config.get("sha256") != EXPECTED_CONFIG:
        fail("configuration SHA256 differs from frozen contract")
    contract = result.get("tensor_contract", {})
    if contract.get("input", {}).get("shape") != EXPECTED_INPUT_SHAPE:
        fail("ArmNN input shape differs from [1,3,640,640]")
    if contract.get("input", {}).get("dtype") != "float32":
        fail("ArmNN input dtype is not float32")
    if contract.get("output", {}).get("shape") != EXPECTED_OUTPUT_SHAPE:
        fail("ArmNN output shape differs from [1,25200,85]")
    if contract.get("output", {}).get("dtype") != "float32":
        fail("ArmNN output dtype is not float32")
    raw = result.get("raw_output_stats", {})
    if raw.get("shape") != EXPECTED_OUTPUT_SHAPE or raw.get("element_count") != 25200 * 85:
        fail("raw output shape or element count is invalid")
    if raw.get("finite") is not True or not all(
        finite_number(raw.get(key)) for key in ("min", "max", "mean", "sample_sd")
    ):
        fail("raw output statistics are not finite")
    detections = result.get("detections")
    golden_detections = golden.get("detections")
    if not isinstance(detections, list) or len(detections) != len(golden_detections):
        fail("detection count differs from the frozen golden")
    min_iou = 1.0
    max_confidence_delta = 0.0
    for candidate, reference in zip(detections, golden_detections):
        if candidate.get("class_id") != reference.get("class_id"):
            fail("class id differs from the frozen golden")
        iou = box_iou(candidate.get("box_xyxy_source"), reference.get("box_xyxy_source"))
        min_iou = min(min_iou, iou)
        max_confidence_delta = max(
            max_confidence_delta,
            abs(float(candidate.get("confidence")) - float(reference.get("confidence"))),
        )
    if min_iou < 0.99 or max_confidence_delta > 0.01:
        fail(f"golden comparison failed: min_iou={min_iou}, confidence_delta={max_confidence_delta}")
    if args.mode == "benchmark":
        timings = result.get("timings", {})
        samples = timings.get("samples", [])
        if not samples:
            fail("benchmark contains no measured samples")
        for sample in samples:
            for key in ("preprocess_ms", "inference_ms", "postprocess_ms", "end_to_end_ms"):
                if not finite_positive(sample.get(key)):
                    fail(f"benchmark timing {key} is invalid")
        if result.get("mode") != "benchmark":
            fail("result mode is not benchmark")
    print(json.dumps({
        "status": "PASS",
        "backend": "Alnpu",
        "model_variant": model_variant,
        "fallback": "rejected",
        "detection_count": len(detections),
        "minimum_golden_iou": min_iou,
        "maximum_confidence_delta": max_confidence_delta,
        "mode": args.mode,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
