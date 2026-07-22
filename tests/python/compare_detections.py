#!/usr/bin/env python3
"""Compare real C++ ORT detections with the approved Python semantic golden."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPOSITORY_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from edgeai_benchmark.benchmark import (  # noqa: E402
    BenchmarkError,
    STAGES,
    maximum_relative_difference,
    summarize_ns,
    validate_benchmark_config,
)


FROZEN_MINIMUM_IOU = 0.99
FROZEN_MAXIMUM_CONFIDENCE_DELTA = 0.001
NCNN_TARGET_MINIMUM_IOU = 0.99
NCNN_TARGET_MAXIMUM_CONFIDENCE_DELTA = 0.01
NCNN_HARD_MINIMUM_IOU = 0.98
NCNN_HARD_MAXIMUM_CONFIDENCE_DELTA = 0.02
TASK009_IMMUTABLE_ARTIFACTS = {
    "results/benchmarks/pc_python_ort.json":
        "125f1fa1eb2f2ab46268fb9bdb7cd37d7092543a29d6b41527f885d41e417c41",
    "results/benchmarks/pc_cpp_ort.json":
        "8b8a6cfb444dd4047a43165c256c7a854b406079f8cfb93479039733af7c5c8e",
    "results/benchmarks/pc_ort_summary.csv":
        "4ac971e42f718807fd802c3df9e69cf1a4acc3766f1457e2f86b57fc4d35be63",
    "results/evidence/009/benchmark_validation.json":
        "b3edd6664db4f3c9a9f9e7359687b3d43e826e092b3237e57f9f323d0602fcfc",
}
NCNN_MANIFEST = REPOSITORY_ROOT / "models/yolov5n-v7.0/ncnn_manifest.json"
CPP_ORT_REFERENCE = REPOSITORY_ROOT / "results/evidence/007/cpp_ort_detections.json"


class ComparisonError(RuntimeError):
    """Raised when detection artifacts cannot be compared safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument(
        "--profile",
        choices=("cpp-ort", "ncnn-preregistered"),
        default="cpp-ort",
    )
    parser.add_argument("--min-iou", type=float)
    parser.add_argument("--max-confidence-delta", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--benchmark-input", type=Path)
    parser.add_argument("--benchmark-config", type=Path)
    parser.add_argument("--benchmark-summary", type=Path)
    parser.add_argument("--benchmark-csv", type=Path)
    parser.add_argument("--benchmark-report", type=Path)
    args = parser.parse_args()
    detection_values = (
        args.reference,
        args.candidate,
        args.min_iou,
        args.max_confidence_delta,
        args.output,
    )
    benchmark_values = (
        args.benchmark_input,
        args.benchmark_config,
        args.benchmark_summary,
        args.benchmark_csv,
        args.benchmark_report,
    )
    if any(value is not None for value in benchmark_values):
        if not all(value is not None for value in benchmark_values):
            parser.error("all benchmark arguments are required together")
        if any(value is not None for value in detection_values):
            parser.error("detection and benchmark modes cannot be combined")
        args.mode = "benchmark"
    else:
        if not all(value is not None for value in detection_values):
            parser.error("all detection-comparison arguments are required")
        args.mode = "detection"
    return args


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ComparisonError(f"failed to load JSON {path}: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ComparisonError(f"required artifact is missing or empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_detection(detection: dict[str, Any]) -> None:
    if not isinstance(detection.get("class_id"), int) or detection["class_id"] < 0:
        raise ComparisonError("detection class_id is invalid")
    if not isinstance(detection.get("class_name"), str) or not detection["class_name"]:
        raise ComparisonError("detection class_name is invalid")
    confidence = detection.get("confidence")
    if not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
        raise ComparisonError("detection confidence is not finite")
    if not 0.0 <= confidence <= 1.0:
        raise ComparisonError("detection confidence is outside [0, 1]")
    box = detection.get("box_xyxy_source")
    if (
        not isinstance(box, list)
        or len(box) != 4
        or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in box)
        or box[2] <= box[0]
        or box[3] <= box[1]
    ):
        raise ComparisonError("detection source box is invalid")


def box_iou(left: list[float], right: list[float]) -> float:
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def compare(
    reference: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    minimum_iou: float,
    maximum_confidence_delta: float,
) -> list[dict[str, Any]]:
    if len(reference) != len(candidate):
        raise ComparisonError(
            f"detection count mismatch: reference={len(reference)} candidate={len(candidate)}"
        )
    for detection in reference + candidate:
        validate_detection(detection)
    unmatched = set(range(len(candidate)))
    matches = []
    for expected in reference:
        class_matches = [
            index
            for index in unmatched
            if candidate[index]["class_id"] == expected["class_id"]
            and candidate[index]["class_name"] == expected["class_name"]
        ]
        if not class_matches:
            raise ComparisonError(f"no candidate detection for class {expected['class_name']}")
        best_index = max(
            class_matches,
            key=lambda index: box_iou(
                expected["box_xyxy_source"], candidate[index]["box_xyxy_source"]
            ),
        )
        overlap = box_iou(
            expected["box_xyxy_source"], candidate[best_index]["box_xyxy_source"]
        )
        confidence_delta = abs(expected["confidence"] - candidate[best_index]["confidence"])
        if overlap < minimum_iou:
            raise ComparisonError(
                f"class {expected['class_name']} IoU {overlap} is below {minimum_iou}"
            )
        if confidence_delta > maximum_confidence_delta:
            raise ComparisonError(
                f"class {expected['class_name']} confidence delta {confidence_delta} "
                f"exceeds {maximum_confidence_delta}"
            )
        unmatched.remove(best_index)
        matches.append(
            {
                "reference_rank": expected["rank"],
                "candidate_rank": candidate[best_index]["rank"],
                "class_id": expected["class_id"],
                "class_name": expected["class_name"],
                "iou": overlap,
                "absolute_confidence_difference": confidence_delta,
            }
        )
    if unmatched:
        raise ComparisonError(f"unmatched candidate detections remain: {sorted(unmatched)}")
    return matches


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BenchmarkError(message)


def finite_nonnegative(value: Any, description: str, *, positive: bool = False) -> float:
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{description} must be numeric",
    )
    converted = float(value)
    require(math.isfinite(converted), f"{description} must be finite")
    require(converted > 0.0 if positive else converted >= 0.0, f"{description} is invalid")
    return converted


