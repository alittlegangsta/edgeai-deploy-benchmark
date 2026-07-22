#!/usr/bin/env python3
"""Validate the fixed YOLOv5 TorchScript export against frozen ORT semantics."""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort
import torch
import torchvision


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from edgeai_benchmark.model_contract import (  # noqa: E402
    ContractError,
    load_frozen_contract,
    runtime_tensor_info,
    sha256_file,
    summarize_tensor,
    validate_runtime_io,
)
from edgeai_benchmark.postprocess import (  # noqa: E402
    DetectionConfig,
    box_iou,
    decode_yolov5_output,
)
from edgeai_benchmark.preprocess import load_and_prepare_image  # noqa: E402


APPLICATION_NAME = "edgeai_validate_torchscript_conversion"
CPU_PROVIDER = "CPUExecutionProvider"
EXPECTED_INPUT_SHAPE = [1, 3, 640, 640]
EXPECTED_YOLOV5_TAG = "v7.0"
EXPECTED_YOLOV5_REVISION = "915bbf294bb74c859f0b41f1c23bc395014ea679"
EXPECTED_WEIGHTS_SHA256 = (
    "4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3"
)
EXPECTED_ONNX_SHA256 = (
    "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
)
MINIMUM_CLASS_MATCHED_IOU = 0.99
MAXIMUM_CONFIDENCE_DELTA = 0.001


