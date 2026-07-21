#!/usr/bin/env python3
"""Inspect and freeze the Task 002 YOLOv5 ONNX contract."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime

import onnx
from onnx import TensorProto


SCHEMA_VERSION = 1
EXPECTED_INPUT_SHAPE = [1, 3, 640, 640]
EXPECTED_DEFAULT_OPSET = 12
EXPECTED_CLASS_COUNT = 80
CANONICAL_SOURCE_URL = "https://github.com/ultralytics/yolov5.git"
CANONICAL_WEIGHT_REFERENCE = (
    "https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt"
)
FORBIDDEN_EXPORT_FLAGS = {
    "--agnostic-nms",
    "--dynamic",
    "--half",
    "--nms",
    "--simplify",
}


class ContractError(RuntimeError):
    """Raised when an observed artifact violates the frozen Task 002 rules."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file(path: Path, description: str) -> Path:
    if path.is_symlink():
        raise ContractError(f"{description} must not be a symbolic link: {path}")
    if not path.is_file():
        raise ContractError(f"{description} is missing: {path}")
    if path.stat().st_size <= 0:
        raise ContractError(f"{description} is empty: {path}")
    return path


def _dimension(dimension: onnx.TensorShapeProto.Dimension) -> int | dict[str, str] | None:
    if dimension.HasField("dim_value"):
        return int(dimension.dim_value)
    if dimension.HasField("dim_param"):
        return {"symbol": dimension.dim_param}
    return None


def tensor_info(value: onnx.ValueInfoProto) -> dict[str, object]:
    tensor_type = value.type.tensor_type
    if not tensor_type.HasField("shape"):
        shape: list[object] | None = None
    else:
        shape = [_dimension(dimension) for dimension in tensor_type.shape.dim]
    return {
        "name": value.name,
        "dtype": TensorProto.DataType.Name(tensor_type.elem_type),
        "shape": shape,
    }


def parse_class_names(metadata: dict[str, str]) -> list[str]:
    raw_names = metadata.get("names")
    if raw_names is None:
        raise ContractError("ONNX metadata does not contain class names")
    try:
        names = ast.literal_eval(raw_names)
    except (SyntaxError, ValueError) as error:
        raise ContractError("ONNX class-name metadata is not a Python literal") from error
    if isinstance(names, dict):
        try:
            integer_names = {int(key): str(value) for key, value in names.items()}
        except (TypeError, ValueError) as error:
            raise ContractError("ONNX class-name keys are not integer-like") from error
        expected_keys = list(range(len(integer_names)))
        if sorted(integer_names) != expected_keys:
            raise ContractError("ONNX class-name keys are not contiguous from zero")
        return [integer_names[index] for index in expected_keys]
    if isinstance(names, (list, tuple)):
        return [str(value) for value in names]
    raise ContractError("ONNX class-name metadata must be a dictionary or list")


def find_nms_nodes(model: onnx.ModelProto) -> list[dict[str, object]]:
    matches = []
    for index, node in enumerate(model.graph.node):
        normalized = node.op_type.lower()
        if normalized == "nonmaxsuppression" or "nms" in normalized:
            matches.append(
                {
                    "index": index,
                    "name": node.name,
                    "domain": node.domain,
                    "op_type": node.op_type,
                }
            )
    return matches


def inspect_model(path: Path) -> dict[str, object]:
    regular_file(path, "ONNX model")
    model = onnx.load(path, load_external_data=True)
    onnx.checker.check_model(model, full_check=True)
    metadata = {item.key: item.value for item in model.metadata_props}
    class_names = parse_class_names(metadata)
    operator_counts = Counter(node.op_type for node in model.graph.node)
    nms_nodes = find_nms_nodes(model)
    inspection = {
        "ir_version": int(model.ir_version),
        "producer_name": model.producer_name,
        "producer_version": model.producer_version,
        "domain": model.domain,
        "model_version": int(model.model_version),
        "opset_imports": [
            {"domain": item.domain, "version": int(item.version)}
            for item in model.opset_import
        ],
        "inputs": [tensor_info(value) for value in model.graph.input],
        "outputs": [tensor_info(value) for value in model.graph.output],
        "metadata": metadata,
        "class_names": class_names,
        "class_count": len(class_names),
        "node_count": len(model.graph.node),
        "operator_counts": dict(sorted(operator_counts.items())),
        "nms_nodes": nms_nodes,
        "contains_graph_nms": bool(nms_nodes),
        "onnx_checker": "PASS",
    }
    validate_inspection(inspection)
    return inspection


