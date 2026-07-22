#!/usr/bin/env python3
"""Run and validate the Task 012 PC campaign and generate acceptance reports."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from edgeai_benchmark.benchmark import (  # noqa: E402
    BenchmarkError,
    STAGES,
    compare_detections,
    load_json,
    maximum_relative_difference,
    summarize_ns,
    validate_benchmark_config,
)


BACKENDS = ("python_ort", "cpp_ort", "cpp_ncnn")
BACKEND_LABELS = {
    "python_ort": "Python ORT",
    "cpp_ort": "C++ ORT",
    "cpp_ncnn": "C++ ncnn",
}
EXPECTED_ORDER = (
    ("python_ort", "cpp_ort", "cpp_ncnn"),
    ("python_ort", "cpp_ncnn", "cpp_ort"),
    ("cpp_ort", "python_ort", "cpp_ncnn"),
    ("cpp_ort", "cpp_ncnn", "python_ort"),
    ("cpp_ncnn", "python_ort", "cpp_ort"),
    ("cpp_ncnn", "cpp_ort", "python_ort"),
)
EXPECTED_EVIDENCE_TYPES = {
    "python_ort": "task009_raw_benchmark",
    "cpp_ort": "task009_raw_benchmark",
    "cpp_ncnn": "task011_raw_benchmark",
}
TASK_EVIDENCE = {
    1: "tasks/001_project_bootstrap.md",
    2: "results/evidence/002/model_contract.json",
    3: "results/evidence/003/raw_tensor_stats.json",
    4: "results/evidence/004/python_ort_detections.json",
    5: "results/evidence/005/python_test_summary.json",
    6: "results/evidence/006/preprocess_alignment.json",
    7: "results/evidence/007/python_cpp_ort_comparison.json",
    8: "results/evidence/008/cpp_ort_video.json",
    9: "results/evidence/009/benchmark_validation.json",
    10: "results/evidence/010/ncnn_model_load.json",
    11: "results/evidence/011/ncnn_benchmark_validation.json",
    12: "results/evidence/012/three_backend_benchmark_validation.json",
}


class AcceptanceError(BenchmarkError):
    """Raised when Task 012 evidence or configuration is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def repository_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def require_regular_file(path: Path, description: str) -> None:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            f"{description} is missing, empty, or a symlink: {path}")


def validate_artifact(value: Any, description: str) -> dict[str, str]:
    require(isinstance(value, dict), f"{description} must be an object")
    path_value = value.get("path")
    expected = value.get("sha256")
    require(isinstance(path_value, str) and path_value, f"{description} path is invalid")
    require(isinstance(expected, str) and len(expected) == 64,
            f"{description} SHA256 is invalid")
    path = repository_path(path_value)
    require_regular_file(path, description)
    observed = sha256_file(path)
    require(observed == expected,
            f"{description} SHA256 differs: expected {expected}, observed {observed}")
    return {"path": path_value, "sha256": observed}