def validate_benchmark_correctness(value: Any, description: str) -> None:
    require(isinstance(value, dict), f"{description} must be an object")
    require(value.get("status") == "PASS_TARGET", f"{description} did not pass target")
    require(value.get("detection_count") == 5, f"{description} detection count differs")
    minimum_iou = finite_nonnegative(
        value.get("minimum_class_matched_iou"), f"{description} minimum IoU"
    )
    confidence_delta = finite_nonnegative(
        value.get("maximum_absolute_confidence_difference"),
        f"{description} confidence difference",
    )
    require(minimum_iou >= NCNN_TARGET_MINIMUM_IOU, f"{description} IoU is below target")
    require(
        confidence_delta <= NCNN_TARGET_MAXIMUM_CONFIDENCE_DELTA,
        f"{description} confidence difference exceeds target",
    )


def write_benchmark_csv(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "backend",
        "scope",
        "round",
        "stage",
        "count",
        "mean_ms",
        "p50_ms",
        "p90_ms",
        "min_ms",
        "max_ms",
        "pipeline_fps_batch1_sequential",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for round_summary in summary["rounds"]:
            for stage, values in round_summary["stages"].items():
                writer.writerow(
                    {
                        "backend": summary["backend"],
                        "scope": "round",
                        "round": round_summary["round"],
                        "stage": stage,
                        **values,
                        "pipeline_fps_batch1_sequential": "",
                    }
                )
        for stage, values in summary["aggregate"]["stages"].items():
            writer.writerow(
                {
                    "backend": summary["backend"],
                    "scope": "aggregate",
                    "round": "",
                    "stage": stage,
                    **values,
                    "pipeline_fps_batch1_sequential": (
                        summary["aggregate"]["pipeline_fps_batch1_sequential"]
                        if stage == "pipeline_total"
                        else ""
                    ),
                }
            )


def validate_ncnn_benchmark(
    payload: dict[str, Any], config: dict[str, Any], config_sha256: str
) -> dict[str, Any]:
    require(payload.get("schema_version") == 1, "ncnn benchmark schema differs")
    require(
        payload.get("evidence_type") == "task011_raw_benchmark",
        "ncnn benchmark evidence type differs",
    )
    require(payload.get("backend") == "cpp_ncnn", "ncnn benchmark backend differs")
    require(
        payload.get("benchmark_config_sha256") == config_sha256,
        "ncnn benchmark config SHA256 differs",
    )

    ncnn_manifest = load_json(NCNN_MANIFEST)
    workload = config["workload"]
    expected_hashes = {
        "source_weights_sha256": ncnn_manifest["lineage"]["weights"]["sha256"],
        "frozen_onnx_sha256": workload["model"]["sha256"],
        "ncnn_manifest_sha256": sha256_file(NCNN_MANIFEST),
        "ncnn_param_sha256": ncnn_manifest["ncnn_model"]["param"]["sha256"],
        "ncnn_bin_sha256": ncnn_manifest["ncnn_model"]["bin"]["sha256"],
        "image_sha256": workload["image"]["sha256"],
        "inference_config_sha256": workload["inference_config"]["sha256"],
        "golden_result_sha256": workload["golden_result"]["sha256"],
        "reference_detections_sha256": sha256_file(CPP_ORT_REFERENCE),
    }
    rounds = payload.get("rounds")
    require(isinstance(rounds, list) and len(rounds) == 5, "five ncnn rounds required")
    required_environment = config["environment"]["required_environment_variables"]
    process_ids: set[int] = set()
    process_starts: list[int] = []
    all_samples: list[dict[str, Any]] = []
    round_summaries: list[dict[str, Any]] = []
    for round_index, round_value in enumerate(rounds, start=1):
        require(isinstance(round_value, dict), "ncnn round must be an object")
        require(round_value.get("round") == round_index, "ncnn round ID differs")
        process_id = round_value.get("process_id")
        require(isinstance(process_id, int) and process_id > 0, "ncnn PID is invalid")
        require(process_id not in process_ids, "ncnn benchmark reused a process ID")
        process_ids.add(process_id)
        process_started = round_value.get("process_started_unix_ns")
        require(
            isinstance(process_started, int) and process_started > 0,
            "ncnn process start is invalid",
        )
        process_starts.append(process_started)
        finite_nonnegative(round_value.get("model_load_ms"), "ncnn model load", positive=True)
        for key, expected in expected_hashes.items():
            require(round_value.get(key) == expected, f"ncnn {key} differs")

        runtime = round_value.get("runtime")
        require(
            runtime
            == {
                "ncnn_version": "1.0.20240410",
                "execution_provider": "ncnn CPU",
                "threads": 1,
                "vulkan": False,
                "fp16": False,
                "bf16": False,
                "int8": False,
                "input": {
                    "name": "in0",
                    "logical_shape": [1, 3, 640, 640],
                    "dtype": "float32",
                },
                "output": {
                    "name": "out0",
                    "logical_shape": [1, 25200, 85],
                    "dtype": "float32",
                },
            },
            "ncnn runtime contract differs",
        )
        environment = round_value.get("environment", {})
        require(environment.get("platform") == "WSL2", "ncnn platform differs")
        require("microsoft" in str(environment.get("kernel", "")).lower(), "not WSL2")
        require(environment.get("architecture") == "x86_64", "architecture differs")
        require(environment.get("build_type") == "Release", "ncnn build is not Release")
        require(environment.get("opencv_version") == "4.6.0", "C++ OpenCV differs")
        require(
            environment.get("cpu_affinity") == "scheduler managed"
            and environment.get("cpu_pinning") == "disabled",
            "ncnn CPU affinity policy differs",
        )
        require(
            environment.get("environment_variables") == required_environment,
            "ncnn thread environment differs",
        )
        require(
            isinstance(environment.get("logical_cpu_count"), int)
            and environment["logical_cpu_count"] > 0,
            "logical CPU count is invalid",
        )
        require(bool(environment.get("cpu_model")), "CPU model is missing")
        require(bool(environment.get("compiler_version")), "compiler version is missing")
        require(round_value.get("warmup_iterations") == 10, "ncnn warmup differs")
        require(round_value.get("formal_iterations") == 100, "ncnn repeat differs")
        require(
            round_value.get("timing_boundaries")
            == {
                "preprocess": "shared preprocessing",
                "inference": "ncnn input bind, extract, validation and copy",
                "postprocess": "shared decode, threshold and NMS",
                "pipeline_total": (
                    "exact stage sum; excludes image read, model load, drawing and writes"
                ),
            },
            "ncnn timing boundaries differ",
        )

        resources = round_value.get("resource_measurement", {})
        cpu_percent = finite_nonnegative(
            resources.get("process_cpu_percent_one_core_basis"), "ncnn CPU percent"
        )
        cpu_delta = finite_nonnegative(
            resources.get("process_cpu_time_delta_seconds"),
            "ncnn CPU time",
            positive=True,
        )
        wall_delta = finite_nonnegative(
            resources.get("wall_clock_time_delta_seconds"),
            "ncnn wall time",
            positive=True,
        )
        require(
            math.isclose(cpu_percent, 100.0 * cpu_delta / wall_delta, rel_tol=1e-9),
            "ncnn CPU metric formula differs",
        )
        require(
            isinstance(resources.get("peak_rss_bytes"), int)
            and resources["peak_rss_bytes"] > 0,
            "ncnn peak RSS is invalid",
        )
        require(
            resources.get("peak_rss_is_process_level_not_model_only") is True,
            "ncnn peak RSS scope is not explicit",
        )
        require(
            resources.get("peak_rss_scope")
            == "process startup through formal measurement completion",
            "ncnn peak RSS time scope differs",
        )
        correctness = round_value.get("correctness", {})
        validate_benchmark_correctness(correctness.get("before_warmup"), "before warmup")
        validate_benchmark_correctness(
            correctness.get("after_measurement"), "after measurement"
        )

        samples = round_value.get("samples")
        require(isinstance(samples, list) and len(samples) == 100, "round samples differ")
        stage_values: dict[str, list[int]] = {stage: [] for stage in STAGES}
        for iteration, sample in enumerate(samples, start=1):
            require(sample.get("round") == round_index, "sample round differs")
            require(sample.get("iteration") == iteration, "sample iteration differs")
            require(
                sample.get("aggregate_sample_index")
                == (round_index - 1) * 100 + iteration,
                "aggregate sample index differs",
            )
            observed: dict[str, int] = {}
            for stage in STAGES:
                value = sample.get(f"{stage}_ns")
                require(
                    not isinstance(value, bool)
                    and isinstance(value, (int, float))
                    and math.isfinite(float(value))
                    and int(value) == value
                    and value > 0,
                    f"{stage} duration is invalid",
                )
                observed[stage] = int(value)
                stage_values[stage].append(int(value))
            require(
                observed["pipeline_total"]
                == observed["preprocess"] + observed["inference"] + observed["postprocess"],
                "pipeline total is not the exact stage sum",
            )
            all_samples.append(sample)
        round_summaries.append(
            {
                "round": round_index,
                "process_id": process_id,
                "process_started_unix_ns": process_started,
                "model_load_ms": round_value["model_load_ms"],
                "resource_measurement": resources,
                "correctness": correctness,
                "stages": {
                    stage: summarize_ns(stage_values[stage]) for stage in STAGES
                },
            }
        )

    require(process_starts == sorted(process_starts), "ncnn process order is not sequential")
    require(len(all_samples) == 500, "ncnn aggregate sample count differs")
    aggregate_stages = {
        stage: summarize_ns([sample[f"{stage}_ns"] for sample in all_samples])
        for stage in STAGES
    }
    round_pipeline_means = [
        value["stages"]["pipeline_total"]["mean_ms"] for value in round_summaries
    ]
    spread = maximum_relative_difference(round_pipeline_means)
    fastest = min(all_samples, key=lambda value: value["pipeline_total_ns"])
    slowest = max(all_samples, key=lambda value: value["pipeline_total_ns"])
    stability_limit = config["statistics"][
        "maximum_round_mean_relative_difference_percent"
    ]
    return {
        "backend": "cpp_ncnn",
        "sample_count": len(all_samples),
        "rounds": round_summaries,
        "aggregate": {
            "stages": aggregate_stages,
            "pipeline_fps_batch1_sequential": (
                1000.0 / aggregate_stages["pipeline_total"]["mean_ms"]
            ),
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
            "five_round_pipeline_mean_max_relative_difference_percent": spread,
            "stability_limit_percent": stability_limit,
            "stability_gate": "PASS" if spread <= stability_limit else "FAIL",
        },
    }


def benchmark_main(args: argparse.Namespace) -> int:
    config = load_json(args.benchmark_config)
    validate_benchmark_config(config)
    config_sha256 = sha256_file(args.benchmark_config)
    require(
        config_sha256
        == "64596e3fd469227c25c2e8c397aade0079867ef3e5e238eec83c50c3536c536d",
        "Task 009 benchmark config changed",
    )
    immutable_task009 = []
    for relative_path, expected_hash in TASK009_IMMUTABLE_ARTIFACTS.items():
        path = REPOSITORY_ROOT / relative_path
        observed_hash = sha256_file(path)
        require(observed_hash == expected_hash, f"immutable Task 009 artifact changed: {path}")
        immutable_task009.append({"path": relative_path, "sha256": observed_hash})

    payload = load_json(args.benchmark_input)
    summary = validate_ncnn_benchmark(payload, config, config_sha256)
    raw_sha256 = sha256_file(args.benchmark_input)
    summary_document = {
        "schema_version": 1,
        "evidence_type": "task011_ncnn_benchmark_summary",
        "campaign": "task011-ncnn-only-v1",
        "benchmark_config": {
            "path": str(args.benchmark_config),
            "sha256": config_sha256,
            "methodology_id": config["methodology_id"],
        },
        "raw_input": {"path": str(args.benchmark_input), "sha256": raw_sha256},
        "statistics_implementation": (
            "edgeai_benchmark.benchmark.summarize_ns and maximum_relative_difference"
        ),
        "percentile_method": "nearest-rank",
        "summary": summary,
        "all_raw_samples_preserved": True,
        "cross_campaign_note": (
            "Task 009 Python/C++ ORT data and Task 011 C++ ncnn data use aligned "
            "methods but were not collected in one synchronized three-backend campaign."
        ),
        "task012_reserved_campaign": (
            "Six-round three-backend balanced permutations with 600 new samples per backend."
        ),
        "status": "PENDING_HUMAN_REVIEW",
    }
    args.benchmark_summary.parent.mkdir(parents=True, exist_ok=True)
    args.benchmark_summary.write_text(
        json.dumps(summary_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_benchmark_csv(args.benchmark_csv, summary)
    report = {
        "schema_version": 1,
        "evidence_type": "task011_ncnn_benchmark_validation",
        "campaign": "task011-ncnn-only-v1",
        "raw_input": {"path": str(args.benchmark_input), "sha256": raw_sha256},
        "derived_outputs": [
            {
                "path": str(args.benchmark_summary),
                "sha256": sha256_file(args.benchmark_summary),
            },
            {"path": str(args.benchmark_csv), "sha256": sha256_file(args.benchmark_csv)},
        ],
        "immutable_task009_artifacts": immutable_task009,
        "checks": {
            "schema_and_identity": "PASS",
            "five_independent_processes": "PASS",
            "formal_sample_count": 500,
            "all_raw_samples_preserved": True,
            "exact_pipeline_stage_sum": "PASS",
            "correctness_before_and_after_every_round": "PASS_TARGET",
            "release_cpu_fp32_one_thread": "PASS",
            "task009_artifacts_unchanged": "PASS",
            "stability_gate": summary["aggregate"]["stability_gate"],
        },
        "summary": summary,
        "status": "PENDING_HUMAN_REVIEW",
    }
    args.benchmark_report.parent.mkdir(parents=True, exist_ok=True)
    args.benchmark_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    aggregate = summary["aggregate"]
    print("schema_validation=PASS")
    print("cpp_ncnn_processes=5")
    print("cpp_ncnn_samples=500")
    for stage in STAGES:
        values = aggregate["stages"][stage]
        print(f"cpp_ncnn_{stage}_mean_ms={values['mean_ms']:.6f}")
        print(f"cpp_ncnn_{stage}_p50_ms={values['p50_ms']:.6f}")
        print(f"cpp_ncnn_{stage}_p90_ms={values['p90_ms']:.6f}")
        print(f"cpp_ncnn_{stage}_min_ms={values['min_ms']:.6f}")
        print(f"cpp_ncnn_{stage}_max_ms={values['max_ms']:.6f}")
    print(
        "cpp_ncnn_pipeline_fps_batch1_sequential="
        f"{aggregate['pipeline_fps_batch1_sequential']:.6f}"
    )
    print(
        "cpp_ncnn_five_round_mean_relative_difference_percent="
        f"{aggregate['five_round_pipeline_mean_max_relative_difference_percent']:.6f}"
    )
    print(f"stability_gate={aggregate['stability_gate']}")
    print("status=PENDING_HUMAN_REVIEW")
    return 0 if aggregate["stability_gate"] == "PASS" else 2


def detection_main(args: argparse.Namespace) -> int:
    expected_minimum_iou = (
        NCNN_TARGET_MINIMUM_IOU
        if args.profile == "ncnn-preregistered"
        else FROZEN_MINIMUM_IOU
    )
    expected_maximum_delta = (
        NCNN_TARGET_MAXIMUM_CONFIDENCE_DELTA
        if args.profile == "ncnn-preregistered"
        else FROZEN_MAXIMUM_CONFIDENCE_DELTA
    )
    if args.min_iou != expected_minimum_iou:
        raise ComparisonError(f"--min-iou must remain frozen at {expected_minimum_iou}")
    if args.max_confidence_delta != expected_maximum_delta:
        raise ComparisonError(
            "--max-confidence-delta must remain frozen at "
            f"{expected_maximum_delta}"
        )
    reference_payload = load_json(args.reference)
    candidate_payload = load_json(args.candidate)
    reference = reference_payload.get("detections")
    candidate = candidate_payload.get("detections")
    if not isinstance(reference, list) or not isinstance(candidate, list):
        raise ComparisonError("both artifacts must contain a detections list")
    comparison_minimum_iou = (
        NCNN_HARD_MINIMUM_IOU
        if args.profile == "ncnn-preregistered"
        else args.min_iou
    )
    comparison_maximum_delta = (
        NCNN_HARD_MAXIMUM_CONFIDENCE_DELTA
        if args.profile == "ncnn-preregistered"
        else args.max_confidence_delta
    )
    matches = compare(
        reference,
        candidate,
        comparison_minimum_iou,
        comparison_maximum_delta,
    )
    minimum_observed_iou = min((match["iou"] for match in matches), default=1.0)
    maximum_observed_delta = max(
        (match["absolute_confidence_difference"] for match in matches), default=0.0
    )
    target_pass = (
        minimum_observed_iou >= args.min_iou
        and maximum_observed_delta <= args.max_confidence_delta
    )
    status = "PASS_TARGET" if args.profile == "ncnn-preregistered" else "PASS"
    if args.profile == "ncnn-preregistered" and not target_pass:
        status = "HUMAN_REVIEW_HARD_FLOOR_ONLY"
    evidence = {
        "schema_version": 1,
        "application": "edgeai_compare_detections",
        "reference": {
            "path": str(args.reference),
            "sha256": sha256_file(args.reference),
            "detection_count": len(reference),
        },
        "candidate": {
            "path": str(args.candidate),
            "sha256": sha256_file(args.candidate),
            "detection_count": len(candidate),
            "model_sha256": candidate_payload.get("model", {}).get("sha256"),
            "runtime_version": candidate_payload.get("model", {}).get("runtime_version"),
            "execution_provider": candidate_payload.get("model", {}).get(
                "execution_provider"
            ),
        },
        "profile": args.profile,
        "tolerances": {
            "minimum_iou": args.min_iou,
            "maximum_absolute_confidence_difference": args.max_confidence_delta,
        },
        "preregistered_gates": {
            "target": {
                "minimum_iou": args.min_iou,
                "maximum_absolute_confidence_difference": args.max_confidence_delta,
            },
            "hard_floor": {
                "minimum_iou": comparison_minimum_iou,
                "maximum_absolute_confidence_difference": comparison_maximum_delta,
            },
        },
        "matches": matches,
        "minimum_observed_iou": minimum_observed_iou,
        "maximum_observed_confidence_difference": maximum_observed_delta,
        "status": status,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Reference detections: {len(reference)}")
    print(f"Candidate detections: {len(candidate)}")
    print(f"Minimum matched IoU: {minimum_observed_iou:.12g}")
    print(f"Maximum confidence delta: {maximum_observed_delta:.12g}")
    print(f"Comparison status: {status}")
    print(f"Evidence: {args.output}")
    return 0 if target_pass else 2


def main() -> int:
    args = parse_args()
    if args.mode == "benchmark":
        return benchmark_main(args)
    return detection_main(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ComparisonError as error:
        raise SystemExit(f"detection comparison error: {error}") from error
    except (BenchmarkError, OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"benchmark validation error: {error}") from error
