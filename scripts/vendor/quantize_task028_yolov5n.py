#!/usr/bin/env python3
"""Reproduce the explicit Task 028 Conv-only QDQ YOLOv5n repair.

This is not a silent model replacement.  It accepts only the frozen model and
the frozen reference image, uses the pinned local ONNX Runtime quantizer, then
removes the four exact-integer constant Floor nodes that the Alnpu parser
rejects.  The output hash is frozen so a board run must identify this variant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np
import onnx
from onnxruntime.quantization import (
    CalibrationDataReader,
    CalibrationMethod,
    QuantFormat,
    QuantType,
    quantize_static,
)
import onnxruntime

SOURCE_SHA256 = "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
INPUT_SHA256 = "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
INTERMEDIATE_SHA256 = "308b93a89b1158b884930222621df9b0d581e88f36a90b6fa1e4aa24e8d50386"
FINAL_SHA256 = "3ce1e58b3d024ac890eef24e0704265aae12a7c58d005aeed288ff4c4aba4b76"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preprocess(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"cannot decode calibration image: {path}")
    height, width = image.shape[:2]
    scale = min(640.0 / width, 640.0 / height)
    new_width = round(width * scale)
    new_height = round(height * scale)
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
    left = (640 - new_width) // 2
    top = (640 - new_height) // 2
    canvas[top : top + new_height, left : left + new_width] = resized
    return canvas[:, :, ::-1].transpose(2, 0, 1).astype(np.float32)[None] / 255.0


class OneImageReader(CalibrationDataReader):
    def __init__(self, tensor: np.ndarray, input_name: str):
        self._items = [{input_name: tensor}]

    def get_next(self):  # type: ignore[no-untyped-def]
        return self._items.pop(0) if self._items else None


def remove_constant_floor(model: onnx.ModelProto) -> int:
    removed_names: set[str] = set()
    for node in list(model.graph.node):
        if node.op_type != "Floor":
            continue
        producers = [
            candidate
            for candidate in model.graph.node
            if node.input[0] in candidate.output and candidate.op_type == "Constant"
        ]
        if len(producers) != 1:
            raise SystemExit(f"Floor input lacks one Constant producer: {node.name}")
        node_value = producers[0].attribute[0].t
        if node_value.data_type != onnx.TensorProto.FLOAT:
            raise SystemExit(f"Floor constant is not FLOAT: {node.name}")
        value = float(onnx.numpy_helper.to_array(node_value).item())
        if not value.is_integer():
            raise SystemExit(f"Floor constant is not an exact integer: {node.name}")
        old_output = node.output[0]
        old_input = node.input[0]
        for consumer in model.graph.node:
            for index, input_name in enumerate(consumer.input):
                if input_name == old_output:
                    consumer.input[index] = old_input
        for graph_output in model.graph.output:
            if graph_output.name == old_output:
                graph_output.name = old_input
        removed_names.add(node.name)
    keep = [node for node in model.graph.node if node.name not in removed_names]
    del model.graph.node[:]
    model.graph.node.extend(keep)
    return len(removed_names)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--calibration-image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if onnx.__version__ != "1.16.2" or onnxruntime.__version__ != "1.18.1":
        raise SystemExit(
            f"requires onnx==1.16.2 and onnxruntime==1.18.1, observed "
            f"{onnx.__version__}/{onnxruntime.__version__}"
        )
    if sha256(args.input) != SOURCE_SHA256:
        raise SystemExit("frozen source model SHA256 mismatch")
    if sha256(args.calibration_image) != INPUT_SHA256:
        raise SystemExit("frozen calibration image SHA256 mismatch")
    source_model = onnx.load(str(args.input))
    input_name = source_model.graph.input[0].name
    calibration_tensor = preprocess(args.calibration_image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    intermediate = args.output.with_suffix(".qdq.onnx")
    quantize_static(
        str(args.input),
        str(intermediate),
        OneImageReader(calibration_tensor, input_name),
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
        per_channel=False,
        op_types_to_quantize=["Conv"],
        extra_options={"ActivationSymmetric": False, "WeightSymmetric": True},
    )
    intermediate_sha = sha256(intermediate)
    if intermediate_sha != INTERMEDIATE_SHA256:
        raise SystemExit(f"intermediate QDQ SHA256 mismatch: {intermediate_sha}")
    repaired = onnx.load(str(intermediate))
    removed = remove_constant_floor(repaired)
    if removed != 4:
        raise SystemExit(f"expected four constant Floor nodes, removed {removed}")
    onnx.checker.check_model(repaired, full_check=True)
    onnx.save(repaired, str(args.output))
    final_sha = sha256(args.output)
    if final_sha != FINAL_SHA256:
        raise SystemExit(f"final QDQ SHA256 mismatch: {final_sha}")
    intermediate.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "status": "PASS",
                "onnx_version": onnx.__version__,
                "onnxruntime_version": onnxruntime.__version__,
                "source_sha256": SOURCE_SHA256,
                "calibration_image_sha256": INPUT_SHA256,
                "intermediate_qdq_sha256": intermediate_sha,
                "final_sha256": final_sha,
                "quant_format": "QDQ",
                "activation_type": "QUInt8",
                "weight_type": "QInt8",
                "quantized_ops": ["Conv"],
                "removed_constant_floor_nodes": removed,
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