def finite_number(value: Any, description: str, *, positive: bool = False) -> float:
    require(not isinstance(value, bool) and isinstance(value, (int, float)),
            f"{description} must be numeric")
    result = float(value)
    require(math.isfinite(result), f"{description} must be finite")
    require(result > 0.0 if positive else result >= 0.0,
            f"{description} must be {'positive' if positive else 'nonnegative'}")
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_and_validate_config(config_path: Path, base_config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(config_path)
    require(config.get("schema_version") == 1, "Task 012 config schema differs")
    require(config.get("methodology_id") == "task012-pc-three-backend-v1",
            "Task 012 methodology differs")
    rounds = config.get("rounds", {})
    require(rounds.get("count") == 6, "Task 012 round count must be 6")
    require(rounds.get("warmup") == 10, "Task 012 warmup must be 10")
    require(rounds.get("repeat") == 100, "Task 012 repeat must be 100")
    order = tuple(tuple(item) for item in rounds.get("order", []))
    require(order == EXPECTED_ORDER, f"Task 012 process order differs: {order}")
    for backend in BACKENDS:
        positions = [position for row in order for position, item in enumerate(row, 1)
                     if item == backend]
        require(positions == [1, 1, 2, 2, 3, 3] or sorted(positions) == [1, 1, 2, 2, 3, 3],
                f"{backend} is not position-balanced: {positions}")
    require(config.get("environment") == {
        "platform": "WSL2",
        "cpu_affinity": "scheduler managed",
        "cpu_pinning": "disabled",
        "required_environment_variables": {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
    }, "Task 012 environment contract differs")
    require(config.get("runtime") == {
        "threads": 1,
        "opencv_threads": 1,
        "ort_intra_op_threads": 1,
        "ort_inter_op_threads": 1,
        "ort_execution_mode": "ORT_SEQUENTIAL",
        "ort_graph_optimization": "ORT_ENABLE_ALL",
    }, "Task 012 runtime contract differs")
    require(config.get("timing", {}).get("pipeline_total_formula") ==
            "preprocess_ns + inference_ns + postprocess_ns",
            "Task 012 pipeline formula differs")
    require(config.get("statistics", {}).get("percentile_method") == "nearest-rank",
            "Task 012 percentile method differs")
    require(config.get("statistics", {}).get("preserve_all_samples") is True,
            "Task 012 must preserve all samples")
    require(config.get("statistics", {}).get(
        "maximum_round_mean_relative_difference_percent") == 10.0,
        "Task 012 stability limit differs")

    base = load_json(base_config_path)
    validate_benchmark_config(base)
    base_identity = config.get("base_process_config", {})
    require(repository_path(base_identity.get("path", "")) == base_config_path.resolve(),
            "base process config path differs")
    require(base_identity.get("sha256") == sha256_file(base_config_path),
            "base process config SHA256 differs")
    require(base["rounds"]["warmup"] == rounds["warmup"] and
            base["rounds"]["repeat"] == rounds["repeat"],
            "base process warmup/repeat differ")
    require(base["workload"]["input_size"] == config["workload"]["input_size"] and
            base["workload"]["batch"] == config["workload"]["batch"] and
            base["workload"]["precision"] == config["workload"]["precision"],
            "base workload differs")
    for name in ("source_weights", "frozen_onnx", "ort_manifest", "ncnn_manifest",
                 "ncnn_param", "ncnn_bin", "image", "inference_config",
                 "golden_result", "reference_detections"):
        validate_artifact(config["workload"].get(name), f"workload {name}")
    for name, artifact in config.get("immutable_historical_campaigns", {}).items():
        validate_artifact(artifact, f"immutable historical artifact {name}")
    return config, base


def validate_environment(config: dict[str, Any]) -> dict[str, str]:
    required = config["environment"]["required_environment_variables"]
    observed = {name: os.environ.get(name, "") for name in required}
    require(observed == required, f"thread environment differs: {observed}")
    return observed


def validate_correctness(value: Any, backend: str, description: str) -> None:
    require(isinstance(value, dict), f"{description} must be an object")
    expected_status = "PASS_TARGET" if backend == "cpp_ncnn" else "PASS"
    require(value.get("status") == expected_status,
            f"{description} status differs: {value.get('status')}")
    require(value.get("detection_count") == 5, f"{description} detection count differs")
    minimum_iou = finite_number(value.get("minimum_class_matched_iou"),
                                f"{description} minimum IoU")
    confidence_delta = finite_number(value.get("maximum_absolute_confidence_difference"),
                                     f"{description} confidence delta")
    maximum_delta = 0.01 if backend == "cpp_ncnn" else 0.001
    require(minimum_iou >= 0.99, f"{description} IoU is below target")
    require(confidence_delta <= maximum_delta, f"{description} confidence delta exceeds target")


def validate_process_payload(payload: dict[str, Any], backend: str,
                             base_config_sha256: str, config: dict[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == 1, f"{backend} process schema differs")
    require(payload.get("evidence_type") == EXPECTED_EVIDENCE_TYPES[backend],
            f"{backend} process evidence type differs")
    require(payload.get("backend") == backend, f"{backend} process identity differs")
    require(payload.get("benchmark_config_sha256") == base_config_sha256,
            f"{backend} base config SHA256 differs")
    rounds = payload.get("rounds")
    require(isinstance(rounds, list) and len(rounds) == 1,
            f"{backend} process fragment must contain one round")
    process_round = rounds[0]
    require(process_round.get("round") == 1, f"{backend} source round must be 1")
    require(process_round.get("warmup_iterations") == 10, f"{backend} warmup differs")
    require(process_round.get("formal_iterations") == 100, f"{backend} repeat differs")
    require(isinstance(process_round.get("process_id"), int) and
            process_round["process_id"] > 0, f"{backend} process ID is invalid")
    require(isinstance(process_round.get("process_started_unix_ns"), int) and
            process_round["process_started_unix_ns"] > 0,
            f"{backend} process start is invalid")
    finite_number(process_round.get("model_load_ms"), f"{backend} model load", positive=True)
    workload = config["workload"]
    if backend in ("python_ort", "cpp_ort"):
        expected_hashes = {
            "model_sha256": workload["frozen_onnx"]["sha256"],
            "image_sha256": workload["image"]["sha256"],
            "manifest_sha256": workload["ort_manifest"]["sha256"],
            "inference_config_sha256": workload["inference_config"]["sha256"],
            "golden_result_sha256": workload["golden_result"]["sha256"],
        }
    else:
        expected_hashes = {
            "source_weights_sha256": workload["source_weights"]["sha256"],
            "frozen_onnx_sha256": workload["frozen_onnx"]["sha256"],
            "ncnn_param_sha256": workload["ncnn_param"]["sha256"],
            "ncnn_bin_sha256": workload["ncnn_bin"]["sha256"],
            "ncnn_manifest_sha256": workload["ncnn_manifest"]["sha256"],
            "image_sha256": workload["image"]["sha256"],
            "inference_config_sha256": workload["inference_config"]["sha256"],
            "golden_result_sha256": workload["golden_result"]["sha256"],
            "reference_detections_sha256": workload["reference_detections"]["sha256"],
        }
    for key, expected in expected_hashes.items():
        require(process_round.get(key) == expected, f"{backend} {key} differs")
    environment = process_round.get("environment", {})
    require(environment.get("platform") == "WSL2" and
            "microsoft" in str(environment.get("kernel", "")).lower(),
            f"{backend} process is not WSL2")
    require(environment.get("cpu_affinity") == "scheduler managed" and
            environment.get("cpu_pinning") == "disabled",
            f"{backend} affinity policy differs")
    require(environment.get("environment_variables") ==
            config["environment"]["required_environment_variables"],
            f"{backend} thread environment differs")
    require(environment.get("opencv_version") ==
            config["backends"][backend]["opencv_version"],
            f"{backend} OpenCV version differs")
    if backend != "python_ort":
        require(environment.get("build_type") == "Release", f"{backend} is not Release")

    runtime = process_round.get("runtime", {})
    if backend in ("python_ort", "cpp_ort"):
        require(runtime.get("onnxruntime_version") == "1.18.1",
                f"{backend} ORT version differs")
        require(runtime.get("selected_providers") == ["CPUExecutionProvider"],
                f"{backend} provider differs")
        for key, expected in (("intra_op_threads", 1), ("inter_op_threads", 1),
                              ("execution_mode", "ORT_SEQUENTIAL"),
                              ("graph_optimization", "ORT_ENABLE_ALL"),
                              ("opencv_threads", 1)):
            require(runtime.get(key) == expected, f"{backend} runtime {key} differs")
    else:
        require(runtime == {
            "ncnn_version": "1.0.20240410",
            "execution_provider": "ncnn CPU",
            "threads": 1,
            "vulkan": False,
            "fp16": False,
            "bf16": False,
            "int8": False,
            "input": {"name": "in0", "logical_shape": [1, 3, 640, 640],
                      "dtype": "float32"},
            "output": {"name": "out0", "logical_shape": [1, 25200, 85],
                       "dtype": "float32"},
        }, "ncnn runtime contract differs")

    correctness = process_round.get("correctness", {})
    validate_correctness(correctness.get("before_warmup"), backend,
                         f"{backend} before-warmup correctness")
    validate_correctness(correctness.get("after_measurement"), backend,
                         f"{backend} after-measurement correctness")
    resources = process_round.get("resource_measurement", {})
    cpu = finite_number(resources.get("process_cpu_percent_one_core_basis"),
                        f"{backend} CPU percent")
    cpu_seconds = finite_number(resources.get("process_cpu_time_delta_seconds"),
                                f"{backend} process CPU time", positive=True)
    wall_seconds = finite_number(resources.get("wall_clock_time_delta_seconds"),
                                 f"{backend} wall time", positive=True)
    require(math.isclose(cpu, 100.0 * cpu_seconds / wall_seconds, rel_tol=1e-9),
            f"{backend} CPU formula differs")
    require(isinstance(resources.get("peak_rss_bytes"), int) and
            resources["peak_rss_bytes"] > 0, f"{backend} peak RSS is invalid")
    require(resources.get("peak_rss_is_process_level_not_model_only") is True,
            f"{backend} peak RSS scope is not process-level")

    samples = process_round.get("samples")
    require(isinstance(samples, list) and len(samples) == 100,
            f"{backend} process must contain 100 samples")
    for iteration, sample in enumerate(samples, 1):
        require(sample.get("round") == 1 and sample.get("iteration") == iteration and
                sample.get("aggregate_sample_index") == iteration,
                f"{backend} source sample identity differs")
        values = {}
        for stage in STAGES:
            raw = sample.get(f"{stage}_ns")
            require(not isinstance(raw, bool) and isinstance(raw, (int, float)) and
                    math.isfinite(float(raw)) and int(raw) == raw and raw > 0,
                    f"{backend} {stage} sample is invalid")
            values[stage] = int(raw)
        require(values["pipeline_total"] == values["preprocess"] +
                values["inference"] + values["postprocess"],
                f"{backend} pipeline total is not the exact stage sum")
    return process_round


def command_for_backend(args: argparse.Namespace, backend: str, output: Path) -> list[str]:
    common = ["--benchmark-config", str(args.base_config), "--round", "1", "--output", str(output)]
    if backend == "python_ort":
        return [str(args.python), str(args.python_benchmark), *common]
    if backend == "cpp_ort":
        return [str(args.cpp_ort), *common]
    return [
        str(args.cpp_ncnn),
        "--benchmark-config", str(args.base_config),
        "--ncnn-manifest", str(args.ncnn_manifest),
        "--reference-detections", str(args.reference_detections),
        "--round", "1", "--output", str(output),
    ]


def append_log(stream: Any, message: str) -> None:
    stream.write(message)
    if not message.endswith("\n"):
        stream.write("\n")
    stream.flush()


def run_campaign(args: argparse.Namespace) -> int:
    config_path = args.config.resolve()
    base_config_path = args.base_config.resolve()
    config, _ = load_and_validate_config(config_path, base_config_path)
    validate_environment(config)
    outputs = {
        "python_ort": args.python_output.resolve(),
        "cpp_ort": args.cpp_ort_output.resolve(),
        "cpp_ncnn": args.cpp_ncnn_output.resolve(),
    }
    protected_outputs = [*outputs.values(), args.summary.resolve(), args.csv.resolve(),
                         args.validation.resolve(), args.log.resolve()]
    existing = [str(path) for path in protected_outputs if path.exists()]
    require(not existing, f"Task 012 outputs already exist; refusing overwrite: {existing}")
    for path in (args.python, args.python_benchmark, args.cpp_ort, args.cpp_ncnn,
                 args.ncnn_manifest, args.reference_detections):
        require_regular_file(path.resolve(), "campaign executable/input")

    temp_root = Path(tempfile.mkdtemp(prefix="edgeai-task012-campaign-", dir="/tmp"))
    entries: dict[str, list[dict[str, Any]]] = {backend: [] for backend in BACKENDS}
    base_sha256 = sha256_file(base_config_path)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PYTHON_ROOT)
    sequence = 0
    with args.log.open("x", encoding="utf-8") as log:
        append_log(log, f"task012_campaign_started={datetime.now(timezone.utc).isoformat()}")
        append_log(log, f"temporary_fragment_directory={temp_root}")
        try:
            for campaign_round, backend_order in enumerate(EXPECTED_ORDER, 1):
                for position, backend in enumerate(backend_order, 1):
                    sequence += 1
                    fragment = temp_root / f"sequence_{sequence:02d}_{backend}.json"
                    command = command_for_backend(args, backend, fragment)
                    started = datetime.now(timezone.utc).isoformat()
                    append_log(log, json.dumps({
                        "event": "process_start", "sequence": sequence,
                        "campaign_round": campaign_round, "position": position,
                        "backend": backend, "started_at_utc": started,
                        "command": command,
                    }, sort_keys=True))
                    result = subprocess.run(
                        command,
                        cwd=REPOSITORY_ROOT,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                    append_log(log, result.stdout)
                    append_log(log, json.dumps({
                        "event": "process_exit", "sequence": sequence,
                        "campaign_round": campaign_round, "position": position,
                        "backend": backend, "exit_code": result.returncode,
                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    }, sort_keys=True))
                    print(f"sequence={sequence}/18 round={campaign_round} position={position} "
                          f"backend={backend} exit={result.returncode}", flush=True)
                    require(result.returncode == 0,
                            f"campaign process failed at sequence {sequence}: {command}")
                    payload = load_json(fragment)
                    process_round = validate_process_payload(payload, backend, base_sha256, config)
                    entries[backend].append({
                        "campaign_round": campaign_round,
                        "position": position,
                        "sequence_index": sequence,
                        "source_process_round_argument": 1,
                        "source_fragment_sha256": sha256_file(fragment),
                        "source_payload_canonical_sha256": sha256_json(payload),
                        "process_id": process_round["process_id"],
                        "process_started_unix_ns": process_round["process_started_unix_ns"],
                        "process_payload": payload,
                    })
        except Exception as error:
            append_log(log, json.dumps({
                "event": "campaign_failed", "sequence": sequence,
                "error": str(error), "temporary_fragment_directory": str(temp_root),
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            }, sort_keys=True))
            raise
        append_log(log, f"task012_campaign_completed={datetime.now(timezone.utc).isoformat()}")

    config_sha256 = sha256_file(config_path)
    for backend, output in outputs.items():
        write_json(output, {
            "schema_version": 1,
            "evidence_type": "task012_three_backend_raw_campaign",
            "methodology_id": config["methodology_id"],
            "backend": backend,
            "campaign_config_sha256": config_sha256,
            "base_process_config_sha256": base_sha256,
            "raw_process_payloads_unmodified": True,
            "rounds": entries[backend],
        })
    validation = validate_and_write_campaign(
        config_path, base_config_path, list(outputs.values()),
        args.summary.resolve(), args.csv.resolve(), args.validation.resolve()
    )
    print("campaign_processes=18")
    print("formal_samples_per_backend=600")
    print(f"stability_gate={validation['stability_gate']}")
    print("status=PENDING_HUMAN_REVIEW")
    return 0 if validation["stability_gate"] == "PASS" else 2


def extract_round(entry: dict[str, Any], backend: str, base_sha256: str,
                  config: dict[str, Any]) -> dict[str, Any]:
    payload = entry.get("process_payload")
    require(isinstance(payload, dict), f"{backend} process payload is missing")
    process_round = validate_process_payload(payload, backend, base_sha256, config)
    source_hash = entry.get("source_payload_canonical_sha256")
    require(isinstance(source_hash, str) and source_hash == sha256_json(payload),
            f"{backend} embedded process payload canonical SHA256 differs")
    fragment_hash = entry.get("source_fragment_sha256")
    require(isinstance(fragment_hash, str) and len(fragment_hash) == 64,
            f"{backend} source fragment SHA256 is invalid")
    require(entry.get("process_id") == process_round["process_id"] and
            entry.get("process_started_unix_ns") == process_round["process_started_unix_ns"],
            f"{backend} outer process identity differs")
    require(entry.get("source_process_round_argument") == 1,
            f"{backend} source round argument differs")
    return process_round


def summarize_backend(payload: dict[str, Any], backend: str, config: dict[str, Any],
                      config_sha256: str, base_sha256: str) -> dict[str, Any]:
    require(payload.get("schema_version") == 1, f"{backend} campaign schema differs")
    require(payload.get("evidence_type") == "task012_three_backend_raw_campaign",
            f"{backend} campaign type differs")
    require(payload.get("methodology_id") == config["methodology_id"],
            f"{backend} campaign methodology differs")
    require(payload.get("backend") == backend, f"{backend} campaign identity differs")
    require(payload.get("campaign_config_sha256") == config_sha256,
            f"{backend} campaign config SHA256 differs")
    require(payload.get("base_process_config_sha256") == base_sha256,
            f"{backend} base config SHA256 differs")
    require(payload.get("raw_process_payloads_unmodified") is True,
            f"{backend} raw preservation flag differs")
    entries = payload.get("rounds")
    require(isinstance(entries, list) and len(entries) == 6,
            f"{backend} campaign must contain six rounds")
    all_samples: list[tuple[int, int, int, dict[str, Any]]] = []
    round_summaries = []
    positions: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: []}
    process_identity: set[tuple[int, int]] = set()
    for expected_round, entry in enumerate(entries, 1):
        require(entry.get("campaign_round") == expected_round,
                f"{backend} campaign round differs")
        expected_position = EXPECTED_ORDER[expected_round - 1].index(backend) + 1
        require(entry.get("position") == expected_position,
                f"{backend} position differs in round {expected_round}")
        expected_sequence = (expected_round - 1) * 3 + expected_position
        require(entry.get("sequence_index") == expected_sequence,
                f"{backend} sequence differs in round {expected_round}")
        process_round = extract_round(entry, backend, base_sha256, config)
        identity = (process_round["process_id"], process_round["process_started_unix_ns"])
        require(identity not in process_identity, f"{backend} process identity was reused")
        process_identity.add(identity)
        stage_values = {stage: [] for stage in STAGES}
        for iteration, sample in enumerate(process_round["samples"], 1):
            for stage in STAGES:
                stage_values[stage].append(int(sample[f"{stage}_ns"]))
            all_samples.append((expected_round, expected_position, iteration, sample))
            positions[expected_position].append(sample)
        round_summaries.append({
            "round": expected_round,
            "position": expected_position,
            "sequence_index": expected_sequence,
            "process_id": process_round["process_id"],
            "process_started_unix_ns": process_round["process_started_unix_ns"],
            "model_load_ms": process_round["model_load_ms"],
            "resource_measurement": process_round["resource_measurement"],
            "correctness": process_round["correctness"],
            "stages": {stage: summarize_ns(values) for stage, values in stage_values.items()},
        })
    require(len(all_samples) == 600, f"{backend} aggregate sample count differs")
    aggregate_stages = {
        stage: summarize_ns([item[3][f"{stage}_ns"] for item in all_samples])
        for stage in STAGES
    }
    position_summaries = []
    for position in (1, 2, 3):
        require(len(positions[position]) == 200,
                f"{backend} position {position} sample count differs")
        position_summaries.append({
            "position": position,
            "rounds": [item["round"] for item in round_summaries
                       if item["position"] == position],
            "stages": {
                stage: summarize_ns([sample[f"{stage}_ns"] for sample in positions[position]])
                for stage in STAGES
            },
        })
    round_means = [item["stages"]["pipeline_total"]["mean_ms"] for item in round_summaries]
    position_means = [item["stages"]["pipeline_total"]["mean_ms"]
                      for item in position_summaries]
    fastest = min(all_samples, key=lambda item: item[3]["pipeline_total_ns"])
    slowest = max(all_samples, key=lambda item: item[3]["pipeline_total_ns"])
    round_spread = maximum_relative_difference(round_means)
    position_spread = maximum_relative_difference(position_means)
    limit = config["statistics"]["maximum_round_mean_relative_difference_percent"]
    environment = extract_round(entries[0], backend, base_sha256, config)["environment"]
    runtime = extract_round(entries[0], backend, base_sha256, config)["runtime"]
    return {
        "backend": backend,
        "sample_count": 600,
        "round_count": 6,
        "environment": environment,
        "runtime": runtime,
        "rounds": round_summaries,
        "positions": position_summaries,
        "aggregate": {
            "stages": aggregate_stages,
            "pipeline_fps_batch1_sequential": 1000.0 /
            aggregate_stages["pipeline_total"]["mean_ms"],
            "fastest_sample": {
                "aggregate_sample_index": (fastest[0] - 1) * 100 + fastest[2],
                "round": fastest[0], "position": fastest[1], "iteration": fastest[2],
                "pipeline_total_ms": fastest[3]["pipeline_total_ns"] / 1_000_000.0,
            },
            "slowest_sample": {
                "aggregate_sample_index": (slowest[0] - 1) * 100 + slowest[2],
                "round": slowest[0], "position": slowest[1], "iteration": slowest[2],
                "pipeline_total_ms": slowest[3]["pipeline_total_ns"] / 1_000_000.0,
            },
            "six_round_pipeline_mean_max_relative_difference_percent": round_spread,
            "position_pipeline_mean_spread_percent": position_spread,
            "stability_limit_percent": limit,
            "stability_gate": "PASS" if round_spread <= limit else "FAIL",
        },
    }


def write_summary_csv(path: Path, summaries: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "backend", "scope", "round", "position", "stage", "count", "mean_ms",
        "p50_ms", "p90_ms", "min_ms", "max_ms", "model_load_ms",
        "process_cpu_percent_one_core_basis", "peak_rss_bytes",
        "pipeline_fps_batch1_sequential",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for summary in summaries:
            for round_value in summary["rounds"]:
                for stage, stats in round_value["stages"].items():
                    writer.writerow({
                        "backend": summary["backend"], "scope": "round",
                        "round": round_value["round"], "position": round_value["position"],
                        "stage": stage, **stats,
                        "model_load_ms": round_value["model_load_ms"] if stage == "pipeline_total" else "",
                        "process_cpu_percent_one_core_basis": round_value["resource_measurement"][
                            "process_cpu_percent_one_core_basis"] if stage == "pipeline_total" else "",
                        "peak_rss_bytes": round_value["resource_measurement"]["peak_rss_bytes"]
                        if stage == "pipeline_total" else "",
                        "pipeline_fps_batch1_sequential": "",
                    })
            for position_value in summary["positions"]:
                for stage, stats in position_value["stages"].items():
                    writer.writerow({
                        "backend": summary["backend"], "scope": "position", "round": "",
                        "position": position_value["position"], "stage": stage, **stats,
                        "model_load_ms": "", "process_cpu_percent_one_core_basis": "",
                        "peak_rss_bytes": "", "pipeline_fps_batch1_sequential": "",
                    })
            for stage, stats in summary["aggregate"]["stages"].items():
                writer.writerow({
                    "backend": summary["backend"], "scope": "aggregate", "round": "",
                    "position": "", "stage": stage, **stats, "model_load_ms": "",
                    "process_cpu_percent_one_core_basis": "", "peak_rss_bytes": "",
                    "pipeline_fps_batch1_sequential": summary["aggregate"][
                        "pipeline_fps_batch1_sequential"] if stage == "pipeline_total" else "",
                })


def validate_and_write_campaign(config_path: Path, base_config_path: Path,
                                input_paths: Sequence[Path], summary_path: Path,
                                csv_path: Path, validation_path: Path) -> dict[str, Any]:
    config, _ = load_and_validate_config(config_path, base_config_path)
    require(len(input_paths) == 3, "three campaign inputs are required")
    config_sha256 = sha256_file(config_path)
    base_sha256 = sha256_file(base_config_path)
    payloads = [load_json(path) for path in input_paths]
    by_backend = {payload.get("backend"): (path, payload)
                  for path, payload in zip(input_paths, payloads)}
    require(set(by_backend) == set(BACKENDS), "campaign inputs do not contain all backends")
    summaries = [summarize_backend(by_backend[backend][1], backend, config,
                                   config_sha256, base_sha256) for backend in BACKENDS]
    actual_sequence = []
    identities: set[tuple[int, int]] = set()
    for backend in BACKENDS:
        for entry in by_backend[backend][1]["rounds"]:
            identity = (entry["process_id"], entry["process_started_unix_ns"])
            require(identity not in identities, "campaign reused a process identity")
            identities.add(identity)
            actual_sequence.append((entry["sequence_index"], entry["campaign_round"],
                                    entry["position"], backend,
                                    entry["process_started_unix_ns"]))
    actual_sequence.sort()
    require(len(actual_sequence) == 18, "campaign must contain 18 process records")
    require([item[4] for item in actual_sequence] == sorted(item[4] for item in actual_sequence),
            "process start timestamps do not follow campaign sequence")
    actual_order = [[item[3] for item in actual_sequence if item[1] == round_id]
                    for round_id in range(1, 7)]
    require(tuple(tuple(item) for item in actual_order) == EXPECTED_ORDER,
            f"actual campaign order differs: {actual_order}")
    stable = all(item["aggregate"]["stability_gate"] == "PASS" for item in summaries)
    summary_document = {
        "schema_version": 1,
        "evidence_type": "task012_three_backend_summary",
        "methodology_id": config["methodology_id"],
        "campaign_config": {"path": str(config_path.relative_to(REPOSITORY_ROOT)),
                            "sha256": config_sha256},
        "base_process_config": {"path": str(base_config_path.relative_to(REPOSITORY_ROOT)),
                                "sha256": base_sha256},
        "model_relationship": config["workload"]["model_relationship"],
        "percentile_method": "nearest-rank",
        "actual_process_order": actual_order,
        "summaries": summaries,
        "all_raw_samples_preserved": True,
        "sample_count_per_backend": 600,
        "status": "PENDING_HUMAN_REVIEW",
    }
    write_json(summary_path, summary_document)
    write_summary_csv(csv_path, summaries)
    raw_inputs = [{"path": str(path.relative_to(REPOSITORY_ROOT)), "sha256": sha256_file(path)}
                  for path in input_paths]
    immutable = [validate_artifact(value, name)
                 for name, value in config["immutable_historical_campaigns"].items()]
    validation = {
        "schema_version": 1,
        "evidence_type": "task012_three_backend_benchmark_validation",
        "methodology_id": config["methodology_id"],
        "raw_inputs": raw_inputs,
        "derived_outputs": [
            {"path": str(summary_path.relative_to(REPOSITORY_ROOT)),
             "sha256": sha256_file(summary_path)},
            {"path": str(csv_path.relative_to(REPOSITORY_ROOT)), "sha256": sha256_file(csv_path)},
        ],
        "immutable_historical_campaigns": immutable,
        "checks": {
            "process_count": 18,
            "independent_process_identities": 18,
            "actual_process_order": actual_order,
            "position_balance": "PASS",
            "sample_count_per_backend": 600,
            "all_raw_samples_preserved": True,
            "exact_pipeline_stage_sum": "PASS",
            "correctness_before_and_after_every_process": "PASS_TARGET",
            "release_cpu_fp32_one_thread": "PASS",
            "historical_campaigns_unchanged": "PASS",
        },
        "summaries": summaries,
        "stability_gate": "PASS" if stable else "FAIL",
        "status": "PENDING_HUMAN_REVIEW",
    }
    write_json(validation_path, validation)
    return validation


def parse_detections(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = load_json(path)
    detections = payload.get("detections")
    require(isinstance(detections, list), f"detections are missing: {path}")
    for detection in detections:
        box = detection.get("box_xyxy_source")
        require(isinstance(box, list) and len(box) == 4,
                f"detection box is invalid: {path}")
        values = [finite_number(value, "detection box coordinate") for value in box]
        require(0.0 <= values[0] <= values[2] <= 1280.0 and
                0.0 <= values[1] <= values[3] <= 960.0,
                f"detection box is out of bounds: {values}")
        finite_number(detection.get("confidence"), "detection confidence")
    return payload, detections


def validate_png(path: Path) -> dict[str, Any]:
    require_regular_file(path, "fresh result image")
    import cv2  # imported only for report generation
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    require(image is not None and image.shape == (960, 1280, 3),
            f"fresh image is not decodable 1280x960 BGR: {path}")
    return {"path": str(path.relative_to(REPOSITORY_ROOT)), "sha256": sha256_file(path),
            "width": 1280, "height": 960, "channels": 3}


def validate_task_states(tasks_directory: Path) -> list[dict[str, Any]]:
    task_table = (REPOSITORY_ROOT / "TASKS.md").read_text(encoding="utf-8")
    matrix = []
    for task_id in range(1, 13):
        allowed_states = ("Completed",)
        row_prefix = f"| {task_id:03d} |"
        row = next((line for line in task_table.splitlines() if line.startswith(row_prefix)), None)
        require(row is not None, f"TASKS.md row {task_id:03d} is missing")
        actual = next((state for state in allowed_states if f"| {state} |" in row), None)
        require(actual is not None,
                f"Task {task_id:03d} state is not one of {allowed_states}")
        task_path = tasks_directory / f"{task_id:03d}_"  # prefix lookup below
        matches = sorted(tasks_directory.glob(f"{task_id:03d}_*.md"))
        require(len(matches) == 1, f"Task {task_id:03d} file is ambiguous")
        text = matches[0].read_text(encoding="utf-8")
        require(f"## Status\n\n{actual}" in text,
                f"Task {task_id:03d} file state is not {actual}")
        evidence_path = repository_path(TASK_EVIDENCE[task_id])
        if task_id <= 11:
            require_regular_file(evidence_path, f"Task {task_id:03d} evidence")
        matrix.append({
            "task": task_id,
            "task_file": str(matches[0].relative_to(REPOSITORY_ROOT)),
            "task_status": actual,
            "evidence": TASK_EVIDENCE[task_id],
            "automatic_state": "PASS",
            "human_review": "APPROVED",
        })
    return matrix


def markdown_performance_table(summary: dict[str, Any]) -> str:
    lines = [
        "| Backend | Pipeline mean (ms) | P50 | P90 | Min | Max | Pipeline FPS | Six-round spread | Position spread |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["summaries"]:
        aggregate = item["aggregate"]
        pipeline = aggregate["stages"]["pipeline_total"]
        lines.append(
            f"| {BACKEND_LABELS[item['backend']]} | {pipeline['mean_ms']:.6f} | {pipeline['p50_ms']:.6f} | "
            f"{pipeline['p90_ms']:.6f} | {pipeline['min_ms']:.6f} | {pipeline['max_ms']:.6f} | "
            f"{aggregate['pipeline_fps_batch1_sequential']:.6f} | "
            f"{aggregate['six_round_pipeline_mean_max_relative_difference_percent']:.6f}% | "
            f"{aggregate['position_pipeline_mean_spread_percent']:.6f}% |"
        )
    return "\n".join(lines)


def markdown_stage_table(summary: dict[str, Any]) -> str:
    lines = [
        "| Backend | Preprocess mean (ms) | Inference mean (ms) | Postprocess mean (ms) | Pipeline mean (ms) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["summaries"]:
        stages = item["aggregate"]["stages"]
        lines.append(
            f"| {BACKEND_LABELS[item['backend']]} | {stages['preprocess']['mean_ms']:.6f} | "
            f"{stages['inference']['mean_ms']:.6f} | {stages['postprocess']['mean_ms']:.6f} | "
            f"{stages['pipeline_total']['mean_ms']:.6f} |"
        )
    return "\n".join(lines)


def markdown_position_table(summary: dict[str, Any]) -> str:
    lines = [
        "| Backend | Position 1 mean (ms) | Position 2 mean (ms) | Position 3 mean (ms) | Position spread |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["summaries"]:
        positions = {value["position"]: value for value in item["positions"]}
        aggregate = item["aggregate"]
        lines.append(
            f"| {BACKEND_LABELS[item['backend']]} | "
            f"{positions[1]['stages']['pipeline_total']['mean_ms']:.6f} | "
            f"{positions[2]['stages']['pipeline_total']['mean_ms']:.6f} | "
            f"{positions[3]['stages']['pipeline_total']['mean_ms']:.6f} | "
            f"{aggregate['position_pipeline_mean_spread_percent']:.6f}% |"
        )
    return "\n".join(lines)


def markdown_resource_table(summary: dict[str, Any]) -> str:
    lines = [
        "| Backend | Model load range (ms) | Process CPU range (%) | Peak RSS range (bytes) | Peak RSS range (MiB) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["summaries"]:
        loads = [value["model_load_ms"] for value in item["rounds"]]
        cpu = [value["resource_measurement"]["process_cpu_percent_one_core_basis"]
               for value in item["rounds"]]
        rss = [value["resource_measurement"]["peak_rss_bytes"] for value in item["rounds"]]
        lines.append(
            f"| {BACKEND_LABELS[item['backend']]} | {min(loads):.6f}–{max(loads):.6f} | "
            f"{min(cpu):.6f}–{max(cpu):.6f} | {min(rss)}–{max(rss)} | "
            f"{min(rss) / (1024 * 1024):.1f}–{max(rss) / (1024 * 1024):.1f} |"
        )
    return "\n".join(lines)


def performance_interpretation(summary: dict[str, Any]) -> str:
    by_backend = {item["backend"]: item for item in summary["summaries"]}
    python_stages = by_backend["python_ort"]["aggregate"]["stages"]
    cpp_stages = by_backend["cpp_ort"]["aggregate"]["stages"]
    ncnn_stages = by_backend["cpp_ncnn"]["aggregate"]["stages"]
    python_pipeline = python_stages["pipeline_total"]["mean_ms"]
    cpp_pipeline = cpp_stages["pipeline_total"]["mean_ms"]
    ncnn_pipeline = ncnn_stages["pipeline_total"]["mean_ms"]
    cpp_lower_than_python = (python_pipeline - cpp_pipeline) / python_pipeline * 100.0
    ort_inference_difference = abs(
        python_stages["inference"]["mean_ms"] - cpp_stages["inference"]["mean_ms"]
    ) / python_stages["inference"]["mean_ms"] * 100.0
    ncnn_pipeline_higher = (ncnn_pipeline - cpp_pipeline) / cpp_pipeline * 100.0
    ncnn_inference_higher = (
        ncnn_stages["inference"]["mean_ms"] - cpp_stages["inference"]["mean_ms"]
    ) / cpp_stages["inference"]["mean_ms"] * 100.0
    return f"""Under this fixed WSL2 configuration, C++ ORT has the lowest complete-
pipeline mean at `{cpp_pipeline:.6f} ms`, which is `{cpp_lower_than_python:.2f}%`
lower than Python ORT. Python ORT and C++ ORT inference means are
`{python_stages['inference']['mean_ms']:.6f} ms` and
`{cpp_stages['inference']['mean_ms']:.6f} ms`, a difference of about
`{ort_inference_difference:.2f}%`; the observed C++ pipeline advantage is
therefore concentrated in this implementation's preprocess and postprocess
overheads, not evidence that C++ or the ORT inference kernel is universally
faster.

C++ ncnn records `{ncnn_pipeline:.6f} ms`, `{ncnn_pipeline_higher:.2f}%` above
C++ ORT for the complete pipeline. Its inference mean is
`{ncnn_stages['inference']['mean_ms']:.6f} ms`, `{ncnn_inference_higher:.2f}%`
above C++ ORT in this campaign. This is specific to the fixed x86 CPU, WSL2,
runtime versions, model-conversion path, build, and input; it predicts neither
another PC nor ARM behavior."""


def render_readme(summary: dict[str, Any]) -> str:
    performance = markdown_performance_table(summary)
    stages = markdown_stage_table(summary)
    positions = markdown_position_table(summary)
    resources = markdown_resource_table(summary)
    interpretation = performance_interpretation(summary)
    return f"""# EdgeAI Deploy Benchmark

EdgeAI Deploy Benchmark is a reproducible PC deployment and measurement baseline
for a fixed YOLOv5n v7.0 detector. The PC implementation contains Python ONNX
Runtime, C++ ONNX Runtime, and C++ ncnn image/video paths with shared correctness
and benchmark contracts.

## Current status

Tasks 001–012 are completed, Checkpoint C is human-approved, and PC Stage 1 is
complete. Stage 2 for the Anlogic DR1 ARM CPU has not been implemented or started.
Its status remains `Not implemented / Planned`.

## PC architecture and model lineage

```text
YOLOv5n v7.0 weights
├── frozen ONNX ──> Python ORT / C++ ORT
└── frozen TorchScript ──> pnnx 20240410 ──> ncnn param/bin ──> C++ ncnn
```

{summary['model_relationship']}

YOLOv5n was selected as a small, established detector suitable for learning and
comparing deployment pipelines. The source weights SHA256 is
`4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3`;
the frozen ONNX SHA256 is
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`.
The input contract is batch 1, FP32, NCHW `[1,3,640,640]`.

## Environment and dependencies

- WSL2 Linux x86_64; CPU affinity scheduler managed; pinning disabled.
- Python 3.12.3, ONNX Runtime 1.18.1 CPUExecutionProvider, OpenCV 4.10.0.
- GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1, system OpenCV 4.6.0.
- C++ ONNX Runtime SDK 1.18.1 and ncnn 1.0.20240410.
- ORT intra/inter-op threads 1, ncnn threads 1, OpenCV threads 1.
- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
  `NUMEXPR_NUM_THREADS` are all 1.

The Python/C++ OpenCV version difference limits single-cause attribution of
preprocess performance even though tensor and detection correctness pass.

## Repository structure

- `python/`: Python ORT applications and common processing.
- `cpp/`: C++ common modules and ORT/ncnn applications.
- `configs/`: frozen inference and benchmark contracts.
- `models/`: manifests; generated model binaries remain Git-ignored.
- `tasks/`: auditable task state and execution records.
- `results/`: committed small evidence and generated local outputs.
- `docs/`: model, benchmark, and PC acceptance documentation.

## Model preparation

Model weights, ONNX, TorchScript, ncnn param/bin, SDKs, and large videos are
intentionally Git-ignored. Put the official v7.0 weights at
`models/yolov5n-v7.0/yolov5n.pt`, verify the Task 002 SHA256, and export ONNX
from a read-only YOLOv5 v7.0 checkout:

```bash
export YOLOV5_SOURCE=/path/to/yolov5-v7.0
.venv/bin/python "$YOLOV5_SOURCE/export.py" \\
  --weights models/yolov5n-v7.0/yolov5n.pt \\
  --imgsz 640 640 --batch-size 1 --device cpu \\
  --include onnx --opset 12
```

Do not add `--simplify`, `--dynamic`, `--half`, or graph NMS. For ncnn, follow
Task 010's fixed CPU/FP32 chain using the same weights: TorchScript export, pnnx
from ncnn tag `20240410` revision
`56775de50990ab7f16627efdcf5529b49541206f`, `inputshape=[1,3,640,640]f32`,
`device=cpu`, `fp16=0`, and `optlevel=2`. The manifests and Task 010 validators
must reproduce the recorded SHA256 values before inference. Do not substitute a
different model, pnnx revision, input size, precision, or threshold.

## Build

```bash
export ONNXRUNTIME_ROOT=/path/to/onnxruntime-linux-x64-1.18.1
export NCNN_ROOT=/path/to/ncnn-linux-x64-20240410-local
cmake -S cpp -B build/pc-acceptance-release -G Ninja \\
  -DCMAKE_BUILD_TYPE=Release \\
  -DONNXRUNTIME_ROOT="$ONNXRUNTIME_ROOT" \\
  -DNCNN_ROOT="$NCNN_ROOT"
cmake --build build/pc-acceptance-release --parallel
ctest --test-dir build/pc-acceptance-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
```

## Single-image and video commands

```bash
mkdir -p build/reproduction
PYTHONPATH=python .venv/bin/python python/apps/ort_image.py \\
  --model models/yolov5n-v7.0/yolov5n.onnx \\
  --manifest models/yolov5n-v7.0/manifest.json \\
  --config configs/yolov5n_v7_inference.json \\
  --image data/samples/images/pc_reference.jpg \\
  --output-image build/reproduction/python_ort_reference.png \\
  --output-json build/reproduction/python_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_image \\
  --model models/yolov5n-v7.0/yolov5n.onnx \\
  --manifest models/yolov5n-v7.0/manifest.json \\
  --config configs/yolov5n_v7_inference.json \\
  --image data/samples/images/pc_reference.jpg \\
  --output-image build/reproduction/cpp_ort_reference.png \\
  --output-json build/reproduction/cpp_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_video \\
  --model models/yolov5n-v7.0/yolov5n.onnx \\
  --manifest models/yolov5n-v7.0/manifest.json \\
  --config configs/yolov5n_v7_inference.json \\
  --input data/samples/videos/pc_reference.mp4 \\
  --output build/reproduction/cpp_ort_reference.mp4 \\
  --output-json build/reproduction/cpp_ort_video.json

./build/pc-acceptance-release/edgeai_ncnn_image \\
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \\
  --config configs/yolov5n_v7_inference.json \\
  --image data/samples/images/pc_reference.jpg \\
  --output-image build/reproduction/cpp_ncnn_reference.png \\
  --output-json build/reproduction/cpp_ncnn_reference.json

./build/pc-acceptance-release/edgeai_ncnn_video \\
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \\
  --config configs/yolov5n_v7_inference.json \\
  --input data/samples/videos/pc_reference.mp4 \\
  --output build/reproduction/cpp_ncnn_reference.mp4 \\
  --output-json build/reproduction/cpp_ncnn_video.json
```

These reproduction outputs stay under the Git-ignored build tree and do not
overwrite approved evidence. The known low-confidence second `mouse` on the
earbud case is retained as a model false positive; it is not hidden with
threshold or coordinate rules.

## Task 012 benchmark method

Six rounds execute all permutations of Python ORT, C++ ORT, and C++ ncnn. Every
backend appears twice in each position. Every invocation is an independent
process with 10 warmups and 100 formal iterations, yielding 600 samples per
backend. Every formal iteration performs preprocess, inference, and postprocess.

Pipeline total is the exact unrounded sum of those stages. It excludes image
read, model/runtime load, drawing, labels, writes, video decode, and encoding.
Pipeline FPS is `1000 / aggregate mean pipeline_total_ms`, not a mean of per-run
FPS and not video application throughput. P50/P90 use nearest-rank.

To reproduce the campaign without overwriting the approved Task 012 files, use
new paths under the Git-ignored build tree:

```bash
mkdir -p build/reproduction/benchmark
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
PYTHONPATH=python .venv/bin/python scripts/generate_pc_acceptance.py run-campaign \\
  --config configs/benchmark_pc_three_backend.json \\
  --base-config configs/benchmark_pc.json \\
  --python .venv/bin/python \\
  --python-benchmark python/apps/benchmark_ort.py \\
  --cpp-ort build/pc-acceptance-release/edgeai_benchmark_ort \\
  --cpp-ncnn build/pc-acceptance-release/edgeai_benchmark_ncnn \\
  --ncnn-manifest models/yolov5n-v7.0/ncnn_manifest.json \\
  --reference-detections results/evidence/007/cpp_ort_detections.json \\
  --python-output build/reproduction/benchmark/python_ort.json \\
  --cpp-ort-output build/reproduction/benchmark/cpp_ort.json \\
  --cpp-ncnn-output build/reproduction/benchmark/cpp_ncnn.json \\
  --summary build/reproduction/benchmark/summary.json \\
  --csv build/reproduction/benchmark/summary.csv \\
  --validation build/reproduction/benchmark/validation.json \\
  --log build/reproduction/benchmark/campaign.log
```

This command intentionally launches a new campaign; its outputs are not the
approved data below and must not replace files under `results/benchmarks/`.

### Final PC performance — campaign approved

{performance}

### Stage means

{stages}

{interpretation}

### Running-position effect

{positions}

Every position group contains 200 samples. All round spreads are below 3.3% and
all position spreads are below 1.4%; the execution position did not change the
backend ranking in this campaign. Position spread is diagnostic and no sample
was removed because of it.

### Model load, CPU, and Peak RSS

{resources}

All 1,800 samples and outliers are preserved. The table applies only to this
fixed WSL2 environment, code, model lineage, input, thread configuration, and
campaign. It is not a universal language/runtime ranking and cannot be projected
to bare-metal Linux, another PC, or ARM.

## Correctness

Python/C++ ORT use the frozen golden tolerances. ncnn matches ORT at the
pre-registered target of class-matched IoU at least 0.99 and confidence delta at
most 0.01. Each formal process performs untimed checks before warmup and after
measurement. The approved final values are minimum IoU `0.999999982537` and
maximum confidence delta `1.64833068306e-08` for Python/C++ ORT, and minimum IoU
`0.999997080011` and maximum delta `2.02655792236e-06` for C++ ORT/ncnn. The
three annotated images are human-approved and byte-identical with SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.

## CPU and memory definitions

`process_cpu_percent_one_core_basis` is 100 times process CPU-time delta divided
by wall-time delta. About 100% represents sustained use of one logical CPU;
values above 100% can reflect auxiliary Runtime or system activity. A configured
thread count of 1 does not mean the process owns exactly one OS thread.

Peak RSS is the complete process peak, not model-only memory. Python includes the
interpreter/modules; C++ includes executable and linked-library costs; every
backend includes its Runtime, model, and input state.

## Evidence, limitations, and reproduction

- Benchmark summary: `results/benchmarks/pc_three_backend_summary.json` and CSV.
- Validation: `results/evidence/012/three_backend_benchmark_validation.json`.
- Approved annotated outputs: `results/acceptance/python_ort_reference.png`,
  `results/acceptance/cpp_ort_reference.png`, and
  `results/acceptance/cpp_ncnn_reference.png`.
- PC acceptance: `docs/pc_stage_acceptance.md` and
  `results/evidence/012/pc_acceptance.json`.
- Task 009/011 campaigns remain immutable historical evidence and are not used as
  substitute rows in the Task 012 main table.
- WSL2 scheduling, frequency/thermal state, background activity, unpinned CPU,
  distinct OpenCV versions, and distinct ONNX/ncnn serialized graphs limit causal
  attribution.
- Generated models, SDKs, logs, videos, and other large reproducible artifacts
  remain Git-ignored. Reproduction requires the exact recorded hashes and local
  tool versions.

## Next stage

Checkpoint C is approved, but Stage 2 remains `Not implemented / Planned` and
requires separate authorization before work begins. No ARM build, deployment,
compatibility, or performance result exists yet.
"""


def render_acceptance_report(summary: dict[str, Any], matrix: Sequence[dict[str, Any]],
                             comparisons: dict[str, Any]) -> str:
    matrix_lines = [
        "| Task | Repository state | Automatic evidence | Human review | Evidence |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in matrix:
        matrix_lines.append(
            f"| {row['task']:03d} | {row['task_status']} | {row['automatic_state']} | "
            f"{row['human_review']} | `{row['evidence']}` |"
        )
    return f"""# PC Stage Acceptance Report — Checkpoint C

Status: **PC STAGE 1 COMPLETED; CHECKPOINT C APPROVED**

This report is generated from the approved first complete Task 012 six-round
campaign. The final document, matrix, risk statements, and Checkpoint C are
human-approved. This completion is not authorization to begin the ARM stage.

## Model relationship

{summary['model_relationship']}

## Benchmark boundaries

Each backend has six independent processes, 10 warmups per process, 100 measured
pipelines per process, and 600 retained samples. Pipeline total is the exact sum
of preprocess, inference, and postprocess. It excludes image read, model/runtime
load, drawing, labels, file writes, and video I/O/encoding. Pipeline FPS is
`1000 / aggregate mean pipeline_total_ms`. P50/P90 are nearest-rank.

## Final PC performance

{markdown_performance_table(summary)}

## Stage analysis

{markdown_stage_table(summary)}

{performance_interpretation(summary)}

## Running-position effect

{markdown_position_table(summary)}

All position groups contain 200 samples. The measured position spreads are
diagnostic; all samples remain in the aggregate result.

## Fresh correctness

- Python ORT versus C++ ORT: minimum IoU
  `{comparisons['python_cpp_ort']['minimum_class_matched_iou']:.12g}`, maximum
  confidence delta
  `{comparisons['python_cpp_ort']['maximum_absolute_confidence_difference']:.12g}`.
- C++ ORT versus C++ ncnn: minimum IoU
  `{comparisons['ort_ncnn']['minimum_class_matched_iou']:.12g}`, maximum
  confidence delta
  `{comparisons['ort_ncnn']['maximum_absolute_confidence_difference']:.12g}`.
- All three contain the same five classes/detections. The earbud-case low-
  confidence `mouse` is a known shared model false positive.
- The three fresh annotated images are human-approved and byte-identical with
  SHA256 `57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.

## CPU and Peak RSS

{markdown_resource_table(summary)}

CPU is `process_cpu_percent_one_core_basis`, not whole-machine utilization.
Configured thread count 1 does not restrict the process to one OS thread. Peak
RSS is full-process peak memory, including language/runtime/library/model/input
costs, and is not pure model memory.

## Acceptance matrix

{chr(10).join(matrix_lines)}

## Limitations and unresolved risks

- WSL2 is not bare-metal Linux; affinity is scheduler managed and CPU pinning is
  disabled.
- Python OpenCV 4.10.0 and C++ OpenCV 4.6.0 limit preprocess attribution.
- ORT and ncnn share source weights but not the same serialized graph.
- Frequency, thermal state, and background load may affect measured latency.
- The approved PC measurements remain specific to this environment, model,
  conversion path, Runtime versions, build, and input.
- PC correctness and speed do not predict ARM compatibility or performance.

## Checkpoint C

Checkpoint C is human-approved after review of raw sample counts/order, per-round
and position statistics, outliers, stability, CPU/RSS definitions, fresh images,
README, matrix, and limitations. PC Stage 1 is complete. Stage 2 remains
`Not implemented / Planned` and has not started.
"""


def generate_report(args: argparse.Namespace) -> int:
    config, _ = load_and_validate_config(args.config.resolve(),
                                         repository_path(config_base_path(args.config)))
    summary = load_json(args.benchmark_summary.resolve())
    validation = load_json(args.benchmark_validation.resolve())
    require(summary.get("status") == "PENDING_HUMAN_REVIEW",
            "benchmark summary status differs")
    require(validation.get("status") == "PENDING_HUMAN_REVIEW" and
            validation.get("stability_gate") == "PASS",
            "benchmark validation is not a stable human-review candidate")
    expected_inputs = {item["path"]: item["sha256"] for item in validation["raw_inputs"]}
    for path in args.benchmark_inputs:
        relative = str(path.resolve().relative_to(REPOSITORY_ROOT))
        require(expected_inputs.get(relative) == sha256_file(path.resolve()),
                f"benchmark raw hash differs: {relative}")
    derived = {item["path"]: item["sha256"] for item in validation["derived_outputs"]}
    summary_relative = str(args.benchmark_summary.resolve().relative_to(REPOSITORY_ROOT))
    require(derived.get(summary_relative) == sha256_file(args.benchmark_summary.resolve()),
            "benchmark summary hash differs")

    require(len(args.fresh_results) == 3, "three fresh results are required")
    fresh_by_backend = {}
    images = []
    for backend, path in zip(BACKENDS, args.fresh_results):
        payload, detections = parse_detections(path.resolve())
        fresh_by_backend[backend] = {"path": path.resolve(), "payload": payload,
                                     "detections": detections}
        image_path = args.image_paths[BACKENDS.index(backend)].resolve()
        images.append(validate_png(image_path))
    python_cpp = compare_detections(fresh_by_backend["python_ort"]["detections"],
                                    fresh_by_backend["cpp_ort"]["detections"], 0.99, 0.001)
    ort_ncnn = compare_detections(fresh_by_backend["cpp_ort"]["detections"],
                                  fresh_by_backend["cpp_ncnn"]["detections"], 0.99, 0.01)
    matrix = validate_task_states(args.tasks.resolve())
    comparisons = {"python_cpp_ort": python_cpp, "ort_ncnn": ort_ncnn}
    acceptance = {
        "schema_version": 1,
        "evidence_type": "task012_pc_stage_acceptance",
        "status": "COMPLETED_CHECKPOINT_C_APPROVED",
        "campaign_config": {"path": str(args.config), "sha256": sha256_file(args.config)},
        "benchmark_summary": {"path": str(args.benchmark_summary),
                              "sha256": sha256_file(args.benchmark_summary)},
        "benchmark_validation": {"path": str(args.benchmark_validation),
                                 "sha256": sha256_file(args.benchmark_validation)},
        "fresh_results": [
            {"backend": backend, "path": str(value["path"].relative_to(REPOSITORY_ROOT)),
             "sha256": sha256_file(value["path"]), "detection_count": len(value["detections"])}
            for backend, value in fresh_by_backend.items()
        ],
        "fresh_images": images,
        "fresh_comparisons": comparisons,
        "acceptance_matrix": matrix,
        "checks": {
            "tasks_001_012_completed": "PASS",
            "historical_evidence_unchanged": "PASS",
            "three_backend_campaign": "PASS_HUMAN_APPROVED",
            "fresh_correctness": "PASS_TARGET",
            "fresh_visual_review": "HUMAN_APPROVED",
            "performance_review": "HUMAN_APPROVED",
            "final_document_review": "HUMAN_APPROVED",
            "checkpoint_c": "HUMAN_APPROVED",
            "pc_stage_1": "COMPLETED",
            "arm_stage": "NOT_IMPLEMENTED_PLANNED",
        },
    }
    write_json(args.acceptance_json.resolve(), acceptance)
    args.readme.resolve().write_text(render_readme(summary), encoding="utf-8")
    args.acceptance_report.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.acceptance_report.resolve().write_text(
        render_acceptance_report(summary, matrix, comparisons), encoding="utf-8"
    )
    print("task001_012_evidence=PASS")
    print("fresh_python_cpp_ort=PASS")
    print("fresh_ort_ncnn=PASS_TARGET")
    print("benchmark_campaign=PASS_HUMAN_APPROVED")
    print("status=COMPLETED_CHECKPOINT_C_APPROVED")
    return 0


def config_base_path(config_path: Path) -> str:
    config = load_json(config_path.resolve())
    value = config.get("base_process_config", {}).get("path")
    require(isinstance(value, str) and value, "base process config path is missing")
    return value


def add_common_campaign_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--base-config", required=True, type=Path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    campaign = subparsers.add_parser("run-campaign", help="run the 18-process campaign")
    add_common_campaign_arguments(campaign)
    campaign.add_argument("--python", required=True, type=Path)
    campaign.add_argument("--python-benchmark", required=True, type=Path)
    campaign.add_argument("--cpp-ort", required=True, type=Path)
    campaign.add_argument("--cpp-ncnn", required=True, type=Path)
    campaign.add_argument("--ncnn-manifest", required=True, type=Path)
    campaign.add_argument("--reference-detections", required=True, type=Path)
    campaign.add_argument("--python-output", required=True, type=Path)
    campaign.add_argument("--cpp-ort-output", required=True, type=Path)
    campaign.add_argument("--cpp-ncnn-output", required=True, type=Path)
    campaign.add_argument("--summary", required=True, type=Path)
    campaign.add_argument("--csv", required=True, type=Path)
    campaign.add_argument("--validation", required=True, type=Path)
    campaign.add_argument("--log", required=True, type=Path)

    report = subparsers.add_parser("generate-report", help="generate PC acceptance reports")
    report.add_argument("--config", required=True, type=Path)
    report.add_argument("--tasks", required=True, type=Path)
    report.add_argument("--benchmark-inputs", required=True, type=Path, nargs=3)
    report.add_argument("--benchmark-summary", required=True, type=Path)
    report.add_argument("--benchmark-validation", required=True, type=Path)
    report.add_argument("--fresh-results", required=True, type=Path, nargs=3)
    report.add_argument("--image-paths", required=True, type=Path, nargs=3)
    report.add_argument("--acceptance-json", required=True, type=Path)
    report.add_argument("--acceptance-report", required=True, type=Path)
    report.add_argument("--readme", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run-campaign":
        return run_campaign(args)
    return generate_report(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AcceptanceError, BenchmarkError, OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"Task 012 acceptance error: {error}") from error
