#!/usr/bin/env python3
"""Compare a real C++ preprocessing tensor with the frozen Python reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from edgeai_benchmark.preprocess import load_and_prepare_image


MAXIMUM_ABSOLUTE_DIFFERENCE = 1.0 / 255.0 + 1e-6
MAXIMUM_MEAN_ABSOLUTE_DIFFERENCE = 1e-6


class AlignmentError(RuntimeError):
    """Raised when real C++ and Python preprocessing cannot be compared."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--cpp-metadata", required=True, type=Path)
    parser.add_argument("--cpp-tensor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AlignmentError(f"failed to load JSON {path}: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise AlignmentError(f"required input is missing or empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_samples(
    python_tensor: np.ndarray,
    cpp_tensor: np.ndarray,
) -> list[dict[str, int | float]]:
    flattened_python = python_tensor.reshape(-1)
    flattened_cpp = cpp_tensor.reshape(-1)
    plane_size = int(python_tensor.shape[2] * python_tensor.shape[3])
    indices = sorted(
        {
            0,
            int(python_tensor.shape[3]) - 1,
            plane_size,
            2 * plane_size,
            len(flattened_python) // 2,
            len(flattened_python) - 1,
        }
    )
    return [
        {
            "flat_index": index,
            "python_value": float(flattened_python[index]),
            "cpp_value": float(flattened_cpp[index]),
            "absolute_difference": abs(
                float(flattened_python[index]) - float(flattened_cpp[index])
            ),
        }
        for index in indices
    ]


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    cpp_metadata = load_json(args.cpp_metadata)
    input_size = config.get("input_size")
    if (
        not isinstance(input_size, list)
        or len(input_size) != 2
        or not all(isinstance(value, int) and value > 0 for value in input_size)
    ):
        raise AlignmentError("configuration input_size must contain two positive integers")

    python_tensor, python_metadata = load_and_prepare_image(
        args.image,
        target_size=(input_size[0], input_size[1]),
    )
    cpp_shape = cpp_metadata.get("input_tensor", {}).get("shape")
    if not isinstance(cpp_shape, list) or len(cpp_shape) != 4:
        raise AlignmentError("C++ metadata tensor shape is missing or invalid")
    expected_elements = math.prod(cpp_shape)
    cpp_flat = np.fromfile(args.cpp_tensor, dtype=np.float32)
    if cpp_flat.size != expected_elements:
        raise AlignmentError(
            f"C++ tensor element count mismatch: expected {expected_elements}, "
            f"observed {cpp_flat.size}"
        )
    cpp_tensor = cpp_flat.reshape(cpp_shape)
    if not np.isfinite(python_tensor).all() or not np.isfinite(cpp_tensor).all():
        raise AlignmentError("a preprocessing tensor contains non-finite values")

    shape_match = list(python_tensor.shape) == cpp_shape
    cpp_preprocess_metadata = cpp_metadata.get("preprocess")
    metadata_match = python_metadata == cpp_preprocess_metadata
    differences = np.abs(
        python_tensor.astype(np.float64, copy=False)
        - cpp_tensor.astype(np.float64, copy=False)
    )
    maximum_difference = float(differences.max(initial=0.0))
    mean_difference = float(differences.mean()) if differences.size else 0.0
    passed = (
        shape_match
        and metadata_match
        and maximum_difference <= MAXIMUM_ABSOLUTE_DIFFERENCE
        and mean_difference <= MAXIMUM_MEAN_ABSOLUTE_DIFFERENCE
    )
    evidence = {
        "schema_version": 1,
        "application": "edgeai_compare_preprocess",
        "inputs": {
            "config": {
                "path": str(args.config),
                "sha256": sha256_file(args.config),
            },
            "image": {
                "path": str(args.image),
                "sha256": sha256_file(args.image),
            },
            "cpp_metadata": {
                "path": str(args.cpp_metadata),
                "sha256": sha256_file(args.cpp_metadata),
            },
            "cpp_tensor": {
                "path": str(args.cpp_tensor),
                "sha256": sha256_file(args.cpp_tensor),
                "size_bytes": args.cpp_tensor.stat().st_size,
            },
        },
        "python": {
            "shape": list(python_tensor.shape),
            "dtype": str(python_tensor.dtype),
            "metadata": python_metadata,
        },
        "cpp": {
            "shape": cpp_shape,
            "dtype": cpp_metadata.get("input_tensor", {}).get("dtype"),
            "metadata": cpp_preprocess_metadata,
        },
        "comparison": {
            "shape_match": shape_match,
            "metadata_match": metadata_match,
            "maximum_absolute_difference": maximum_difference,
            "mean_absolute_difference": mean_difference,
            "tolerances": {
                "maximum_absolute_difference": MAXIMUM_ABSOLUTE_DIFFERENCE,
                "maximum_mean_absolute_difference": MAXIMUM_MEAN_ABSOLUTE_DIFFERENCE,
            },
            "samples": select_samples(python_tensor, cpp_tensor),
        },
        "status": "PASS" if passed else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Python tensor shape: {list(python_tensor.shape)}")
    print(f"C++ tensor shape: {cpp_shape}")
    print(f"Metadata match: {metadata_match}")
    print(f"Maximum absolute difference: {maximum_difference:.12g}")
    print(f"Mean absolute difference: {mean_difference:.12g}")
    print(f"Alignment status: {evidence['status']}")
    print(f"Evidence: {args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AlignmentError as error:
        raise SystemExit(f"preprocess alignment error: {error}") from error