class ValidationError(RuntimeError):
    """Raised when the exported model violates the approved Task 010 contract."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--onnx-manifest", required=True, type=Path)
    parser.add_argument("--torchscript", required=True, type=Path)
    parser.add_argument("--yolov5-source", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--export-log", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def require_regular_file(path: Path, description: str) -> Path:
    if path.is_symlink():
        raise ValidationError(f"{description} must not be a symbolic link: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValidationError(f"{description} is missing or empty: {path}")
    return path


def load_json(path: Path, description: str) -> dict[str, Any]:
    require_regular_file(path, description)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"failed to parse {description}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{description} root must be an object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_output(source: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise ValidationError(f"git {' '.join(arguments)} failed: {message}")
    return completed.stdout.strip()


def inspect_yolov5_source(source: Path) -> dict[str, Any]:
    source = source.resolve()
    export_script = require_regular_file(source / "export.py", "YOLOv5 exporter")
    require_regular_file(source / "models" / "yolo.py", "YOLOv5 model definition")
    tag = git_output(source, "describe", "--tags", "--exact-match")
    revision = git_output(source, "rev-parse", "HEAD")
    status = git_output(source, "status", "--short")
    if tag != EXPECTED_YOLOV5_TAG:
        raise ValidationError(f"expected YOLOv5 tag {EXPECTED_YOLOV5_TAG}, observed {tag}")
    if revision != EXPECTED_YOLOV5_REVISION:
        raise ValidationError(
            f"expected YOLOv5 revision {EXPECTED_YOLOV5_REVISION}, observed {revision}"
        )
    if status:
        raise ValidationError(f"YOLOv5 source worktree is not clean:\n{status}")
    return {
        "path": str(source),
        "tag": tag,
        "revision": revision,
        "tree": git_output(source, "rev-parse", "HEAD^{tree}"),
        "worktree_status": "clean",
        "export_py_sha256": sha256_file(export_script),
    }


def load_detection_config(path: Path) -> tuple[DetectionConfig, dict[str, Any]]:
    value = load_json(path, "inference configuration")
    expected_keys = {
        "schema_version",
        "input_size",
        "confidence_threshold",
        "iou_threshold",
        "class_aware_nms",
        "max_detections",
    }
    if set(value) != expected_keys:
        raise ValidationError(f"unexpected inference configuration keys: {sorted(value)}")
    if value["schema_version"] != 1 or value["input_size"] != [640, 640]:
        raise ValidationError("inference configuration does not preserve 640x640 schema 1")
    config = DetectionConfig(
        confidence_threshold=float(value["confidence_threshold"]),
        iou_threshold=float(value["iou_threshold"]),
        class_aware_nms=value["class_aware_nms"],
        max_detections=int(value["max_detections"]),
    )
    config.validate()
    return config, value


def flatten_tensors(value: Any) -> list[torch.Tensor]:
    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, (tuple, list)):
        tensors: list[torch.Tensor] = []
        for item in value:
            tensors.extend(flatten_tensors(item))
        return tensors
    if isinstance(value, dict):
        tensors = []
        for key in sorted(value):
            tensors.extend(flatten_tensors(value[key]))
        return tensors
    raise ValidationError(f"TorchScript returned unsupported value type: {type(value)!r}")


def validate_module_cpu_fp32(module: torch.jit.ScriptModule) -> dict[str, Any]:
    parameters = list(module.parameters())
    buffers = list(module.buffers())
    tensors = parameters + buffers
    devices = sorted({str(value.device) for value in tensors})
    dtypes = sorted({str(value.dtype) for value in tensors})
    if any(value.device.type != "cpu" for value in tensors):
        raise ValidationError(f"TorchScript contains non-CPU tensors: {devices}")
    if any(value.is_floating_point() and value.dtype != torch.float32 for value in tensors):
        raise ValidationError(f"TorchScript contains non-FP32 floating tensors: {dtypes}")
    return {
        "parameter_count": sum(value.numel() for value in parameters),
        "buffer_count": sum(value.numel() for value in buffers),
        "devices": devices,
        "dtypes": dtypes,
        "floating_precision": "FP32",
    }


def detection_matches(
    reference: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(reference) != len(candidate):
        raise ValidationError(
            f"detection count mismatch: ONNX={len(reference)} TorchScript={len(candidate)}"
        )
    unmatched = set(range(len(candidate)))
    matches = []
    for expected in reference:
        eligible = [
            index
            for index in unmatched
            if candidate[index]["class_id"] == expected["class_id"]
            and candidate[index]["class_name"] == expected["class_name"]
        ]
        if not eligible:
            raise ValidationError(
                f"TorchScript has no class match for ONNX {expected['class_name']}"
            )
        expected_box = np.asarray(expected["box_xyxy_source"], dtype=np.float32)
        overlaps = [
            float(
                box_iou(
                    expected_box,
                    np.asarray(
                        [candidate[index]["box_xyxy_source"]], dtype=np.float32
                    ),
                )[0]
            )
            for index in eligible
        ]
        best_position = int(np.argmax(overlaps))
        matched_index = eligible[best_position]
        overlap = overlaps[best_position]
        confidence_delta = abs(
            float(expected["confidence"]) - float(candidate[matched_index]["confidence"])
        )
        if overlap < MINIMUM_CLASS_MATCHED_IOU:
            raise ValidationError(
                f"class {expected['class_name']} IoU {overlap} is below "
                f"{MINIMUM_CLASS_MATCHED_IOU}"
            )
        if confidence_delta > MAXIMUM_CONFIDENCE_DELTA:
            raise ValidationError(
                f"class {expected['class_name']} confidence delta {confidence_delta} "
                f"exceeds {MAXIMUM_CONFIDENCE_DELTA}"
            )
        unmatched.remove(matched_index)
        matches.append(
            {
                "onnx_rank": expected["rank"],
                "torchscript_rank": candidate[matched_index]["rank"],
                "class_id": expected["class_id"],
                "class_name": expected["class_name"],
                "iou": overlap,
                "absolute_confidence_difference": confidence_delta,
            }
        )
    if unmatched:
        raise ValidationError(f"unmatched TorchScript detections: {sorted(unmatched)}")
    return matches


def package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as error:
        raise ValidationError(f"required distribution is missing: {distribution}") from error


def main() -> int:
    args = parse_args()
    for path, description in (
        (args.weights, "source weights"),
        (args.onnx, "frozen ONNX"),
        (args.onnx_manifest, "Task 002 manifest"),
        (args.torchscript, "TorchScript model"),
        (args.image, "reference image"),
        (args.config, "inference configuration"),
        (args.export_log, "TorchScript export log"),
    ):
        require_regular_file(path, description)

    frozen = load_frozen_contract(args.onnx_manifest, args.onnx)
    source_weights = frozen["manifest"]["model"]["source_weights"]
    weights_hash = sha256_file(args.weights)
    onnx_hash = sha256_file(args.onnx)
    if weights_hash != EXPECTED_WEIGHTS_SHA256 or weights_hash != source_weights["sha256"]:
        raise ValidationError(f"source-weight SHA256 mismatch: {weights_hash}")
    if onnx_hash != EXPECTED_ONNX_SHA256 or onnx_hash != frozen["model_sha256"]:
        raise ValidationError(f"frozen ONNX SHA256 mismatch: {onnx_hash}")

    source = inspect_yolov5_source(args.yolov5_source)
    config, raw_config = load_detection_config(args.config)
    input_tensor, letterbox_metadata = load_and_prepare_image(args.image)
    if list(input_tensor.shape) != EXPECTED_INPUT_SHAPE or input_tensor.dtype != np.float32:
        raise ValidationError(
            f"unexpected input tensor: shape={input_tensor.shape}, dtype={input_tensor.dtype}"
        )
    if not np.isfinite(input_tensor).all():
        raise ValidationError("input tensor contains non-finite values")

    module = torch.jit.load(str(args.torchscript), map_location="cpu")
    module.eval()
    module_contract = validate_module_cpu_fp32(module)
    torch_input = torch.from_numpy(input_tensor)
    with torch.inference_mode():
        torch_value = module(torch_input)
    torch_outputs = flatten_tensors(torch_value)
    if len(torch_outputs) != 1:
        raise ValidationError(
            f"expected one TorchScript tensor output, observed {len(torch_outputs)}"
        )
    torch_output_tensor = torch_outputs[0]
    if torch_output_tensor.device.type != "cpu":
        raise ValidationError(f"TorchScript output is not on CPU: {torch_output_tensor.device}")
    if torch_output_tensor.dtype != torch.float32:
        raise ValidationError(
            f"TorchScript output is not FP32: {torch_output_tensor.dtype}"
        )
    torch_output = torch_output_tensor.detach().contiguous().numpy()

    if ort.__version__ != "1.18.1":
        raise ValidationError(f"expected onnxruntime 1.18.1, observed {ort.__version__}")
    if CPU_PROVIDER not in ort.get_available_providers():
        raise ValidationError(f"{CPU_PROVIDER} is unavailable")
    session = ort.InferenceSession(str(args.onnx), providers=[CPU_PROVIDER])
    if session.get_providers() != [CPU_PROVIDER]:
        raise ValidationError(f"unexpected ORT providers: {session.get_providers()}")
    runtime_inputs = [runtime_tensor_info(node) for node in session.get_inputs()]
    runtime_outputs = [runtime_tensor_info(node) for node in session.get_outputs()]
    validate_runtime_io(runtime_inputs, runtime_outputs, frozen["contract"])
    onnx_outputs = session.run(
        [value["name"] for value in runtime_outputs],
        {runtime_inputs[0]["name"]: input_tensor},
    )
    if len(onnx_outputs) != 1:
        raise ValidationError(f"expected one ONNX output, observed {len(onnx_outputs)}")
    onnx_output = onnx_outputs[0]

    expected_shape = frozen["contract"]["outputs"][0]["shape"]
    for name, value in (("TorchScript", torch_output), ("ONNX", onnx_output)):
        if list(value.shape) != expected_shape:
            raise ValidationError(
                f"{name} output shape differs from frozen contract: {list(value.shape)}"
            )
        if value.dtype != np.float32:
            raise ValidationError(f"{name} output dtype is not float32: {value.dtype}")
        if not np.isfinite(value).all():
            raise ValidationError(f"{name} output contains non-finite values")

    class_names = frozen["contract"]["class_names"]
    onnx_detections = decode_yolov5_output(
        onnx_output, class_names, letterbox_metadata, config
    )
    torchscript_detections = decode_yolov5_output(
        torch_output, class_names, letterbox_metadata, config
    )
    matches = detection_matches(
        onnx_detections["detections"], torchscript_detections["detections"]
    )
    minimum_iou = min((item["iou"] for item in matches), default=1.0)
    maximum_confidence_delta = max(
        (item["absolute_confidence_difference"] for item in matches), default=0.0
    )
    absolute_delta = np.abs(torch_output - onnx_output)

    export_command = [
        ".venv/bin/python",
        str((args.yolov5_source.resolve() / "export.py")),
        "--weights",
        str(args.weights),
        "--include",
        "torchscript",
        "--imgsz",
        "640",
        "640",
        "--batch-size",
        "1",
        "--device",
        "cpu",
    ]
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    torchscript_identity = {
        "path": str(args.torchscript),
        "sha256": sha256_file(args.torchscript),
        "size_bytes": args.torchscript.stat().st_size,
        "load": "PASS",
        "forward_schema": str(module.forward.schema),
        "module": module_contract,
        "input": {
            "shape": EXPECTED_INPUT_SHAPE,
            "dtype": "float32",
            "device": "cpu",
            "layout": "NCHW",
        },
        "outputs": [summarize_tensor("output_0", torch_output)],
    }
    comparison = {
        "status": "PASS",
        "identical_input": True,
        "onnx_detection_count": len(onnx_detections["detections"]),
        "torchscript_detection_count": len(torchscript_detections["detections"]),
        "tolerances": {
            "minimum_class_matched_iou": MINIMUM_CLASS_MATCHED_IOU,
            "maximum_absolute_confidence_difference": MAXIMUM_CONFIDENCE_DELTA,
        },
        "minimum_observed_iou": minimum_iou,
        "maximum_observed_confidence_difference": maximum_confidence_delta,
        "matches": matches,
        "raw_tensor_delta_diagnostic": {
            "maximum_absolute_difference": float(np.max(absolute_delta)),
            "mean_absolute_difference": float(
                np.mean(absolute_delta, dtype=np.float64)
            ),
            "note": "Diagnostic only; Task 010 acceptance is the frozen detection-semantic comparison.",
        },
    }
    environment = {
        "python": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": np.__version__,
        "onnxruntime": ort.__version__,
        "opencv_python_distribution": package_version("opencv-python"),
        "opencv_runtime": cv2.__version__,
        "torch_cxx11_abi": bool(torch.compiled_with_cxx11_abi()),
        "cuda_available": torch.cuda.is_available(),
    }
    lineage = {
        "statement": (
            "The ORT implementations use the same frozen ONNX model. The ncnn model is "
            "generated from the same YOLOv5n v7.0 weights through a separately frozen "
            "TorchScript-to-pnnx conversion path and is validated for semantic equivalence."
        ),
        "weights": {
            "path": str(args.weights),
            "sha256": weights_hash,
            "size_bytes": args.weights.stat().st_size,
        },
        "frozen_onnx": {
            "path": str(args.onnx),
            "sha256": onnx_hash,
            "size_bytes": args.onnx.stat().st_size,
            "role": "unchanged ORT baseline",
        },
    }
    export = {
        "command": export_command,
        "source": source,
        "batch_size": 1,
        "input_size": [640, 640],
        "layout": "NCHW",
        "device": "cpu",
        "precision": "FP32",
        "include": ["torchscript"],
        "half": False,
        "int8": False,
        "optimize": False,
        "dynamic": False,
        "quantization": False,
        "vulkan": False,
        "model_surgery": False,
        "detect_head_replacement": False,
        "log": {
            "path": str(args.export_log),
            "sha256": sha256_file(args.export_log),
            "size_bytes": args.export_log.stat().st_size,
        },
    }
    evidence = {
        "schema_version": 1,
        "application": APPLICATION_NAME,
        "generated_at": generated_at,
        "lineage": lineage,
        "export": export,
        "environment": environment,
        "reference_input": {
            "image": {
                "path": str(args.image),
                "sha256": sha256_file(args.image),
                "size_bytes": args.image.stat().st_size,
            },
            "configuration": {
                "path": str(args.config),
                "sha256": sha256_file(args.config),
                "values": raw_config,
            },
            "tensor": summarize_tensor("images", input_tensor),
            "letterbox": letterbox_metadata,
        },
        "torchscript": torchscript_identity,
        "onnx_runtime": {
            "version": ort.__version__,
            "providers": session.get_providers(),
            "inputs": runtime_inputs,
            "outputs": runtime_outputs,
            "raw_outputs": [summarize_tensor("output0", onnx_output)],
        },
        "semantic_comparison": comparison,
        "status": "PASS",
    }
    write_json(args.output, evidence)

    manifest = {
        "schema_version": 1,
        "created_at": generated_at,
        "lineage": lineage,
        "export": export,
        "environment": environment,
        "torchscript": torchscript_identity,
        "reference_input": evidence["reference_input"],
        "frozen_onnx_runtime_contract": evidence["onnx_runtime"],
        "semantic_comparison": comparison,
        "validation_evidence": {
            "path": str(args.output),
            "sha256": sha256_file(args.output),
        },
        "status": "PASS",
    }
    write_json(args.manifest, manifest)

    print(f"Application: {APPLICATION_NAME}")
    print(f"Weights SHA256: {weights_hash}")
    print(f"Frozen ONNX SHA256: {onnx_hash}")
    print(f"TorchScript SHA256: {torchscript_identity['sha256']}")
    print(f"TorchScript output shape: {list(torch_output.shape)}")
    print(f"TorchScript output dtype: {torch_output.dtype}")
    print(f"Detections: {len(torchscript_detections['detections'])}")
    print(f"Minimum class-matched IoU: {minimum_iou:.12g}")
    print(f"Maximum confidence delta: {maximum_confidence_delta:.12g}")
    print("TorchScript validation: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, ValidationError) as error:
        raise SystemExit(f"TorchScript validation error: {error}") from error
