#!/usr/bin/env python3
"""Validate and summarize Task 009 Python/C++ raw benchmark evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPOSITORY_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from edgeai_benchmark.benchmark import (  # noqa: E402
    BenchmarkError,
    STAGES,
    load_json,
    maximum_relative_difference,
    summarize_ns,
    validate_benchmark_config,
)


BACKENDS = ("python_ort", "cpp_ort")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path, nargs=2)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BenchmarkError(message)


def finite_nonnegative(value: Any, description: str, positive: bool = False) -> float:
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{description} must be numeric",
    )
    converted = float(value)
    require(math.isfinite(converted), f"{description} must be finite")
    require(converted > 0.0 if positive else converted >= 0.0, f"{description} is invalid")
    return converted


def validate_correctness(value: Any, description: str) -> None:
    require(isinstance(value, dict), f"{description} must be an object")
    require(value.get("status") == "PASS", f"{description} did not pass")
    require(value.get("detection_count") == 5, f"{description} count differs")
    minimum_iou = finite_nonnegative(
        value.get("minimum_class_matched_iou"), f"{description} minimum IoU"
    )
    confidence = finite_nonnegative(
        value.get("maximum_absolute_confidence_difference"),
        f"{description} confidence difference",
    )
    require(minimum_iou >= 0.99, f"{description} IoU is below 0.99")
    require(confidence <= 0.001, f"{description} confidence difference exceeds 0.001")


def validate_backend(
    payload: dict[str, Any],
    backend: str,
    config: dict[str, Any],
    config_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require(payload.get("schema_version") == 1, f"{backend} schema differs")
    require(payload.get("evidence_type") == "task009_raw_benchmark", f"{backend} type differs")
    require(payload.get("backend") == backend, f"{backend} identity differs")
    require(
        payload.get("benchmark_config_sha256") == config_sha256,
        f"{backend} benchmark config SHA256 differs",
    )
    rounds = payload.get("rounds")
    require(isinstance(rounds, list) and len(rounds) == 5, f"{backend} must have five rounds")
    process_ids: set[int] = set()
    process_starts: list[dict[str, Any]] = []
    aggregate_samples: list[dict[str, Any]] = []
    round_summaries = []
    workload = config["workload"]
    expected_hashes = {
        "model_sha256": workload["model"]["sha256"],
        "image_sha256": workload["image"]["sha256"],
        "manifest_sha256": workload["manifest"]["sha256"],
        "inference_config_sha256": workload["inference_config"]["sha256"],
        "golden_result_sha256": workload["golden_result"]["sha256"],
    }
    required_environment = config["environment"]["required_environment_variables"]
    for round_index, round_value in enumerate(rounds, start=1):
        require(round_value.get("round") == round_index, f"{backend} round ID differs")
        process_id = round_value.get("process_id")
        require(isinstance(process_id, int) and process_id > 0, f"{backend} PID is invalid")
        require(process_id not in process_ids, f"{backend} reused a process ID")
        process_ids.add(process_id)
        process_started = round_value.get("process_started_unix_ns")
        require(
            isinstance(process_started, int) and process_started > 0,
            f"{backend} process start is invalid",
        )
        process_starts.append(
            {"backend": backend, "round": round_index, "unix_ns": process_started, "pid": process_id}
        )
        finite_nonnegative(round_value.get("model_load_ms"), f"{backend} model load", positive=True)
        for key, expected in expected_hashes.items():
            require(round_value.get(key) == expected, f"{backend} {key} differs")
        runtime = round_value.get("runtime", {})
        expected_runtime = config["runtime"]
        for key, expected in expected_runtime.items():
            require(runtime.get(key) == expected, f"{backend} runtime {key} differs")
        require(
            runtime.get("selected_providers") == ["CPUExecutionProvider"],
            f"{backend} selected providers differ",
        )
        require(runtime.get("runtime_inputs") == [{
            "name": "images", "shape": [1, 3, 640, 640], "dtype": "FLOAT",
            **({"ort_type": "tensor(float)"} if backend == "python_ort" else {}),
        }], f"{backend} runtime input contract differs")
        expected_output = {
            "name": "output0", "shape": [1, 25200, 85], "dtype": "FLOAT",
            **({"ort_type": "tensor(float)"} if backend == "python_ort" else {}),
        }
        require(runtime.get("runtime_outputs") == [expected_output], f"{backend} output contract differs")
        environment = round_value.get("environment", {})
        require(environment.get("platform") == "WSL2", f"{backend} platform differs")
        require(
            environment.get("cpu_affinity") == "scheduler managed"
            and environment.get("cpu_pinning") == "disabled",
            f"{backend} affinity policy differs",
        )
        require(
            environment.get("environment_variables") == required_environment,
            f"{backend} thread environment differs",
        )
        require("microsoft" in str(environment.get("kernel", "")).lower(), f"{backend} is not WSL2")
        if backend == "cpp_ort":
            require(environment.get("build_type") == "Release", "C++ build is not Release")
        require(round_value.get("warmup_iterations") == 10, f"{backend} warmup differs")
        require(round_value.get("formal_iterations") == 100, f"{backend} repeat differs")
        resource_value = round_value.get("resource_measurement", {})
        finite_nonnegative(
            resource_value.get("process_cpu_percent_one_core_basis"),
            f"{backend} CPU percent",
        )
        cpu_delta = finite_nonnegative(
            resource_value.get("process_cpu_time_delta_seconds"),
            f"{backend} CPU delta",
            positive=True,
        )
        wall_delta = finite_nonnegative(
            resource_value.get("wall_clock_time_delta_seconds"),
            f"{backend} wall delta",
            positive=True,
        )
        observed_cpu = float(resource_value["process_cpu_percent_one_core_basis"])
        require(
            math.isclose(observed_cpu, 100.0 * cpu_delta / wall_delta, rel_tol=1e-9),
            f"{backend} CPU formula differs",
        )
        peak_rss = resource_value.get("peak_rss_bytes")
        require(isinstance(peak_rss, int) and peak_rss > 0, f"{backend} peak RSS is invalid")
        require(
            resource_value.get("peak_rss_is_process_level_not_model_only") is True,
            f"{backend} peak RSS scope is not explicit",
        )
        correctness = round_value.get("correctness", {})
        validate_correctness(correctness.get("before_warmup"), f"{backend} before correctness")
        validate_correctness(
            correctness.get("after_measurement"), f"{backend} after correctness"
        )
        samples = round_value.get("samples")
        require(isinstance(samples, list) and len(samples) == 100, f"{backend} round samples differ")
        stage_values: dict[str, list[int]] = {stage: [] for stage in STAGES}
        for iteration, sample in enumerate(samples, start=1):
            require(sample.get("round") == round_index, f"{backend} sample round differs")
            require(sample.get("iteration") == iteration, f"{backend} sample iteration differs")
            aggregate_index = (round_index - 1) * 100 + iteration
            require(
                sample.get("aggregate_sample_index") == aggregate_index,
                f"{backend} aggregate sample index differs",
            )
            observed: dict[str, int] = {}
            for stage in STAGES:
                key = f"{stage}_ns"
                raw = sample.get(key)
                require(
                    not isinstance(raw, bool)
                    and isinstance(raw, (int, float))
                    and math.isfinite(float(raw))
                    and int(raw) == raw
                    and raw >= 0,
                    f"{backend} {key} is invalid",
                )
                observed[stage] = int(raw)
                stage_values[stage].append(int(raw))
            require(
                observed["pipeline_total"]
                == observed["preprocess"] + observed["inference"] + observed["postprocess"],
                f"{backend} pipeline total is not the exact stage sum",
            )
            aggregate_samples.append(sample)
        round_summaries.append(
            {
                "round": round_index,
                "model_load_ms": round_value["model_load_ms"],
                "resource_measurement": resource_value,
                "stages": {
                    stage: summarize_ns(stage_values[stage]) for stage in STAGES
                },
            }
        )
    require(len(aggregate_samples) == 500, f"{backend} aggregate sample count differs")
    aggregate_stages = {
        stage: summarize_ns([sample[f"{stage}_ns"] for sample in aggregate_samples])
        for stage in STAGES
    }
    pipeline_means = [
        round_value["stages"]["pipeline_total"]["mean_ms"]
        for round_value in round_summaries
    ]
    relative_difference = maximum_relative_difference(pipeline_means)
    fastest = min(aggregate_samples, key=lambda sample: sample["pipeline_total_ns"])
    slowest = max(aggregate_samples, key=lambda sample: sample["pipeline_total_ns"])
    stability_limit = config["statistics"][
        "maximum_round_mean_relative_difference_percent"
    ]
    return (
        {
            "backend": backend,
            "sample_count": len(aggregate_samples),
            "rounds": round_summaries,
            "aggregate": {
                "stages": aggregate_stages,
                "pipeline_fps_batch1_sequential": 1000.0
                / aggregate_stages["pipeline_total"]["mean_ms"],
                "fastest_sample": {
                    "aggregate_sample_index": fastest["aggregate_sample_index"],
                    "round": fastest["round"],
                    "iteration": fastest["iteration"],
                    "pipeline_total_ms": fastest["pipeline_total_ns"] / 1_000_000.0,
                },
                "slowest_sample": {
                    "aggregate_sample_index": slowest["aggregate_sample_index"],
                    "round": slowest["round"],
                    "iteration": slowest["iteration"],
                    "pipeline_total_ms": slowest["pipeline_total_ns"] / 1_000_000.0,
                },
                "five_round_pipeline_mean_max_relative_difference_percent": relative_difference,
                "stability_limit_percent": stability_limit,
                "stability_gate": "PASS" if relative_difference <= stability_limit else "FAIL",
            },
        },
        process_starts,
    )


def write_csv(path: Path, summaries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "backend", "scope", "round", "stage", "count", "mean_ms", "p50_ms",
        "p90_ms", "min_ms", "max_ms", "pipeline_fps_batch1_sequential",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for summary in summaries:
            for round_summary in summary["rounds"]:
                for stage, values in round_summary["stages"].items():
                    writer.writerow({
                        "backend": summary["backend"],
                        "scope": "round",
                        "round": round_summary["round"],
                        "stage": stage,
                        **values,
                        "pipeline_fps_batch1_sequential": "",
                    })
            for stage, values in summary["aggregate"]["stages"].items():
                writer.writerow({
                    "backend": summary["backend"],
                    "scope": "aggregate",
                    "round": "",
                    "stage": stage,
                    **values,
                    "pipeline_fps_batch1_sequential": (
                        summary["aggregate"]["pipeline_fps_batch1_sequential"]
                        if stage == "pipeline_total" else ""
                    ),
                })


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    validate_benchmark_config(config)
    config_sha256 = sha256_file(args.config)
    payloads = [load_json(path) for path in args.inputs]
    by_backend = {payload.get("backend"): payload for payload in payloads}
    require(set(by_backend) == set(BACKENDS), "inputs must contain Python ORT and C++ ORT")
    summaries = []
    process_starts = []
    for backend in BACKENDS:
        summary, backend_starts = validate_backend(
            by_backend[backend], backend, config, config_sha256
        )
        summaries.append(summary)
        process_starts.extend(backend_starts)
    require(len({item["pid"] for item in process_starts}) == 10, "ten distinct processes required")
    actual_order = [
        [item["backend"] for item in sorted(
            (entry for entry in process_starts if entry["round"] == round_id),
            key=lambda entry: entry["unix_ns"],
        )]
        for round_id in range(1, 6)
    ]
    require(actual_order == config["rounds"]["order"], f"process order differs: {actual_order}")
    stable = all(summary["aggregate"]["stability_gate"] == "PASS" for summary in summaries)
    write_csv(args.csv, summaries)
    report = {
        "schema_version": 1,
        "evidence_type": "task009_benchmark_validation",
        "benchmark_config": {"path": str(args.config), "sha256": config_sha256},
        "raw_inputs": [
            {"path": str(path), "sha256": sha256_file(path)} for path in args.inputs
        ],
        "statistics_implementation": "scripts/validate_benchmark.py",
        "percentile_method": "nearest-rank",
        "actual_process_order": actual_order,
        "summaries": summaries,
        "all_raw_samples_preserved": True,
        "sample_count_per_backend": 500,
        "stability_gate": "PASS" if stable else "FAIL",
        "status": "PENDING_HUMAN_REVIEW",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("schema_validation=PASS")
    print("python_ort_samples=500")
    print("cpp_ort_samples=500")
    print(f"actual_process_order={json.dumps(actual_order)}")
    for summary in summaries:
        aggregate = summary["aggregate"]
        print(
            f"{summary['backend']}_pipeline_mean_ms="
            f"{aggregate['stages']['pipeline_total']['mean_ms']:.6f}"
        )
        print(
            f"{summary['backend']}_pipeline_fps_batch1_sequential="
            f"{aggregate['pipeline_fps_batch1_sequential']:.6f}"
        )
        print(
            f"{summary['backend']}_five_round_mean_relative_difference_percent="
            f"{aggregate['five_round_pipeline_mean_max_relative_difference_percent']:.6f}"
        )
        print(f"{summary['backend']}_stability_gate={aggregate['stability_gate']}")
    print(f"overall_stability_gate={report['stability_gate']}")
    print("status=PENDING_HUMAN_REVIEW")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BenchmarkError, OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"benchmark validation error: {error}") from error
