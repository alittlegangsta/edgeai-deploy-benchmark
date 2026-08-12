#!/usr/bin/env python3
"""Offline validator for the Task 038 unified C++ application evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/038"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load(name: str) -> dict[str, Any]:
    with (EVIDENCE / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate() -> dict[str, Any]:
    validation = load("validation.json")
    runs = load("backend_runs.json")
    require(validation["task"] == "038", "validation task mismatch")
    require(validation["status"] == "PASS", "unified validation is not PASS")
    contract = validation["contract"]
    require("--backend ort|tensorrt|ncnn" in contract["cli"], "CLI backend contract missing")
    require(contract["model_input"] == [1, 3, 640, 640], "input contract changed")
    require(contract["model_output"] == [1, 25200, 85], "output contract changed")
    require(contract["backend_selection"].startswith("explicit"), "backend fallback policy changed")

    model = runs["model_contract"]
    require(model["onnx_sha256"] == "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121", "model hash changed")
    require(model["input"] == {"shape": [1, 3, 640, 640], "dtype": "FP32", "layout": "NCHW"}, "model input mismatch")
    require(model["output"] == {"shape": [1, 25200, 85], "dtype": "FP32"}, "model output mismatch")

    expected = {"ort_fp32", "ncnn_fp32", "tensorrt_fp32", "tensorrt_fp16"}
    expected_binaries = {
        "ort_fp32": "5a94d91abc2b46fc1c08d07503e0b1e6940afb13f97ff47132e936adf8f700c5",
        "ncnn_fp32": "5a94d91abc2b46fc1c08d07503e0b1e6940afb13f97ff47132e936adf8f700c5",
        "tensorrt_fp32": "174c30357f6e97bb45cbfbe4183e5255d30a2281ac3490220287c0de8fcc0fee",
        "tensorrt_fp16": "174c30357f6e97bb45cbfbe4183e5255d30a2281ac3490220287c0de8fcc0fee",
    }
    require(set(runs["runs"]) == expected, "backend run matrix mismatch")
    for key in expected:
        item = runs["runs"][key]
        require(item["exit_code"] == 0, f"{key} did not exit 0")
        require(SHA256.fullmatch(item["binary_sha256"]) is not None, f"{key} binary hash malformed")
        require(item["binary_sha256"] == expected_binaries[key], f"{key} binary identity drifted")
        require(item["fallback"] == "none", f"{key} fallback policy changed")
        require(item["input_shape"] == [1, 3, 640, 640], f"{key} input shape mismatch")
        require(item.get("output_shape", [1, 25200, 85]) == [1, 25200, 85], f"{key} output shape mismatch")
        for stage in ("preprocess", "inference", "postprocess", "pipeline"):
            metrics = item["timings_ms"][stage]
            require(all(metrics[name] > 0 for name in ("mean", "p50", "p95")), f"{key} {stage} timing missing")
        output = item["output_image"]
        output_path = ROOT / output["path"]
        require(output_path.is_file(), f"{key} annotated image missing")
        require(file_sha256(output_path) == output["sha256"], f"{key} annotated image hash mismatch")

    for key in ("ort_fp32", "ncnn_fp32", "tensorrt_fp32"):
        correctness = runs["runs"][key]["correctness"]
        require(correctness["status"] == "PASS_TARGET", f"{key} correctness failed")
        require(correctness["detections"] == 5, f"{key} detection count changed")
        require(correctness["minimum_iou"] >= 0.99, f"{key} IoU gate failed")
        require(correctness["maximum_confidence_delta"] <= 0.001, f"{key} confidence gate failed")

    fp16 = runs["runs"]["tensorrt_fp16"]["correctness"]
    require(fp16["status"].startswith("TASK037_COCO_GATE_PASS"), "FP16 gate provenance missing")
    require(fp16["single_image_confidence_delta"] > 0.001, "FP16 secondary diagnostic was not retained")
    require(validation["ncnn_int8"]["status"] == "EXTERNAL_MATCHING_MANIFEST_REQUIRED", "ncnn INT8 identity policy changed")
    require(validation["ncnn_int8"]["guard_probe"]["exit_code"] == 1, "ncnn INT8 guard did not reject the FP32 manifest")
    require("matching manifest" in validation["ncnn_int8"]["guard_probe"]["stderr_contains"], "ncnn INT8 guard evidence missing")
    disabled = validation["disabled_backend_probe"]
    require(disabled["exit_code"] == 1 and "unavailable" in disabled["stderr_contains"], "disabled backend rejection missing")
    require(validation["tests"]["release_ctest_ort_ncnn"] == "PASS 11/11", "ORT/ncnn CTest evidence missing")
    require(validation["tests"]["release_ctest_ort_ncnn_tensorrt"] == "PASS 11/11", "TensorRT CTest evidence missing")
    return {
        "schema_version": 1,
        "task": "038",
        "status": "PASS",
        "application": "edgeai_demo",
        "checks": {
            "contract": True,
            "ort_fp32": True,
            "ncnn_fp32": True,
            "tensorrt_fp32": True,
            "tensorrt_fp16_secondary_diagnostic": True,
            "no_fallback": True,
            "disabled_backend_rejection": True,
            "annotated_image_hashes": True,
            "ctest": True,
        },
    }


def main() -> int:
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
