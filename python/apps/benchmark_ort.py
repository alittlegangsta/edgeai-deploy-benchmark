#!/usr/bin/env python3
"""Run one independent Python ORT round for the Task 009 benchmark."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from edgeai_benchmark.benchmark import (
    BenchmarkError,
    compare_detections,
    load_json,
    sample_from_boundaries,
    validate_benchmark_config,
)
from edgeai_benchmark.model_contract import (
    load_frozen_contract,
    runtime_tensor_info,
    sha256_file,
    validate_runtime_io,
)
from edgeai_benchmark.postprocess import DetectionConfig, decode_yolov5_output
from edgeai_benchmark.preprocess import load_bgr_image, prepare_image_tensor


BACKEND = "python_ort"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-config", required=True, type=Path)
    parser.add_argument("--round", required=True, type=int, dest="round_id")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def require_hash(path: Path, expected: str, description: str) -> str:
    observed = sha256_file(path)
    if observed != expected:
        raise BenchmarkError(
            f"{description} SHA256 differs: expected {expected}, observed {observed}"
        )
    return observed


def load_inference_config(path: Path) -> tuple[DetectionConfig, tuple[int, int]]:
    value = load_json(path)
    if value.get("schema_version") != 1 or value.get("input_size") != [640, 640]:
        raise BenchmarkError("inference configuration differs from frozen 640x640 schema")
    config = DetectionConfig(
        confidence_threshold=float(value["confidence_threshold"]),
        iou_threshold=float(value["iou_threshold"]),
        class_aware_nms=value["class_aware_nms"],
        max_detections=int(value["max_detections"]),
    )
    config.validate()
    return config, (640, 640)


def environment_record(required: dict[str, str]) -> dict[str, Any]:
    observed = {name: os.environ.get(name) for name in sorted(required)}
    if observed != dict(sorted(required.items())):
        raise BenchmarkError(f"thread environment differs: {observed}")
    release = platform.release()
    if "microsoft" not in release.lower():
        raise BenchmarkError(f"benchmark requires the approved WSL2 environment: {release}")
    cpu_model = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError as error:
        raise BenchmarkError(f"failed to read CPU identity: {error}") from error
    return {
        "platform": "WSL2",
        "os": platform.system(),
        "kernel": release,
        "architecture": platform.machine(),
        "cpu_model": cpu_model,
        "logical_cpu_count": os.cpu_count(),
        "cpu_affinity": "scheduler managed",
        "cpu_pinning": "disabled",
        "environment_variables": observed,
        "python_version": platform.python_version(),
        "opencv_version": cv2.__version__,
        "onnxruntime_version": ort.__version__,
    }


def make_session(
    model: Path, manifest: Path
) -> tuple[ort.InferenceSession, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    frozen = load_frozen_contract(manifest, model)
    if ort.__version__ != "1.18.1":
        raise BenchmarkError(f"Python ORT version differs: {ort.__version__}")
    if "CPUExecutionProvider" not in ort.get_available_providers():
        raise BenchmarkError("CPUExecutionProvider is unavailable")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        str(model), sess_options=options, providers=["CPUExecutionProvider"]
    )
    if session.get_providers() != ["CPUExecutionProvider"]:
        raise BenchmarkError(f"unexpected selected providers: {session.get_providers()}")
    inputs = [runtime_tensor_info(node) for node in session.get_inputs()]
    outputs = [runtime_tensor_info(node) for node in session.get_outputs()]
    validate_runtime_io(inputs, outputs, frozen["contract"])
    return session, frozen, inputs, outputs


def pipeline(
    image: np.ndarray,
    session: ort.InferenceSession,
    runtime_inputs: list[dict[str, Any]],
    runtime_outputs: list[dict[str, Any]],
    class_names: list[str],
    detection_config: DetectionConfig,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    start = time.perf_counter_ns()
    tensor, metadata = prepare_image_tensor(image, target_size=(640, 640))
    after_preprocess = time.perf_counter_ns()
    raw_outputs = session.run(
        [item["name"] for item in runtime_outputs],
        {runtime_inputs[0]["name"]: tensor},
    )
    after_inference = time.perf_counter_ns()
    if len(raw_outputs) != 1 or raw_outputs[0].dtype != np.float32:
        raise BenchmarkError("ORT output count or dtype differs from frozen contract")
    if list(raw_outputs[0].shape) != runtime_outputs[0]["shape"]:
        raise BenchmarkError("ORT output shape changed during benchmark")
    postprocessed = decode_yolov5_output(
        raw_outputs[0], class_names, metadata, detection_config
    )
    after_postprocess = time.perf_counter_ns()
    sample = sample_from_boundaries(
        after_preprocess - start,
        after_inference - after_preprocess,
        after_postprocess - after_inference,
    )
    return sample, postprocessed["detections"]


def append_round(path: Path, config_sha256: str, round_value: dict[str, Any]) -> None:
    if path.exists():
        payload = load_json(path)
        if payload.get("backend") != BACKEND:
            raise BenchmarkError("existing output belongs to another backend")
        if payload.get("benchmark_config_sha256") != config_sha256:
            raise BenchmarkError("existing output uses another benchmark configuration")
        rounds = payload.get("rounds")
        if not isinstance(rounds, list):
            raise BenchmarkError("existing output rounds are invalid")
    else:
        payload = {
            "schema_version": 1,
            "evidence_type": "task009_raw_benchmark",
            "backend": BACKEND,
            "benchmark_config_sha256": config_sha256,
            "rounds": [],
        }
        rounds = payload["rounds"]
    expected_round = len(rounds) + 1
    if round_value["round"] != expected_round:
        raise BenchmarkError(
            f"round append must be sequential: expected {expected_round}, "
            f"observed {round_value['round']}"
        )
    rounds.append(round_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    process_started_unix_ns = time.time_ns()
    config = load_json(args.benchmark_config)
    validate_benchmark_config(config)
    if not 1 <= args.round_id <= config["rounds"]["count"]:
        raise BenchmarkError("round must be in [1, 5]")
    config_sha256 = sha256_file(args.benchmark_config)
    workload = config["workload"]
    required_environment = config["environment"]["required_environment_variables"]
    environment = environment_record(required_environment)
    cv2.setNumThreads(config["runtime"]["opencv_threads"])
    if cv2.getNumThreads() != 1:
        raise BenchmarkError(f"OpenCV thread count differs: {cv2.getNumThreads()}")

    paths = {
        key: Path(workload[key]["path"])
        for key in ("model", "manifest", "image", "inference_config", "golden_result")
    }
    hashes = {
        key: require_hash(paths[key], workload[key]["sha256"], key)
        for key in paths
    }
    detection_config, input_size = load_inference_config(paths["inference_config"])
    image = load_bgr_image(paths["image"])
    if [image.shape[1], image.shape[0]] != [1280, 960]:
        raise BenchmarkError(f"reference image dimensions changed: {image.shape}")

    model_load_start = time.perf_counter_ns()
    session, frozen, runtime_inputs, runtime_outputs = make_session(
        paths["model"], paths["manifest"]
    )
    model_load_end = time.perf_counter_ns()
    model_load_ms = (model_load_end - model_load_start) / 1_000_000.0

    golden = load_json(paths["golden_result"])["detections"]
    correctness_config = config["correctness"]
    _, before_detections = pipeline(
        image,
        session,
        runtime_inputs,
        runtime_outputs,
        frozen["contract"]["class_names"],
        detection_config,
    )
    correctness_before = compare_detections(
        golden,
        before_detections,
        correctness_config["minimum_class_matched_iou"],
        correctness_config["maximum_absolute_confidence_difference"],
    )

    for _ in range(config["rounds"]["warmup"]):
        pipeline(
            image,
            session,
            runtime_inputs,
            runtime_outputs,
            frozen["contract"]["class_names"],
            detection_config,
        )

    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    wall_start_ns = time.perf_counter_ns()
    samples = []
    for iteration in range(1, config["rounds"]["repeat"] + 1):
        sample, _ = pipeline(
            image,
            session,
            runtime_inputs,
            runtime_outputs,
            frozen["contract"]["class_names"],
            detection_config,
        )
        sample["round"] = args.round_id
        sample["iteration"] = iteration
        sample["aggregate_sample_index"] = (
            (args.round_id - 1) * config["rounds"]["repeat"] + iteration
        )
        samples.append(sample)
    wall_end_ns = time.perf_counter_ns()
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    peak_rss_bytes = int(usage_after.ru_maxrss) * 1024
    cpu_seconds = (
        usage_after.ru_utime
        + usage_after.ru_stime
        - usage_before.ru_utime
        - usage_before.ru_stime
    )
    wall_seconds = (wall_end_ns - wall_start_ns) / 1_000_000_000.0
    cpu_percent = 100.0 * cpu_seconds / wall_seconds

    _, after_detections = pipeline(
        image,
        session,
        runtime_inputs,
        runtime_outputs,
        frozen["contract"]["class_names"],
        detection_config,
    )
    correctness_after = compare_detections(
        golden,
        after_detections,
        correctness_config["minimum_class_matched_iou"],
        correctness_config["maximum_absolute_confidence_difference"],
    )
    round_value = {
        "round": args.round_id,
        "process_id": os.getpid(),
        "process_started_unix_ns": process_started_unix_ns,
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model_load_ms": model_load_ms,
        "model_sha256": hashes["model"],
        "image_sha256": hashes["image"],
        "manifest_sha256": hashes["manifest"],
        "inference_config_sha256": hashes["inference_config"],
        "golden_result_sha256": hashes["golden_result"],
        "runtime": {
            **config["runtime"],
            "selected_providers": session.get_providers(),
            "runtime_inputs": runtime_inputs,
            "runtime_outputs": runtime_outputs,
        },
        "environment": environment,
        "warmup_iterations": config["rounds"]["warmup"],
        "formal_iterations": config["rounds"]["repeat"],
        "resource_measurement": {
            "process_cpu_percent_one_core_basis": cpu_percent,
            "process_cpu_time_delta_seconds": cpu_seconds,
            "wall_clock_time_delta_seconds": wall_seconds,
            "peak_rss_bytes": peak_rss_bytes,
            "peak_rss_scope": "process startup through formal measurement completion",
            "peak_rss_is_process_level_not_model_only": True,
            "language_scope_note": "includes Python interpreter and imported modules",
        },
        "correctness": {
            "before_warmup": correctness_before,
            "after_measurement": correctness_after,
        },
        "samples": samples,
    }
    append_round(args.output, config_sha256, round_value)
    return round_value


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
    except Exception as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        return 1
    print(f"backend={BACKEND}")
    print(f"round={result['round']}")
    print(f"process_id={result['process_id']}")
    print(f"model_load_ms={result['model_load_ms']:.6f}")
    print(f"formal_samples={len(result['samples'])}")
    print(
        "process_cpu_percent_one_core_basis="
        f"{result['resource_measurement']['process_cpu_percent_one_core_basis']:.6f}"
    )
    print(f"peak_rss_bytes={result['resource_measurement']['peak_rss_bytes']}")
    print("correctness_before=PASS")
    print("correctness_after=PASS")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
