"""Validation helpers for the frozen Task 002 ONNX model contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_SCHEMA_VERSION = 1
EXPECTED_INPUT_SHAPE = [1, 3, 640, 640]
EXPECTED_LAYOUT = "NCHW"
EXPECTED_PRECISION = "FP32"


class ContractError(RuntimeError):
    """Raised when an artifact or runtime value violates the frozen contract."""


def require_regular_file(path: Path, description: str) -> Path:
    """Return *path* after checking that it is a nonempty regular file."""
    if path.is_symlink():
        raise ContractError(f"{description} must not be a symbolic link: {path}")
    if not path.is_file():
        raise ContractError(f"{description} is missing: {path}")
    if path.stat().st_size <= 0:
        raise ContractError(f"{description} is empty: {path}")
    return path


def sha256_file(path: Path) -> str:
    """Compute SHA256 from the bytes of a validated local file."""
    require_regular_file(path, "file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_frozen_contract(manifest_path: Path, model_path: Path) -> dict[str, Any]:
    """Load the Task 002 manifest and verify the model before ORT sees it."""
    require_regular_file(manifest_path, "model manifest")
    require_regular_file(model_path, "ONNX model")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        onnx_section = manifest["onnx"]
        contract = onnx_section["contract"]
        model_hash = onnx_section["sha256"]
        export = manifest["export"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ContractError(f"invalid Task 002 manifest: {error}") from error

    if manifest.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise ContractError(
            f"expected manifest schema {EXPECTED_SCHEMA_VERSION}, "
            f"observed {manifest.get('schema_version')}"
        )
    actual_hash = sha256_file(model_path)
    if actual_hash != model_hash:
        raise ContractError(
            f"ONNX SHA256 mismatch: expected {model_hash}, observed {actual_hash}"
        )

    inputs = contract.get("inputs")
    outputs = contract.get("outputs")
    expected_input = {"name": "images", "shape": EXPECTED_INPUT_SHAPE, "dtype": "FLOAT"}
    if inputs != [expected_input]:
        raise ContractError(f"unexpected frozen input contract: {inputs}")
    if not isinstance(outputs, list) or not outputs:
        raise ContractError("frozen contract has no outputs")
    if contract.get("contains_graph_nms") is not False:
        raise ContractError("frozen contract does not confirm graph NMS is absent")
    if export.get("batch_size") != 1:
        raise ContractError(f"unexpected frozen batch size: {export.get('batch_size')}")
    if export.get("input_size") != [640, 640]:
        raise ContractError(f"unexpected frozen input size: {export.get('input_size')}")
    if export.get("layout") != EXPECTED_LAYOUT:
        raise ContractError(f"unexpected frozen layout: {export.get('layout')}")
    if export.get("precision") != EXPECTED_PRECISION:
        raise ContractError(f"unexpected frozen precision: {export.get('precision')}")

    return {
        "manifest": manifest,
        "contract": contract,
        "model_sha256": actual_hash,
    }


def ort_dtype_to_contract(ort_type: str) -> str:
    """Convert an ONNX Runtime tensor type to the manifest spelling."""
    mapping = {
        "tensor(float)": "FLOAT",
        "tensor(double)": "DOUBLE",
        "tensor(float16)": "FLOAT16",
        "tensor(int64)": "INT64",
        "tensor(int32)": "INT32",
        "tensor(uint8)": "UINT8",
    }
    try:
        return mapping[ort_type]
    except KeyError as error:
        raise ContractError(f"unsupported ONNX Runtime tensor type: {ort_type}") from error


def runtime_tensor_info(node: Any) -> dict[str, Any]:
    """Capture actual metadata from one ONNX Runtime NodeArg."""
    shape = [int(value) if isinstance(value, int) else value for value in node.shape]
    return {
        "name": node.name,
        "shape": shape,
        "dtype": ort_dtype_to_contract(node.type),
        "ort_type": node.type,
    }


def validate_runtime_io(
    runtime_inputs: list[dict[str, Any]],
    runtime_outputs: list[dict[str, Any]],
    frozen_contract: dict[str, Any],
) -> None:
    """Require actual ORT I/O to exactly match Task 002 names/shapes/dtypes."""

    def contract_view(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"name": value["name"], "shape": value["shape"], "dtype": value["dtype"]}
            for value in values
        ]

    actual_inputs = contract_view(runtime_inputs)
    actual_outputs = contract_view(runtime_outputs)
    if actual_inputs != frozen_contract["inputs"]:
        raise ContractError(
            f"runtime input contract mismatch: expected {frozen_contract['inputs']}, "
            f"observed {actual_inputs}"
        )
    if actual_outputs != frozen_contract["outputs"]:
        raise ContractError(
            f"runtime output contract mismatch: expected {frozen_contract['outputs']}, "
            f"observed {actual_outputs}"
        )


def summarize_tensor(name: str, tensor: np.ndarray) -> dict[str, Any]:
    """Return finite aggregate statistics without preserving tensor contents."""
    if not isinstance(tensor, np.ndarray):
        raise ContractError(f"tensor {name} is not a NumPy array")
    if tensor.size == 0:
        raise ContractError(f"tensor {name} is empty")
    finite = np.isfinite(tensor)
    finite_count = int(np.count_nonzero(finite))
    element_count = int(tensor.size)
    if finite_count != element_count:
        raise ContractError(
            f"tensor {name} contains {element_count - finite_count} non-finite values"
        )
    return {
        "name": name,
        "shape": [int(value) for value in tensor.shape],
        "dtype": str(tensor.dtype),
        "element_count": element_count,
        "finite_count": finite_count,
        "all_finite": True,
        "min": float(np.min(tensor)),
        "max": float(np.max(tensor)),
        "mean": float(np.mean(tensor, dtype=np.float64)),
        "std": float(np.std(tensor, dtype=np.float64)),
    }