def _contains_dynamic_dimension(shape: object) -> bool:
    return not isinstance(shape, list) or any(not isinstance(value, int) for value in shape)


def validate_inspection(inspection: dict[str, object]) -> None:
    default_opsets = [
        item["version"]
        for item in inspection["opset_imports"]  # type: ignore[index]
        if item["domain"] in ("", "ai.onnx")
    ]
    if default_opsets != [EXPECTED_DEFAULT_OPSET]:
        raise ContractError(f"expected default ONNX opset 12, observed {default_opsets}")

    inputs = inspection["inputs"]
    if not isinstance(inputs, list) or len(inputs) != 1:
        raise ContractError(f"expected exactly one ONNX input, observed {len(inputs)}")
    model_input = inputs[0]
    if model_input["dtype"] != "FLOAT":
        raise ContractError(f"expected FP32 input, observed {model_input['dtype']}")
    if model_input["shape"] != EXPECTED_INPUT_SHAPE:
        raise ContractError(
            f"expected static NCHW input {EXPECTED_INPUT_SHAPE}, observed {model_input['shape']}"
        )

    outputs = inspection["outputs"]
    if not isinstance(outputs, list) or not outputs:
        raise ContractError("ONNX graph has no outputs")
    for output in outputs:
        if output["dtype"] != "FLOAT":
            raise ContractError(
                f"expected FP32 output {output['name']}, observed {output['dtype']}"
            )
        if _contains_dynamic_dimension(output["shape"]):
            raise ContractError(f"output {output['name']} has dynamic or unknown dimensions")

    if inspection["contains_graph_nms"]:
        raise ContractError(f"ONNX graph contains NMS nodes: {inspection['nms_nodes']}")
    if inspection["class_count"] != EXPECTED_CLASS_COUNT:
        raise ContractError(
            f"expected 80 observed COCO class names, found {inspection['class_count']}"
        )


