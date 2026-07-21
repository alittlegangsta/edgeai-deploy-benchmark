#!/usr/bin/env python3
"""Freeze and validate the Task 010 pnnx-to-ncnn conversion contract."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


EXPECTED_NCNN_TAG = "20240410"
EXPECTED_NCNN_REVISION = "56775de50990ab7f16627efdcf5529b49541206f"
EXPECTED_PNNX_TREE = "db4f9e5bc6dff9d78e0eecb1ebc5d2b19a4f5893"
EXPECTED_PNNX_SHA256 = (
    "978daf93358863bd6ebcceee6447d5a8db9b95c4aa1b25d34fdee71b816d052f"
)
EXPECTED_NCNN_LIBRARY_SHA256 = (
    "f1936728d19ce288ad7180926670ac7f1833107a13cc9446d178d2bef340fcc1"
)
EXPECTED_NCNN_CONFIG_SHA256 = (
    "8b132a0fa6e1335f1e33e49efd8b8fd009ba4869e89a47d6f2b45b6414a28e01"
)
EXPECTED_WEIGHTS_SHA256 = (
    "4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3"
)
EXPECTED_ONNX_SHA256 = (
    "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
)
EXPECTED_TORCHSCRIPT_SHA256 = (
    "1ea5813fac07158ca4ff5eb98b273353b1bf5baafdd46f1ced4ab33835247892"
)
NCNN_BUILTIN_TYPES = {
    "BinaryOp",
    "Concat",
    "Convolution",
    "Eltwise",
    "Input",
    "Interp",
    "MemoryData",
    "Permute",
    "Pooling",
    "Reshape",
    "Sigmoid",
    "Slice",
    "Split",
    "Swish",
    "UnaryOp",
}


class ConversionError(RuntimeError):
    """Raised when generated conversion evidence is incomplete or inconsistent."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--onnx-manifest", required=True, type=Path)
    parser.add_argument("--torchscript", required=True, type=Path)
    parser.add_argument("--torchscript-manifest", required=True, type=Path)
    parser.add_argument("--pnnx", required=True, type=Path)
    parser.add_argument("--pnnx-source", required=True, type=Path)
    parser.add_argument("--pnnx-provenance", required=True, type=Path)
    parser.add_argument("--torch-lib", required=True, type=Path)
    parser.add_argument("--ncnn-root", required=True, type=Path)
    parser.add_argument("--ncnn-provenance", required=True, type=Path)
    parser.add_argument("--conversion-log", required=True, type=Path)
    parser.add_argument("--pnnx-param", required=True, type=Path)
    parser.add_argument("--pnnx-bin", required=True, type=Path)
    parser.add_argument("--pnnx-onnx", required=True, type=Path)
    parser.add_argument("--pnnx-py", required=True, type=Path)
    parser.add_argument("--ncnn-py", required=True, type=Path)
    parser.add_argument("--param", required=True, type=Path)
    parser.add_argument("--bin", required=True, type=Path)
    parser.add_argument("--runtime-evidence", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def require_regular_file(path: Path, description: str) -> Path:
    if path.is_symlink():
        raise ConversionError(f"{description} must not be a symbolic link: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        raise ConversionError(f"{description} is missing or empty: {path}")
    return path


def sha256_file(path: Path) -> str:
    import hashlib

    require_regular_file(path, "artifact")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, description: str) -> dict[str, Any]:
    require_regular_file(path, description)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def load_json(path: Path, description: str) -> dict[str, Any]:
    require_regular_file(path, description)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"failed to parse {description}: {error}") from error
    if not isinstance(value, dict):
        raise ConversionError(f"{description} root must be an object")
    return value


