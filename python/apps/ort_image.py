#!/usr/bin/env python3
"""Run one complete YOLOv5 image detection with CPU ONNX Runtime."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from edgeai_benchmark.model_contract import (
    ContractError,
    load_frozen_contract,
    runtime_tensor_info,
    sha256_file,
    validate_runtime_io,
)
from edgeai_benchmark.postprocess import (
    DetectionConfig,
    PostprocessError,
    decode_yolov5_output,
)
from edgeai_benchmark.preprocess import (
    PreprocessError,
    load_bgr_image,
    prepare_image_tensor,
)
from edgeai_benchmark.visualize import (
    VisualizationError,
    draw_detections,
    save_png,
)


APPLICATION_NAME = "edgeai_python_ort_image"
CPU_PROVIDER = "CPUExecutionProvider"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YOLOv5 single-image ORT detection.")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output-image", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    return parser.parse_args()


def load_config(path: Path) -> tuple[DetectionConfig, tuple[int, int], dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise PostprocessError(f"inference configuration is missing or invalid: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value["schema_version"] != 1:
            raise PostprocessError(
                f"expected configuration schema 1, observed {value['schema_version']}"
            )
        input_size = value["input_size"]
        if input_size != [640, 640]:
            raise PostprocessError(f"Task 004 requires input size [640, 640]: {input_size}")
        config = DetectionConfig(
            confidence_threshold=float(value["confidence_threshold"]),
            iou_threshold=float(value["iou_threshold"]),
            class_aware_nms=value["class_aware_nms"],
            max_detections=int(value["max_detections"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise PostprocessError(f"invalid inference configuration: {error}") from error
    config.validate()
    return config, (int(input_size[0]), int(input_size[1])), value


def elapsed_ms(start_ns: int, end_ns: int) -> float:
    return round((end_ns - start_ns) / 1_000_000.0, 6)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_image.resolve() == args.image.resolve():
        raise VisualizationError("output image must not overwrite the reference image")
    frozen = load_frozen_contract(args.manifest, args.model)
    config, input_size, raw_config = load_config(args.config)
    contract = frozen["contract"]
    if contract["inputs"][0]["shape"] != [1, 3, input_size[0], input_size[1]]:
        raise ContractError("configuration input size differs from the frozen model contract")

    available_providers = ort.get_available_providers()
    if CPU_PROVIDER not in available_providers:
        raise ContractError(f"{CPU_PROVIDER} is unavailable: {available_providers}")
    session = ort.InferenceSession(str(args.model), providers=[CPU_PROVIDER])
    selected_providers = session.get_providers()
    if selected_providers != [CPU_PROVIDER]:
        raise ContractError(f"unexpected session providers: {selected_providers}")
    runtime_inputs = [runtime_tensor_info(node) for node in session.get_inputs()]
    runtime_outputs = [runtime_tensor_info(node) for node in session.get_outputs()]
    validate_runtime_io(runtime_inputs, runtime_outputs, contract)

    preprocess_start = time.perf_counter_ns()
    source_image = load_bgr_image(args.image)
    input_tensor, letterbox_metadata = prepare_image_tensor(
        source_image,
        target_size=input_size,
    )
    preprocess_end = time.perf_counter_ns()

    inference_start = time.perf_counter_ns()
    raw_outputs = session.run(
        [value["name"] for value in runtime_outputs],
        {runtime_inputs[0]["name"]: input_tensor},
    )
    inference_end = time.perf_counter_ns()
    if len(raw_outputs) != 1:
        raise ContractError(f"Task 004 expects one frozen output, observed {len(raw_outputs)}")
    expected_output = contract["outputs"][0]
    if list(raw_outputs[0].shape) != expected_output["shape"]:
        raise ContractError(
            f"returned output shape differs from the frozen contract: "
            f"expected {expected_output['shape']}, observed {list(raw_outputs[0].shape)}"
        )
    if raw_outputs[0].dtype != np.float32:
        raise ContractError(
            f"returned output dtype differs from FP32: {raw_outputs[0].dtype}"
        )

    postprocess_start = time.perf_counter_ns()
    postprocessed = decode_yolov5_output(
        raw_outputs[0],
        contract["class_names"],
        letterbox_metadata,
        config,
    )
    postprocess_end = time.perf_counter_ns()

    visualization_start = time.perf_counter_ns()
    annotated = draw_detections(source_image, postprocessed["detections"])
    save_png(args.output_image, annotated)
    visualization_end = time.perf_counter_ns()

    image_check = cv2.imread(str(args.output_image), cv2.IMREAD_COLOR)
    if image_check is None or image_check.shape != source_image.shape:
        raise VisualizationError(
            f"written image failed decode/shape validation: {args.output_image}"
        )
    for detection in postprocessed["detections"]:
        box = detection["box_xyxy_source"]
        if not all(np.isfinite(value) for value in box):
            raise PostprocessError(f"non-finite emitted box: {detection}")
        if not (0.0 <= box[0] < box[2] <= source_image.shape[1]):
            raise PostprocessError(f"emitted x coordinates are outside the image: {box}")
        if not (0.0 <= box[1] < box[3] <= source_image.shape[0]):
            raise PostprocessError(f"emitted y coordinates are outside the image: {box}")

    result = {
        "schema_version": 1,
        "application": APPLICATION_NAME,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": {
            "path": str(args.model),
            "sha256": frozen["model_sha256"],
            "manifest_path": str(args.manifest),
            "runtime_inputs": runtime_inputs,
            "runtime_outputs": runtime_outputs,
            "execution_provider": CPU_PROVIDER,
        },
        "source_image": {
            "path": str(args.image),
            "sha256": sha256_file(args.image),
            "size_bytes": args.image.stat().st_size,
            "shape_bgr": [int(value) for value in source_image.shape],
        },
        "output_image": {
            "path": str(args.output_image),
            "sha256": sha256_file(args.output_image),
            "size_bytes": args.output_image.stat().st_size,
            "shape_bgr": [int(value) for value in image_check.shape],
            "decode_validation": "PASS",
            "visual_review": "PENDING_HUMAN_REVIEW",
        },
        "configuration": raw_config,
        "configuration_file": {
            "path": str(args.config),
            "sha256": sha256_file(args.config),
        },
        "preprocess": letterbox_metadata,
        "candidate_counts": {
            key: postprocessed[key]
            for key in (
                "raw_candidate_count",
                "threshold_candidate_count",
                "nms_candidate_count",
                "invalid_box_count",
            )
        },
        "detections": postprocessed["detections"],
        "timings_ms": {
            "measurement_type": "single-run diagnostic, not a benchmark",
            "clock": "time.perf_counter_ns",
            "preprocess": elapsed_ms(preprocess_start, preprocess_end),
            "inference": elapsed_ms(inference_start, inference_end),
            "postprocess": elapsed_ms(postprocess_start, postprocess_end),
            "visualization_and_png_write": elapsed_ms(
                visualization_start,
                visualization_end,
            ),
            "boundaries": {
                "preprocess": "image decode, letterbox, color/layout conversion, normalization",
                "inference": "session.run only",
                "postprocess": "decode, threshold, class-aware NMS, inverse map, clipping",
                "visualization_and_png_write": "copy, draw labels/boxes, PNG encode and write",
            },
        },
    }
    write_json(args.output_json, result)
    return result


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Application: {APPLICATION_NAME}")
    print(f"Execution provider: {result['model']['execution_provider']}")
    print(f"Model SHA256: {result['model']['sha256']}")
    print(f"Image SHA256: {result['source_image']['sha256']}")
    print(f"Configuration: {json.dumps(result['configuration'], sort_keys=True)}")
    print(f"Candidate counts: {json.dumps(result['candidate_counts'], sort_keys=True)}")
    for detection in result["detections"]:
        print(
            f"Detection {detection['rank']}: class={detection['class_name']} "
            f"class_id={detection['class_id']} confidence={detection['confidence']:.6f} "
            f"objectness={detection['objectness']:.6f} "
            f"class_score={detection['class_score']:.6f} "
            f"box={detection['box_xyxy_source']}"
        )
    print(f"Diagnostic timings ms: {json.dumps(result['timings_ms'], sort_keys=True)}")
    print(f"Output image: {result['output_image']['path']}")
    print("Visual review: PENDING_HUMAN_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
