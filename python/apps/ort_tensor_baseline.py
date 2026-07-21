#!/usr/bin/env python3
"""Run one CPU ONNX Runtime inference and save raw tensor metadata."""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from edgeai_benchmark.model_contract import (
    ContractError,
    load_frozen_contract,
    runtime_tensor_info,
    sha256_file,
    summarize_tensor,
    validate_runtime_io,
)
from edgeai_benchmark.preprocess import PreprocessError, load_and_prepare_image


APPLICATION_NAME = "edgeai_ort_tensor_baseline"
CPU_PROVIDER = "CPUExecutionProvider"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate frozen YOLOv5 ONNX I/O and save raw tensor statistics."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--io-output", required=True, type=Path)
    parser.add_argument("--stats-output", required=True, type=Path)
    return parser.parse_args()


def distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as error:
        raise ContractError(f"required distribution is unavailable: {name}") from error


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if args.io_output.resolve() == args.stats_output.resolve():
        raise ContractError("I/O and statistics output paths must differ")

    frozen = load_frozen_contract(args.manifest, args.model)
    contract = frozen["contract"]
    available_providers = ort.get_available_providers()
    if CPU_PROVIDER not in available_providers:
        raise ContractError(
            f"{CPU_PROVIDER} is unavailable; observed providers: {available_providers}"
        )

    session = ort.InferenceSession(str(args.model), providers=[CPU_PROVIDER])
    selected_providers = session.get_providers()
    if selected_providers != [CPU_PROVIDER]:
        raise ContractError(
            f"expected only {CPU_PROVIDER}, observed session providers {selected_providers}"
        )

    runtime_inputs = [runtime_tensor_info(node) for node in session.get_inputs()]
    runtime_outputs = [runtime_tensor_info(node) for node in session.get_outputs()]
    validate_runtime_io(runtime_inputs, runtime_outputs, contract)

    expected_input_shape = contract["inputs"][0]["shape"]
    target_size = (expected_input_shape[2], expected_input_shape[3])
    input_tensor, preprocess_metadata = load_and_prepare_image(
        args.image,
        target_size=target_size,
    )
    if list(input_tensor.shape) != expected_input_shape:
        raise ContractError(
            f"input tensor shape mismatch: expected {expected_input_shape}, "
            f"observed {list(input_tensor.shape)}"
        )
    if input_tensor.dtype != np.float32:
        raise ContractError(f"input tensor dtype is {input_tensor.dtype}, expected float32")
    if not input_tensor.flags.c_contiguous:
        raise ContractError("input tensor is not C-contiguous")
    input_stats = summarize_tensor(contract["inputs"][0]["name"], input_tensor)

    output_names = [value["name"] for value in runtime_outputs]
    output_tensors = session.run(
        output_names,
        {runtime_inputs[0]["name"]: input_tensor},
    )
    if len(output_tensors) != len(runtime_outputs):
        raise ContractError(
            f"runtime returned {len(output_tensors)} outputs, expected {len(runtime_outputs)}"
        )

    output_stats = []
    for metadata, expected, tensor in zip(
        runtime_outputs,
        contract["outputs"],
        output_tensors,
        strict=True,
    ):
        if list(tensor.shape) != expected["shape"]:
            raise ContractError(
                f"output {metadata['name']} shape mismatch: expected {expected['shape']}, "
                f"observed {list(tensor.shape)}"
            )
        if tensor.dtype != np.float32:
            raise ContractError(
                f"output {metadata['name']} dtype is {tensor.dtype}, expected float32"
            )
        output_stats.append(summarize_tensor(metadata["name"], tensor))

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise PreprocessError(f"OpenCV failed to re-read reference image: {args.image}")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    environment = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": {
            "numpy": np.__version__,
            "onnx": distribution_version("onnx"),
            "onnxruntime": ort.__version__,
            "opencv-python": distribution_version("opencv-python"),
            "scipy": distribution_version("scipy"),
            "torch": distribution_version("torch"),
            "torchvision": distribution_version("torchvision"),
        },
        "available_execution_providers": available_providers,
        "selected_execution_providers": selected_providers,
    }
    model_io = {
        "schema_version": 1,
        "application": APPLICATION_NAME,
        "generated_at": generated_at,
        "environment": environment,
        "model": {
            "path": str(args.model),
            "manifest_path": str(args.manifest),
            "sha256": frozen["model_sha256"],
            "sha256_validation": "PASS",
        },
        "reference_image": {
            "path": str(args.image),
            "sha256": sha256_file(args.image),
            "size_bytes": args.image.stat().st_size,
            "decoded_shape_bgr": [int(value) for value in image.shape],
            "provenance": {
                "author": "alittlegangsta",
                "source": (
                    "Privacy-sanitized and resized derivative of an original "
                    "photograph created for this project by the same repository owner"
                ),
                "original_creation_date": "2026-07-20",
                "derivative_creation_date": "2026-07-20",
                "license": "CC BY 4.0",
            },
        },
        "runtime_io": {
            "inputs": runtime_inputs,
            "outputs": runtime_outputs,
            "validation": "PASS",
        },
        "preprocess": preprocess_metadata,
        "input_tensor": {
            "shape": [int(value) for value in input_tensor.shape],
            "dtype": str(input_tensor.dtype),
            "c_contiguous": bool(input_tensor.flags.c_contiguous),
            "value_range": [float(np.min(input_tensor)), float(np.max(input_tensor))],
            "all_finite": True,
        },
    }
    raw_stats = {
        "schema_version": 1,
        "application": APPLICATION_NAME,
        "generated_at": generated_at,
        "model_sha256": frozen["model_sha256"],
        "selected_execution_provider": CPU_PROVIDER,
        "input": input_stats,
        "outputs": output_stats,
        "all_tensors_finite": True,
        "interpretation": "Raw model tensors only; no decode, NMS, or detections.",
    }
    write_json(args.io_output, model_io)
    write_json(args.stats_output, raw_stats)
    return model_io, raw_stats


def main() -> int:
    args = parse_args()
    try:
        model_io, raw_stats = run(args)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Application: {APPLICATION_NAME}")
    print(f"Python: {model_io['environment']['python']}")
    print(f"ONNX Runtime: {model_io['environment']['packages']['onnxruntime']}")
    print(
        "Available providers: "
        + ", ".join(model_io["environment"]["available_execution_providers"])
    )
    print(
        "Selected providers: "
        + ", ".join(model_io["environment"]["selected_execution_providers"])
    )
    print(f"Model SHA256: {model_io['model']['sha256']}")
    for value in model_io["runtime_io"]["inputs"]:
        print(
            f"Input: name={value['name']} shape={value['shape']} "
            f"dtype={value['dtype']} ort_type={value['ort_type']}"
        )
    for value in model_io["runtime_io"]["outputs"]:
        print(
            f"Output: name={value['name']} shape={value['shape']} "
            f"dtype={value['dtype']} ort_type={value['ort_type']}"
        )
    input_tensor = model_io["input_tensor"]
    print(
        f"Input tensor: shape={input_tensor['shape']} dtype={input_tensor['dtype']} "
        f"contiguous={input_tensor['c_contiguous']}"
    )
    for value in raw_stats["outputs"]:
        print(
            f"Raw tensor: name={value['name']} shape={value['shape']} "
            f"dtype={value['dtype']} min={value['min']:.9g} max={value['max']:.9g} "
            f"mean={value['mean']:.9g} std={value['std']:.9g} "
            f"finite={value['finite_count']}/{value['element_count']}"
        )
    print("Raw inference validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