def command_output(command: list[str], environment: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=environment,
    )
    if completed.returncode != 0:
        raise ConversionError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def parse_param(path: Path, expected_magic: str = "7767517") -> dict[str, Any]:
    require_regular_file(path, "param graph")
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if len(lines) < 3 or lines[0] != expected_magic:
        raise ConversionError(f"invalid param magic/header: {path}")
    try:
        declared_layer_count, declared_blob_count = map(int, lines[1].split())
    except (ValueError, TypeError) as error:
        raise ConversionError(f"invalid param counts: {path}") from error

    layers = []
    produced: set[str] = set()
    consumed: set[str] = set()
    blob_shapes: dict[str, dict[str, Any]] = {}
    shape_pattern = re.compile(r"#([^=\s]+)=\(([^)]*)\)([A-Za-z0-9]+)")
    for line_number, line in enumerate(lines[2:], start=3):
        tokens = line.split()
        if len(tokens) < 4:
            raise ConversionError(f"malformed param line {line_number}: {line}")
        try:
            bottom_count = int(tokens[2])
            top_count = int(tokens[3])
        except ValueError as error:
            raise ConversionError(f"invalid edge counts on line {line_number}") from error
        edge_end = 4 + bottom_count + top_count
        if len(tokens) < edge_end:
            raise ConversionError(f"truncated param edges on line {line_number}")
        bottoms = tokens[4 : 4 + bottom_count]
        tops = tokens[4 + bottom_count : edge_end]
        consumed.update(bottoms)
        produced.update(tops)
        for match in shape_pattern.finditer(line):
            dimensions = [int(value) for value in match.group(2).split(",") if value]
            blob_shapes[match.group(1)] = {
                "shape": dimensions,
                "dtype": match.group(3),
            }
        layers.append(
            {
                "type": tokens[0],
                "name": tokens[1],
                "bottoms": bottoms,
                "tops": tops,
            }
        )
    if len(layers) != declared_layer_count:
        raise ConversionError(
            f"declared {declared_layer_count} layers but parsed {len(layers)}: {path}"
        )
    input_blobs = sorted(consumed - produced)
    output_blobs = sorted(produced - consumed)
    return {
        "magic": lines[0],
        "declared_layer_count": declared_layer_count,
        "declared_blob_count": declared_blob_count,
        "parsed_layer_count": len(layers),
        "layer_type_counts": dict(sorted(Counter(item["type"] for item in layers).items())),
        "layers": layers,
        "input_blobs": input_blobs,
        "output_blobs": output_blobs,
        "blob_shapes": blob_shapes,
    }


def inspect_conversion_log(path: Path) -> dict[str, Any]:
    identity = artifact(path, "pnnx conversion log")
    text = path.read_text(encoding="utf-8")
    required_lines = (
        "fp16 = 0",
        "optlevel = 2",
        "device = cpu",
        "inputshape = [1,3,640,640]f32",
        "customop = ",
        "moduleop = ",
        "pnnx build without onnx-zero support, skip saving onnx",
    )
    missing = [line for line in required_lines if line not in text]
    if missing:
        raise ConversionError(f"conversion log is missing fixed settings: {missing}")
    for line in text.splitlines():
        normalized = line.strip().lower()
        if any(word in normalized for word in ("unsupported", "unknown", "failed", "error")):
            raise ConversionError(f"pnnx reported a conversion error: {line}")
        if normalized.startswith("customop") and normalized != "customop =":
            raise ConversionError(f"pnnx customop is not empty: {line}")
        if normalized.startswith("moduleop") and normalized != "moduleop =":
            raise ConversionError(f"pnnx moduleop is not empty: {line}")
    fallback_count = text.count("no attribute value in int list")
    if fallback_count != 4:
        raise ConversionError(
            f"unexpected pnnx int-list fallback diagnostic count: {fallback_count}"
        )
    return {
        **identity,
        "exit_status": 0,
        "fixed_settings_present": True,
        "unsupported_operator_count": 0,
        "customop": "",
        "moduleop": "",
        "pnnx_int_list_fallback_count": fallback_count,
        "pnnx_int_list_fallback_explanation": (
            "The pinned loader substituted zero for four Torch JIT integer-list elements "
            "without constant value attributes. The generated graph still freezes the "
            "correct explicit input/output shapes and the ncnn runtime contract probe "
            "passes. Task 011 semantic equivalence remains mandatory."
        ),
    }


