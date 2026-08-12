#!/usr/bin/env python3
"""Compare a TensorRT raw output dump with the frozen ORT FP32 output."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from edgeai_benchmark.preprocess import load_and_prepare_image  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--tensorrt-raw", type=Path, required=True)
    args = parser.parse_args()
    tensor, _ = load_and_prepare_image(args.image)
    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    ort_output = np.asarray(session.run(None, {session.get_inputs()[0].name: tensor})[0], dtype=np.float32)
    trt_output = np.fromfile(args.tensorrt_raw, dtype=np.float32).reshape(ort_output.shape)
    delta = np.abs(ort_output - trt_output)
    print(f"shape={list(ort_output.shape)}")
    print(f"max_abs_delta={float(delta.max()):.9g}")
    print(f"mean_abs_delta={float(delta.mean()):.9g}")
    print(f"rmse={float(np.sqrt(np.mean(np.square(ort_output - trt_output)))):.9g}")
    print(f"ort_min={float(ort_output.min()):.9g} ort_max={float(ort_output.max()):.9g}")
    print(f"trt_min={float(trt_output.min()):.9g} trt_max={float(trt_output.max()):.9g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