def _git(source: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip()
        raise ContractError(f"git {' '.join(arguments)} failed: {error}")
    return completed.stdout.strip()


def inspect_source(source: Path) -> dict[str, str]:
    source = source.resolve()
    regular_file(source / "export.py", "YOLOv5 exporter")
    regular_file(source / "models" / "yolo.py", "YOLOv5 model definition")
    origin_url = _git(source, "remote", "get-url", "origin")
    tag = _git(source, "describe", "--tags", "--exact-match")
    revision = _git(source, "rev-parse", "HEAD")
    status = _git(source, "status", "--short")
    if origin_url != CANONICAL_SOURCE_URL:
        raise ContractError(f"unexpected YOLOv5 origin: {origin_url}")
    if tag != "v7.0":
        raise ContractError(f"expected YOLOv5 tag v7.0, observed {tag}")
    if status:
        raise ContractError(f"YOLOv5 source worktree is not clean:\n{status}")
    return {
        "local_path": str(source),
        "origin_url": origin_url,
        "tag": tag,
        "revision": revision,
        "worktree_status": "clean",
    }


def inspect_weight_reference(source: Path) -> dict[str, str]:
    readme = regular_file(source.resolve() / "README.md", "YOLOv5 source README")
    content = readme.read_text(encoding="utf-8")
    if CANONICAL_WEIGHT_REFERENCE not in content:
        raise ContractError(
            "verified YOLOv5 v7.0 README does not contain the expected official YOLOv5n weight reference"
        )
    return {
        "url": CANONICAL_WEIGHT_REFERENCE,
        "document": "README.md from the verified YOLOv5 v7.0 source revision",
    }


def validate_export_command(command: str, weights: Path, source: Path) -> list[str]:
    tokens = shlex.split(command)
    forbidden = sorted(flag for flag in FORBIDDEN_EXPORT_FLAGS if flag in tokens)
    if forbidden:
        raise ContractError(f"export command contains forbidden flags: {forbidden}")
    required_sequences = (
        [str(source.resolve() / "export.py")],
        ["--weights", str(weights)],
        ["--imgsz", "640", "640"],
        ["--batch-size", "1"],
        ["--device", "cpu"],
        ["--include", "onnx"],
        ["--opset", "12"],
    )
    for sequence in required_sequences:
        width = len(sequence)
        if not any(tokens[index : index + width] == sequence for index in range(len(tokens) - width + 1)):
            raise ContractError(f"export command is missing required sequence: {sequence}")
    return tokens


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as error:
        raise ContractError(f"required package metadata is missing: {name}") from error


def build_manifest(
    model_path: Path,
    weights_path: Path,
    source_path: Path,
    export_command: str,
    inspection: dict[str, object],
) -> dict[str, object]:
    source = inspect_source(source_path)
    weight_reference = inspect_weight_reference(source_path)
    weights = regular_file(weights_path, "source weights")
    command_tokens = validate_export_command(export_command, weights_path, source_path)
    model = regular_file(model_path, "ONNX model")
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": timestamp,
        "model": {
            "family": "YOLOv5",
            "variant": "YOLOv5n",
            "release": "v7.0",
            "source": source,
            "source_weights": {
                "path": str(weights_path),
                "source_reference": weight_reference,
                "size_bytes": weights.stat().st_size,
                "sha256": sha256_file(weights),
            },
            "class_labels": {
                "source": "ONNX metadata emitted from the loaded checkpoint by the verified v7.0 exporter",
                "count": inspection["class_count"],
                "names": inspection["class_names"],
            },
        },
        "export": {
            "command": command_tokens,
            "device": "cpu",
            "input_size": [640, 640],
            "batch_size": 1,
            "precision": "FP32",
            "layout": "NCHW",
            "opset": 12,
            "dynamic_axes": False,
            "simplify": False,
            "graph_nms_requested": False,
            "python_version": sys.version.split()[0],
            "packages": {
                "torch": package_version("torch"),
                "torchvision": package_version("torchvision"),
                "numpy": package_version("numpy"),
                "scipy": package_version("scipy"),
                "onnx": package_version("onnx"),
                "opencv-python": package_version("opencv-python"),
            },
        },
        "onnx": {
            "path": str(model_path),
            "size_bytes": model.stat().st_size,
            "sha256": sha256_file(model),
            "contract": inspection,
        },
        "validation": {
            "onnx_checker": "PASS",
            "static_batch_1_fp32_nchw_640": "PASS",
            "default_opset_12": "PASS",
            "dynamic_axes_disabled": "PASS",
            "graph_nms_absent": "PASS",
            "simplify_not_requested": "PASS",
        },
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def shape_text(shape: object) -> str:
    if not isinstance(shape, list):
        return "unknown"
    return "[" + ", ".join(str(value) for value in shape) + "]"


def render_contract(manifest: dict[str, object]) -> str:
    model = manifest["model"]
    export = manifest["export"]
    onnx_section = manifest["onnx"]
    contract = onnx_section["contract"]
    lines = [
        "# YOLOv5n v7.0 Model Contract",
        "",
        "This contract records values observed from the real Task 002 artifacts.",
        "It is not an expected-output template.",
        "",
        "## Provenance",
        "",
        f"- Source: `{model['source']['origin_url']}`",
        f"- Tag: `{model['source']['tag']}`",
        f"- Revision: `{model['source']['revision']}`",
        f"- Source-weight SHA256: `{model['source_weights']['sha256']}`",
        f"- Source-weight size: `{model['source_weights']['size_bytes']}` bytes",
        f"- Source-weight reference: `{model['source_weights']['source_reference']['url']}`",
        f"- ONNX SHA256: `{onnx_section['sha256']}`",
        f"- ONNX size: `{onnx_section['size_bytes']}` bytes",
        "",
        "## Export Configuration",
        "",
        f"- Input size: `{export['input_size']}`",
        f"- Batch: `{export['batch_size']}`",
        f"- Precision/layout: `{export['precision']} {export['layout']}`",
        f"- ONNX opset: `{export['opset']}`",
        f"- Dynamic axes: `{export['dynamic_axes']}`",
        f"- Simplify: `{export['simplify']}`",
        f"- Graph NMS requested: `{export['graph_nms_requested']}`",
        "",
        "## Observed ONNX Interface",
        "",
        "| Kind | Name | Shape | Dtype |",
        "| --- | --- | --- | --- |",
    ]
    for kind in ("inputs", "outputs"):
        label = "Input" if kind == "inputs" else "Output"
        for tensor in contract[kind]:
            lines.append(
                f"| {label} | `{tensor['name']}` | `{shape_text(tensor['shape'])}` | `{tensor['dtype']}` |"
            )
    lines.extend(
        [
            "",
            f"Observed class count: `{contract['class_count']}`.",
            "",
            "## Graph Validation",
            "",
            f"- ONNX checker: `{contract['onnx_checker']}`",
            f"- Default opset imports: `{contract['opset_imports']}`",
            f"- Node count: `{contract['node_count']}`",
            f"- Graph contains NMS: `{contract['contains_graph_nms']}`",
            "- Dynamic dimensions: none observed in the public inputs or outputs.",
            "- Simplification was not requested; the exact exporter command omits `--simplify`.",
            "",
        ]
    )
    return "\n".join(lines)


def check_manifest(model_path: Path, manifest_path: Path) -> dict[str, object]:
    regular_file(manifest_path, "model manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported manifest schema version")
    inspection = inspect_model(model_path)
    onnx_section = manifest.get("onnx", {})
    if onnx_section.get("sha256") != sha256_file(model_path):
        raise ContractError("ONNX SHA256 does not match the manifest")
    if onnx_section.get("size_bytes") != model_path.stat().st_size:
        raise ContractError("ONNX byte size does not match the manifest")
    if onnx_section.get("contract") != inspection:
        raise ContractError("current ONNX contract differs from the manifest")
    weights_section = manifest.get("model", {}).get("source_weights", {})
    weights_path = Path(weights_section.get("path", ""))
    regular_file(weights_path, "manifest source weights")
    if weights_section.get("sha256") != sha256_file(weights_path):
        raise ContractError("source-weight SHA256 does not match the manifest")
    if weights_section.get("size_bytes") != weights_path.stat().st_size:
        raise ContractError("source-weight byte size does not match the manifest")
    source_path = Path(manifest.get("model", {}).get("source", {}).get("local_path", ""))
    source = inspect_source(source_path)
    if manifest["model"]["source"] != source:
        raise ContractError("YOLOv5 source identity differs from the manifest")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-manifest", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--source-path", type=Path)
    parser.add_argument("--export-command")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--contract", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.write_manifest:
            missing = [
                name
                for name in ("weights", "source_path", "export_command", "output", "contract")
                if getattr(args, name) is None
            ]
            if missing:
                raise ContractError(f"write mode is missing arguments: {missing}")
            inspection = inspect_model(args.model)
            manifest = build_manifest(
                args.model,
                args.weights,
                args.source_path,
                args.export_command,
                inspection,
            )
            write_json(args.manifest, manifest)
            evidence = {
                "generated_at": manifest["created_at"],
                "manifest_path": str(args.manifest),
                "model_sha256": manifest["onnx"]["sha256"],
                "weights_sha256": manifest["model"]["source_weights"]["sha256"],
                "contract": inspection,
                "validation": manifest["validation"],
            }
            write_json(args.output, evidence)
            args.contract.parent.mkdir(parents=True, exist_ok=True)
            args.contract.write_text(render_contract(manifest), encoding="utf-8")
        else:
            manifest = check_manifest(args.model, args.manifest)
            inspection = manifest["onnx"]["contract"]

        print("Application: edgeai_onnx_contract_inspector")
        print(f"ONNX version: {onnx.__version__}")
        print(f"ONNX SHA256: {sha256_file(args.model)}")
        print(f"Input count: {len(inspection['inputs'])}")
        for item in inspection["inputs"]:
            print(f"Input: name={item['name']} shape={item['shape']} dtype={item['dtype']}")
        print(f"Output count: {len(inspection['outputs'])}")
        for item in inspection["outputs"]:
            print(f"Output: name={item['name']} shape={item['shape']} dtype={item['dtype']}")
        print(f"Observed class count: {inspection['class_count']}")
        print(f"Default opset: {EXPECTED_DEFAULT_OPSET}")
        print(f"Graph contains NMS: {inspection['contains_graph_nms']}")
        print("Contract validation: PASS")
        return 0
    except (ContractError, OSError, ValueError, json.JSONDecodeError, onnx.checker.ValidationError) as error:
        print(f"Contract validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