def validate_runtime_evidence(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != 1 or value.get("status") != "PASS":
        raise ConversionError("ncnn runtime evidence did not pass schema 1")
    if value.get("ncnn_version") != "1.0.20240410":
        raise ConversionError(f"unexpected ncnn runtime version: {value.get('ncnn_version')}")
    if value.get("load_param_status") != 0 or value.get("load_model_status") != 0:
        raise ConversionError("ncnn runtime did not load both model files")
    if value.get("input_names") != ["in0"] or value.get("output_names") != ["out0"]:
        raise ConversionError("unexpected runtime blob names")
    expected_false = {
        "vulkan_compute",
        "fp16_packed",
        "fp16_storage",
        "fp16_arithmetic",
        "bf16_storage",
        "int8_inference",
        "int8_packed",
        "int8_storage",
        "int8_arithmetic",
    }
    options = value.get("options", {})
    if options.get("num_threads") != 1 or any(options.get(key) is not False for key in expected_false):
        raise ConversionError(f"runtime precision/device options are not frozen: {options}")
    outputs = value.get("probe", {}).get("outputs")
    if not isinstance(outputs, list) or len(outputs) != 1:
        raise ConversionError("runtime contract probe did not produce exactly one output")
    output = outputs[0]
    expected = {
        "name": "out0",
        "dims": 2,
        "w": 85,
        "h": 25200,
        "d": 1,
        "c": 1,
        "elempack": 1,
        "elembits": 32,
        "dtype": "float32",
        "scalar_count": 2142000,
        "all_finite": True,
    }
    if output != expected:
        raise ConversionError(f"unexpected runtime output contract: {output}")
    return output


def main() -> int:
    args = parse_args()
    torchscript_manifest = load_json(args.torchscript_manifest, "TorchScript manifest")
    onnx_manifest = load_json(args.onnx_manifest, "Task 002 manifest")
    if torchscript_manifest.get("status") != "PASS":
        raise ConversionError("TorchScript manifest is not PASS")

    actual_hashes = {
        "weights": sha256_file(args.weights),
        "onnx": sha256_file(args.onnx),
        "torchscript": sha256_file(args.torchscript),
    }
    expected_hashes = {
        "weights": EXPECTED_WEIGHTS_SHA256,
        "onnx": EXPECTED_ONNX_SHA256,
        "torchscript": EXPECTED_TORCHSCRIPT_SHA256,
    }
    if actual_hashes != expected_hashes:
        raise ConversionError(f"model-lineage SHA256 mismatch: {actual_hashes}")
    if onnx_manifest["model"]["source_weights"]["sha256"] != actual_hashes["weights"]:
        raise ConversionError("Task 002 manifest weight hash differs")
    if onnx_manifest["onnx"]["sha256"] != actual_hashes["onnx"]:
        raise ConversionError("Task 002 manifest ONNX hash differs")
    if torchscript_manifest["torchscript"]["sha256"] != actual_hashes["torchscript"]:
        raise ConversionError("TorchScript manifest hash differs")

    revision = command_output(["git", "-C", str(args.pnnx_source), "rev-parse", "HEAD"])
    tag = command_output(
        ["git", "-C", str(args.pnnx_source), "describe", "--tags", "--exact-match"]
    )
    tree = command_output(
        ["git", "-C", str(args.pnnx_source), "rev-parse", "HEAD:tools/pnnx"]
    )
    if (tag, revision, tree) != (
        EXPECTED_NCNN_TAG,
        EXPECTED_NCNN_REVISION,
        EXPECTED_PNNX_TREE,
    ):
        raise ConversionError(f"pnnx source identity mismatch: {(tag, revision, tree)}")

    pnnx_identity = artifact(args.pnnx, "pnnx executable")
    if pnnx_identity["sha256"] != EXPECTED_PNNX_SHA256:
        raise ConversionError("pnnx executable SHA256 mismatch")
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(args.torch_lib)
    file_output = command_output(["file", str(args.pnnx)])
    ldd_output = command_output(["ldd", str(args.pnnx)], environment)
    if "x86-64" not in file_output or "ELF 64-bit" not in file_output:
        raise ConversionError(f"pnnx is not Linux x86-64 ELF: {file_output}")
    if "not found" in ldd_output or "/mnt/c/msys64" in ldd_output:
        raise ConversionError(f"pnnx has an invalid dynamic dependency:\n{ldd_output}")

    ncnn_library = args.ncnn_root / "lib/libncnn.a"
    ncnn_config = args.ncnn_root / "lib/cmake/ncnn/ncnnConfig.cmake"
    ncnn_library_identity = artifact(ncnn_library, "ncnn library")
    ncnn_config_identity = artifact(ncnn_config, "ncnn CMake config")
    if ncnn_library_identity["sha256"] != EXPECTED_NCNN_LIBRARY_SHA256:
        raise ConversionError("ncnn library SHA256 mismatch")
    if ncnn_config_identity["sha256"] != EXPECTED_NCNN_CONFIG_SHA256:
        raise ConversionError("ncnn CMake config SHA256 mismatch")

    log = inspect_conversion_log(args.conversion_log)
    pnnx_graph = parse_param(args.pnnx_param)
    ncnn_graph = parse_param(args.param)
    if pnnx_graph["input_blobs"] != [] or pnnx_graph["output_blobs"] != []:
        # pnnx.Input/Output are layers, so external graph edges are intentionally empty.
        raise ConversionError("pnnx graph has unexpected external edges")
    pnnx_inputs = [layer for layer in pnnx_graph["layers"] if layer["type"] == "pnnx.Input"]
    pnnx_outputs = [layer for layer in pnnx_graph["layers"] if layer["type"] == "pnnx.Output"]
    if len(pnnx_inputs) != 1 or len(pnnx_outputs) != 1:
        raise ConversionError("pnnx graph must contain exactly one Input and one Output layer")
    input_blob = pnnx_inputs[0]["tops"][0]
    output_edge = pnnx_outputs[0]["bottoms"][0]
    if pnnx_graph["blob_shapes"].get(input_blob) != {
        "shape": [1, 3, 640, 640],
        "dtype": "f32",
    }:
        raise ConversionError("pnnx input annotation differs from the frozen contract")
    output_shape = None
    for layer in pnnx_graph["layers"]:
        if output_edge in layer["tops"] and len(layer["bottoms"]) == 1:
            output_shape = pnnx_graph["blob_shapes"].get(layer["bottoms"][0])
            break
    if output_shape != {"shape": [1, 25200, 85], "dtype": "f32"}:
        raise ConversionError(f"pnnx output annotation is not decoded candidates: {output_shape}")

    observed_ncnn_types = set(ncnn_graph["layer_type_counts"])
    custom_types = sorted(observed_ncnn_types - NCNN_BUILTIN_TYPES)
    if custom_types:
        raise ConversionError(f"ncnn graph contains unapproved/custom layer types: {custom_types}")
    ncnn_input_layers = [
        layer for layer in ncnn_graph["layers"] if layer["type"] == "Input"
    ]
    ncnn_input_blobs = [
        blob for layer in ncnn_input_layers for blob in layer["tops"]
    ]
    if ncnn_input_blobs != ["in0"] or ncnn_graph["output_blobs"] != ["out0"]:
        raise ConversionError(
            f"unexpected ncnn graph edges: {ncnn_input_blobs} -> {ncnn_graph['output_blobs']}"
        )

    runtime_evidence = load_json(args.runtime_evidence, "ncnn runtime evidence")
    runtime_output = validate_runtime_evidence(runtime_evidence)
    if Path(runtime_evidence["param_path"]) != args.param:
        raise ConversionError("runtime evidence param path differs")
    if Path(runtime_evidence["bin_path"]) != args.bin:
        raise ConversionError("runtime evidence bin path differs")

    pnnx_onnx = {
        "path": str(args.pnnx_onnx),
        "emitted": args.pnnx_onnx.exists(),
        "reason_if_absent": "pnnx built without onnx-zero because Torch uses CXX11 ABI 0",
    }
    if pnnx_onnx["emitted"]:
        pnnx_onnx.update(artifact(args.pnnx_onnx, "optional pnnx ONNX"))
    conversion_command = [
        f"LD_LIBRARY_PATH={args.torch_lib}",
        str(args.pnnx),
        str(args.torchscript.resolve()),
        "inputshape=[1,3,640,640]f32",
        "device=cpu",
        "fp16=0",
        "optlevel=2",
        f"pnnxparam={args.pnnx_param}",
        f"pnnxbin={args.pnnx_bin}",
        f"pnnxpy={args.pnnx_py}",
        f"pnnxonnx={args.pnnx_onnx}",
        f"ncnnparam={args.param.resolve()}",
        f"ncnnbin={args.bin.resolve()}",
        f"ncnnpy={args.ncnn_py}",
    ]

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lineage": {
            "statement": torchscript_manifest["lineage"]["statement"],
            "weights": artifact(args.weights, "source weights"),
            "frozen_onnx": {
                **artifact(args.onnx, "frozen ONNX"),
                "role": "unchanged ORT baseline",
            },
            "torchscript": artifact(args.torchscript, "TorchScript model"),
            "torchscript_manifest": artifact(
                args.torchscript_manifest, "TorchScript manifest"
            ),
        },
        "toolchain": {
            "official_source": "https://github.com/Tencent/ncnn",
            "tag": tag,
            "revision": revision,
            "pnnx_source_tree": tree,
            "pnnx": {
                **pnnx_identity,
                "file": file_output,
                "ldd": ldd_output.splitlines(),
                "torch_library_path": str(args.torch_lib),
                "provenance": artifact(args.pnnx_provenance, "pnnx provenance"),
            },
            "ncnn": {
                "root": str(args.ncnn_root),
                "version": runtime_evidence["ncnn_version"],
                "library": ncnn_library_identity,
                "cmake_config": ncnn_config_identity,
                "provenance": artifact(args.ncnn_provenance, "ncnn provenance"),
            },
        },
        "conversion": {
            "command": conversion_command,
            "settings": {
                "inputshape": "[1,3,640,640]f32",
                "device": "cpu",
                "fp16": 0,
                "optlevel": 2,
                "customop": [],
                "moduleop": [],
                "quantization": False,
                "vulkan": False,
                "ncnnoptimize_used": False,
            },
            "log": log,
            "pnnx_intermediate": {
                "param": artifact(args.pnnx_param, "pnnx param"),
                "bin": artifact(args.pnnx_bin, "pnnx bin"),
                "onnx": pnnx_onnx,
                "graph": {
                    key: value
                    for key, value in pnnx_graph.items()
                    if key not in {"layers", "blob_shapes"}
                },
                "input_annotation": pnnx_graph["blob_shapes"][input_blob],
                "output_annotation": output_shape,
            },
            "generated_helpers": {
                "executed": False,
                "pnnx_python": artifact(args.pnnx_py, "pnnx generated helper"),
                "ncnn_python": artifact(args.ncnn_py, "ncnn generated helper"),
            },
            "status": "PASS",
        },
        "ncnn_model": {
            "param": artifact(args.param, "ncnn param"),
            "bin": artifact(args.bin, "ncnn bin"),
            "graph": {
                key: value
                for key, value in ncnn_graph.items()
                if key not in {"layers", "blob_shapes"}
            },
            "custom_layer_types": custom_types,
            "custom_layer_count": 0,
        },
        "contract": {
            "classification": "single decoded YOLOv5 candidate tensor",
            "batch": 1,
            "precision": "FP32",
            "device": "CPU",
            "contains_graph_nms": False,
            "class_count": 80,
            "attributes_per_candidate": 85,
            "inputs": [
                {
                    "name": "in0",
                    "logical_shape": [1, 3, 640, 640],
                    "ncnn_dims": 3,
                    "w": 640,
                    "h": 640,
                    "c": 3,
                    "dtype": "float32",
                }
            ],
            "outputs": [
                {
                    "name": runtime_output["name"],
                    "logical_shape": [1, runtime_output["h"], runtime_output["w"]],
                    **{key: runtime_output[key] for key in (
                        "dims", "w", "h", "d", "c", "elempack", "elembits", "dtype"
                    )},
                }
            ],
            "detect_head": {
                "form": "decoded candidates",
                "scale_candidate_counts": [19200, 4800, 1200],
                "strides": [8, 16, 32],
                "adapter_required_for_task_011": False,
                "note": "Task 011 may pass out0 directly to the shared candidate postprocessor after ncnn Mat layout validation.",
            },
        },
        "runtime_validation": {
            **artifact(args.runtime_evidence, "ncnn runtime evidence"),
            "status": "PASS",
            "probe_scope": "zero-input shape/type/load contract probe; not a correctness result",
            "options": runtime_evidence["options"],
        },
        "task_011_preregistered_correctness_gate": {
            "must": [
                "equal detection count",
                "equal detection classes",
                "all boxes finite and within valid image bounds",
                "no confidence/NMS threshold or golden-result changes",
            ],
            "target": {
                "minimum_class_matched_iou": 0.99,
                "maximum_absolute_confidence_difference": 0.01,
                "disposition": "may proceed normally",
            },
            "hard_minimum": {
                "minimum_class_matched_iou": 0.98,
                "maximum_absolute_confidence_difference": 0.02,
                "disposition": "stop for human explanation if only this gate passes",
            },
            "below_hard_minimum": "Task 011 fails and stops",
        },
        "status": "PASS",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("Application: edgeai_validate_ncnn_conversion")
    print(f"pnnx SHA256: {pnnx_identity['sha256']}")
    print(f"ncnn param SHA256: {manifest['ncnn_model']['param']['sha256']}")
    print(f"ncnn bin SHA256: {manifest['ncnn_model']['bin']['sha256']}")
    print("Input blob: in0 [1,3,640,640] float32")
    print("Output blob: out0 [1,25200,85] float32")
    print("Custom layers: 0")
    print("ncnn conversion validation: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConversionError as error:
        raise SystemExit(f"ncnn conversion validation error: {error}") from error
