#!/usr/bin/env python3
"""Validate Task 037 TensorRT environment, engine, and benchmark evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/037"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load(name: str) -> dict[str, Any]:
    with (EVIDENCE / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, Any]:
    environment = load("environment_audit.json")
    engines = load("engine_manifest.json")
    correctness = load("correctness.json")
    benchmark = load("benchmark.json")
    runner = load("runner_build.json")
    coco = load("coco_accuracy.json")

    require(environment["task"] == "037", "environment task mismatch")
    require(environment["environment_gate"] == "PASS", "environment gate is not PASS")
    require(environment["toolchain"]["cuda_toolkit_status"] == "INSTALLED_TOOLKIT_ONLY", "CUDA boundary changed")
    require(environment["toolchain"]["trt_package_versions"]["libnvinfer10"].startswith("10.13.3.9-1+cuda12.9"), "TensorRT version mismatch")
    require(environment["toolchain"]["linux_nvidia_display_driver_packages"] == "NOT_INSTALLED", "Linux display driver boundary changed")
    require(environment["cuda_probe"]["exit_code"] == 0, "CUDA probe failed")

    model = engines["model"]
    require(SHA256.fullmatch(model["sha256"]) is not None, "model hash malformed")
    require(model["opset"] == 12, "model opset changed")
    require(model["input"] == {"shape": [1, 3, 640, 640], "dtype": "FP32", "layout": "NCHW"}, "input contract changed")
    require(model["output"] == {"shape": [1, 25200, 85], "dtype": "FP32"}, "output contract changed")
    require(model["graph_nms"] is False, "graph NMS contract changed")

    by_id = {item["id"]: item for item in engines["engines"]}
    require(set(by_id) == {"fp32_default_tf32", "fp32_no_tf32", "fp16"}, "engine set mismatch")
    for item in by_id.values():
        require(SHA256.fullmatch(item["sha256"]) is not None, f"{item['id']} engine hash malformed")
        require(item["size_bytes"] > 0, f"{item['id']} engine size missing")
        require(item["path"].startswith("/tmp/"), f"{item['id']} engine escaped external artifact policy")
    accepted = by_id["fp32_no_tf32"]
    require(accepted["accepted"] is True and accepted["correctness_status"] == "PASS_TARGET", "FP32 candidate not accepted")
    require(by_id["fp16"]["accepted"] is True, "FP16 COCO candidate not accepted")
    require(by_id["fp16"]["correctness_status"].startswith("COCO_GATE_PASS"), "FP16 COCO status missing")

    fp32 = correctness["results"]["fp32_no_tf32"]
    require(fp32["runner_exit_code"] == 0 and fp32["status"] == "PASS_TARGET", "FP32 runner did not pass")
    require(fp32["detection_count"] == 5, "FP32 detection count mismatch")
    require(fp32["minimum_class_matched_iou"] >= 0.99, "FP32 IoU gate failed")
    require(fp32["maximum_confidence_delta"] <= 0.001, "FP32 confidence gate failed")
    fp16 = correctness["results"]["fp16"]
    require(fp16["runner_exit_code"] == 2 and "SECONDARY_DIAGNOSTIC" in fp16["status"], "FP16 secondary diagnostic missing")
    require(fp16["minimum_class_matched_iou"] < 0.99 or fp16["maximum_confidence_delta"] > 0.001, "FP16 unexpectedly passes strict gate")

    protocol = benchmark["protocol"]
    require(protocol["warmup"] == 10 and protocol["repeat"] == 100, "benchmark protocol changed")
    accepted_metrics = benchmark["accepted"]["metrics"]
    for stage in ("inference_wall_ms", "gpu_h2d_ms", "gpu_inference_ms", "gpu_d2h_ms", "preprocess_ms", "postprocess_ms", "pipeline_ms"):
        values = accepted_metrics[stage]
        require(all(values[key] > 0 for key in ("mean", "p50", "p95")), f"FP32 {stage} metrics invalid")
    require(benchmark["accepted"]["correctness"] == "PASS_TARGET", "accepted benchmark is not correct")
    require(benchmark["formal_fp16"]["correctness"] == "COCO_GATE_PASS_WITH_SECONDARY_GOLDEN_DIAGNOSTIC", "FP16 formal status missing")
    require(benchmark["formal_fp16"]["speed_result_is_accepted_after_coco_gate"] is True, "FP16 benchmark not accepted after gate")
    require(benchmark["formal_fp16"]["coco_gate"]["pass"] is True, "FP16 benchmark COCO gate failed")
    require(benchmark["trtexec_reference"]["exit_code"] == 0, "trtexec reference did not pass")

    require(runner["build"]["exit_code"] == 0, "runner build failed")
    require(SHA256.fullmatch(runner["build"]["binary_sha256"]) is not None, "runner hash malformed")
    require(runner["build"]["runtime_dependencies"]["ldd_not_found"] is False, "runner has unresolved dependencies")
    require(runner["runner_contract"]["input"] == [1, 3, 640, 640], "runner input contract mismatch")
    require(runner["runner_contract"]["output"] == [1, 25200, 85], "runner output contract mismatch")
    require(coco["status"] == "TENSORRT_FP16_READY", "COCO evidence status mismatch")
    require(coco["dataset"]["evaluation_images"] == 4500, "COCO evaluation image count mismatch")
    require(coco["dataset"]["overlap"] == 0, "COCO calibration/evaluation overlap")
    require(coco["models"]["reference_fp32_ncnn_task035"]["images"] == 4500, "secondary FP32 reference scope mismatch")
    require(coco["comparison"]["gate"] == "PASS", "FP16 accuracy gate failed")
    require(abs(coco["comparison"]["fp16_delta_mAP50"]) <= 0.01, "FP16 mAP50 gate failed")
    require(abs(coco["comparison"]["fp16_delta_mAP50_95"]) <= 0.01, "FP16 mAP50-95 gate failed")
    require(coco["comparison"]["gate_no_catastrophic_zero_detection"] is True, "FP16 catastrophic detection gate failed")

    return {
        "schema_version": 1,
        "task": "037",
        "status": "PASS",
        "environment_gate": "PASS",
        "fp32": "PASS_TARGET",
        "fp16": "TENSORRT_FP16_READY",
        "overall": "TENSORRT_FP32_AND_FP16_READY",
        "checks": {
            "model_contract": True,
            "toolkit_only_install": True,
            "cuda_probe": True,
            "engine_hashes": True,
            "fp32_correctness": True,
            "fp16_coco_accuracy_gate": True,
            "runner_build": True,
            "benchmark_protocol": True,
            "trtexec_reference": True,
        },
    }


def main() -> int:
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
