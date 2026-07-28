#!/usr/bin/env python3
"""Validate and summarize the preregistered Task 017 ARM benchmark evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/benchmark_anlogic_arm.json"
DEFAULT_CONTRACT = ROOT / "results/evidence/017/benchmark_contract.json"
STAGES = ("preprocess", "inference", "postprocess", "pipeline")
EXPECTED_PARAM = "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
EXPECTED_BIN = "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
EXPECTED_INPUT = "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
EXPECTED_CONFIG = "82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d"
EXPECTED_GOLDEN = "fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9"
EXPECTED_MANIFEST = "9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff"
EXPECTED_NCNN_COMMIT = "56775de50990ab7f16627efdcf5529b49541206f"


class ValidationError(RuntimeError):
    """Raised when Task 017 contract or evidence is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"failed to read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_sha256(value: Any, description: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        f"{description} must be a lowercase SHA256",
    )
    return value


def finite_number(value: Any, description: str, *, positive: bool = False) -> float:
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{description} must be numeric",
    )
    result = float(value)
    require(math.isfinite(result), f"{description} must be finite")
    require(result > 0.0 if positive else result >= 0.0, f"{description} is out of range")
    return result


def integer(value: Any, description: str, *, positive: bool = False) -> int:
    require(
        not isinstance(value, bool) and isinstance(value, int),
        f"{description} must be an integer",
    )
    require(value > 0 if positive else value >= 0, f"{description} is out of range")
    return value


def validate_contract(config: dict[str, Any], contract: dict[str, Any], config_sha: str) -> None:
    require(config.get("schema_version") == 2, "Task 017 config schema differs")
    require(
        config.get("methodology_id") == "task017-anlogic-dr1-arm-cpu-v1",
        "Task 017 methodology differs",
    )
    environment = config.get("environment", {})
    require(environment.get("platform") == "Anlogic DR1 board", "platform differs")
    require(environment.get("board_model") == "MLK-F3P-CZ02-DR1M90", "board differs")
    require(environment.get("architecture") == "aarch64", "architecture differs")
    require(environment.get("cpu_pinning") == "disabled", "CPU pinning differs")
    require(
        environment.get("governor_policy") == "observe only; do not modify",
        "governor policy differs",
    )
    require(
        environment.get("required_environment_variables")
        == {
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
        },
        "thread environment differs",
    )
    workload = config.get("workload", {})
    require(workload.get("batch") == 1, "batch differs")
    require(workload.get("precision") == "FP32", "precision differs")
    require(workload.get("input_size") == [640, 640], "input size differs")
    require(workload.get("input_blob") == "in0", "input blob differs")
    require(workload.get("output_blob") == "out0", "output blob differs")
    require(workload.get("confidence_threshold") == 0.25, "confidence differs")
    require(workload.get("nms_iou_threshold") == 0.45, "NMS differs")
    expected_hashes = {
        "model_param": EXPECTED_PARAM,
        "model_bin": EXPECTED_BIN,
        "image": EXPECTED_INPUT,
        "inference_config": EXPECTED_CONFIG,
        "golden_result": EXPECTED_GOLDEN,
    }
    for name, expected in expected_hashes.items():
        require(
            workload.get(name, {}).get("sha256") == expected,
            f"{name} SHA256 differs",
        )
    runtime = config.get("runtime", {})
    require(runtime.get("tag") == "20240410", "ncnn tag differs")
    require(runtime.get("commit") == EXPECTED_NCNN_COMMIT, "ncnn commit differs")
    require(runtime.get("threads") == 1, "ncnn thread count differs")
    require(runtime.get("opencv_threads") == 1, "OpenCV thread count differs")
    for disabled in ("vulkan", "fp16", "bf16", "int8"):
        require(runtime.get(disabled) == 0, f"{disabled} must remain disabled")
    rounds = config.get("rounds", {})
    require(rounds.get("count") == 5, "round count differs")
    require(rounds.get("warmup") == 10, "warmup count differs")
    require(rounds.get("repeat") == 20, "measured repeat differs")
    require(rounds.get("required_valid_sample_count") == 100, "sample count differs")
    require(rounds.get("independent_process_per_round") is True, "process contract differs")
    require(rounds.get("latency_outlier_removal") is False, "outlier policy differs")
    timing = config.get("timing", {})
    require(
        timing.get("pipeline_total_formula")
        == "preprocess_ns + inference_ns + postprocess_ns",
        "pipeline formula differs",
    )
    stats = config.get("statistics", {})
    require(stats.get("percentile_method") == "nearest-rank", "percentile differs")
    require(
        stats.get("standard_deviation") == "sample; denominator count - 1",
        "standard deviation differs",
    )
    require(
        stats.get("fps_formula") == "1000 / aggregate_mean_pipeline_ms",
        "FPS formula differs",
    )
    require(stats.get("preserve_all_samples") is True, "sample retention differs")
    correctness = config.get("correctness", {})
    require(correctness.get("expected_detection_count") == 5, "detection count differs")
    require(correctness.get("minimum_class_matched_iou") == 0.99, "IoU gate differs")
    require(
        correctness.get("maximum_absolute_confidence_difference") == 0.01,
        "confidence gate differs",
    )

    require(contract.get("schema_version") == 1, "contract schema differs")
    require(contract.get("task") == "017", "contract task differs")
    require(contract.get("status") == "protocol_frozen_data_pending", "contract status differs")
    require(contract.get("benchmark_config_sha256") == config_sha, "config hash differs")
    require(contract.get("formal_data_collected") is False, "formal data must be pending")
    require(contract.get("published_performance_values") is False, "values must be unpublished")


def nearest_rank(values: Sequence[float], percentile: float) -> float:
    require(bool(values), "cannot summarize empty values")
    require(0.0 < percentile <= 1.0, "percentile is invalid")
    ordered = sorted(finite_number(value, "statistic") for value in values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def summarize_ns(values: Sequence[int]) -> dict[str, float | int]:
    checked = [integer(value, "raw duration", positive=True) for value in values]
    require(bool(checked), "cannot summarize empty durations")
    milliseconds = [value / 1_000_000.0 for value in checked]
    return {
        "count": len(checked),
        "mean_ms": sum(milliseconds) / len(milliseconds),
        "p50_ms": nearest_rank(milliseconds, 0.50),
        "p90_ms": nearest_rank(milliseconds, 0.90),
        "min_ms": min(milliseconds),
        "max_ms": max(milliseconds),
        "sample_standard_deviation_ms": statistics.stdev(milliseconds),
    }


def validate_correctness(value: Any, description: str) -> None:
    require(isinstance(value, dict), f"{description} is missing")
    require(value.get("status") == "PASS_TARGET", f"{description} status differs")
    require(value.get("detection_count") == 5, f"{description} detections differ")
    require(
        finite_number(value.get("minimum_class_matched_iou"), f"{description} IoU")
        >= 0.99,
        f"{description} IoU is below target",
    )
    require(
        finite_number(
            value.get("maximum_absolute_confidence_difference"),
            f"{description} confidence",
        )
        <= 0.01,
        f"{description} confidence exceeds target",
    )


def validate_environment(value: dict[str, Any], phase: str) -> None:
    require(value.get("schema_version") == 1, f"{phase} environment schema differs")
    require(value.get("evidence_type") == "task017_board_environment", f"{phase} type differs")
    require(value.get("phase") == phase, f"{phase} label differs")
    board = value.get("board", {})
    require(board.get("model") == "MLK-F3P-CZ02-DR1M90", f"{phase} board differs")
    require(board.get("architecture") == "aarch64", f"{phase} architecture differs")
    require(board.get("os") == "Buildroot 2022.02.6", f"{phase} OS differs")
    require(board.get("kernel") == "6.1.111-rt42", f"{phase} kernel differs")
    require(board.get("glibc") == "2.25", f"{phase} glibc differs")
    require(board.get("cpu_count") == 2, f"{phase} CPU count differs")
    for field in ("mem_total_kib", "mem_available_kib"):
        observed = value.get("memory", {}).get(field)
        require(observed is None or (isinstance(observed, int) and observed >= 0), f"{phase} {field}")
    for field in ("governors", "available_frequencies_khz", "current_frequencies_khz", "thermal_zones"):
        require(isinstance(value.get(field), list), f"{phase} {field} must be a list")


def validate_and_summarize(
    raw: dict[str, Any],
    config: dict[str, Any],
    config_sha: str,
    environment_before: dict[str, Any],
    environment_after: dict[str, Any],
) -> dict[str, Any]:
    validate_environment(environment_before, "before")
    validate_environment(environment_after, "after")
    require(raw.get("schema_version") == 2, "raw schema differs")
    require(
        raw.get("evidence_type") == "task017_anlogic_arm_raw_benchmark",
        "raw evidence type differs",
    )
    require(raw.get("backend") == "cpp_ncnn", "raw backend differs")
    require(raw.get("benchmark_config_sha256") == config_sha, "raw config hash differs")
    rounds = raw.get("rounds")
    require(isinstance(rounds, list) and len(rounds) == 5, "exactly five rounds required")

    process_ids: set[int] = set()
    process_starts: set[int] = set()
    all_stage_values: dict[str, list[int]] = {stage: [] for stage in STAGES}
    round_summaries: list[dict[str, Any]] = []
    model_load_values: list[float] = []
    peak_rss_values: list[int] = []
    executable_hashes: set[str] = set()
    total_samples = 0
    for expected_round, round_value in enumerate(rounds, 1):
        require(isinstance(round_value, dict), f"round {expected_round} is invalid")
        require(round_value.get("round") == expected_round, "round order differs")
        process_id = integer(round_value.get("process_id"), "process id", positive=True)
        process_started = integer(
            round_value.get("process_started_unix_ns"), "process start", positive=True
        )
        require(process_id not in process_ids, "process id was reused")
        require(process_started not in process_starts, "process start was reused")
        process_ids.add(process_id)
        process_starts.add(process_started)
        executable_hashes.add(
            require_sha256(round_value.get("executable_sha256"), "executable SHA256")
        )
        require(round_value.get("warmup_iterations") == 10, "round warmup differs")
        require(round_value.get("formal_iterations") == 20, "round repeat differs")
        require(round_value.get("ncnn_param_sha256") == EXPECTED_PARAM, "param hash differs")
        require(round_value.get("ncnn_bin_sha256") == EXPECTED_BIN, "bin hash differs")
        require(
            round_value.get("ncnn_manifest_sha256") == EXPECTED_MANIFEST,
            "manifest hash differs",
        )
        require(round_value.get("image_sha256") == EXPECTED_INPUT, "input hash differs")
        require(
            round_value.get("inference_config_sha256") == EXPECTED_CONFIG,
            "inference config hash differs",
        )
        require(round_value.get("golden_result_sha256") == EXPECTED_GOLDEN, "golden hash differs")
        require(
            round_value.get("reference_detections_sha256") == EXPECTED_GOLDEN,
            "reference hash differs",
        )
        runtime = round_value.get("runtime", {})
        require(runtime.get("ncnn_version") == "1.0.20240410", "ncnn version differs")
        require(runtime.get("threads") == 1, "runtime threads differ")
        for disabled in ("vulkan", "fp16", "bf16", "int8"):
            require(runtime.get(disabled) is False, f"runtime {disabled} differs")
        require(
            round_value.get("environment", {}).get("architecture") in ("aarch64", "arm64"),
            "round architecture differs",
        )
        correctness = round_value.get("correctness", {})
        validate_correctness(correctness.get("before_warmup"), "before correctness")
        validate_correctness(correctness.get("after_measurement"), "after correctness")
        model_load_values.append(
            finite_number(round_value.get("model_load_ms"), "model load", positive=True)
        )
        resources = round_value.get("resource_measurement", {})
        peak_rss_values.append(integer(resources.get("peak_rss_kib"), "Peak RSS", positive=True))
        require(
            resources.get("peak_rss_bytes") == peak_rss_values[-1] * 1024,
            "Peak RSS unit conversion differs",
        )
        finite_number(
            resources.get("process_cpu_percent_one_core_basis"),
            "process CPU percent",
        )
        samples = round_value.get("samples")
        require(isinstance(samples, list) and len(samples) == 20, "round must contain 20 samples")
        round_stage_values: dict[str, list[int]] = {stage: [] for stage in STAGES}
        for expected_iteration, sample in enumerate(samples, 1):
            require(isinstance(sample, dict), "sample must be an object")
            require(sample.get("round") == expected_round, "sample round differs")
            require(sample.get("iteration") == expected_iteration, "sample iteration differs")
            require(
                sample.get("aggregate_sample_index")
                == (expected_round - 1) * 20 + expected_iteration,
                "aggregate sample index differs",
            )
            pre = integer(sample.get("preprocess_ns"), "preprocess", positive=True)
            infer = integer(sample.get("inference_ns"), "inference", positive=True)
            post = integer(sample.get("postprocess_ns"), "postprocess", positive=True)
            pipeline = integer(sample.get("pipeline_total_ns"), "pipeline", positive=True)
            require(pipeline == pre + infer + post, "pipeline is not the exact stage sum")
            values = {
                "preprocess": pre,
                "inference": infer,
                "postprocess": post,
                "pipeline": pipeline,
            }
            for stage, nanoseconds in values.items():
                expected_ms = nanoseconds / 1_000_000.0
                observed_ms = finite_number(sample.get(f"{stage}_ms"), f"{stage} milliseconds")
                require(
                    math.isclose(observed_ms, expected_ms, rel_tol=0.0, abs_tol=1e-12),
                    f"{stage} millisecond conversion differs",
                )
                round_stage_values[stage].append(nanoseconds)
                all_stage_values[stage].append(nanoseconds)
            for optional_field in ("cpu_frequency_khz", "temperature_millicelsius"):
                observed = sample.get(optional_field)
                require(
                    observed is None or (isinstance(observed, int) and observed >= 0),
                    f"{optional_field} must be null or a nonnegative integer",
                )
            require(sample.get("error_status") is None, "valid sample error status differs")
        total_samples += len(samples)
        round_summaries.append(
            {
                "round": expected_round,
                "process_id": process_id,
                "process_started_unix_ns": process_started,
                "exit_code": 0,
                "model_load_ms": model_load_values[-1],
                "peak_rss_kib": peak_rss_values[-1],
                "stages": {
                    stage: summarize_ns(values) for stage, values in round_stage_values.items()
                },
            }
        )

    require(total_samples == 100, "exactly 100 measured samples required")
    require(len(executable_hashes) == 1, "all process rounds must use one executable")
    aggregate = {stage: summarize_ns(values) for stage, values in all_stage_values.items()}
    pipeline_round_means = [
        item["stages"]["pipeline"]["mean_ms"] for item in round_summaries
    ]
    spread = (
        (max(pipeline_round_means) - min(pipeline_round_means))
        / min(pipeline_round_means)
        * 100.0
    )
    maximum_spread = finite_number(
        config.get("statistics", {}).get("maximum_round_mean_relative_difference_percent"),
        "round spread gate",
        positive=True,
    )
    require(spread <= maximum_spread, "round pipeline mean spread exceeds the frozen gate")
    aggregate_pipeline_mean = float(aggregate["pipeline"]["mean_ms"])
    return {
        "schema_version": 1,
        "evidence_type": "task017_anlogic_arm_benchmark_summary",
        "benchmark_status": "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        "benchmark_config_sha256": config_sha,
        "runtime_contract": {
            "name": "ncnn",
            "tag": "20240410",
            "commit": EXPECTED_NCNN_COMMIT,
            "execution": "CPU-only FP32",
            "batch": 1,
            "input_size": [640, 640],
            "threads": 1,
            "vulkan": False,
            "fp16": False,
            "bf16": False,
            "int8": False,
            "executable_sha256": next(iter(executable_hashes)),
        },
        "asset_hashes": {
            "ncnn_manifest": EXPECTED_MANIFEST,
            "ncnn_param": EXPECTED_PARAM,
            "ncnn_bin": EXPECTED_BIN,
            "fixed_input": EXPECTED_INPUT,
            "inference_config": EXPECTED_CONFIG,
            "pc_ncnn_golden": EXPECTED_GOLDEN,
        },
        "board_identity": environment_before["board"],
        "sample_count": total_samples,
        "valid_process_rounds": len(rounds),
        "warmup_per_round": 10,
        "measured_per_round": 20,
        "percentile_method": "nearest-rank",
        "standard_deviation": "sample; denominator count - 1",
        "statistics": aggregate,
        "rounds": round_summaries,
        "pipeline_fps_batch1_sequential": 1000.0 / aggregate_pipeline_mean,
        "five_round_pipeline_mean_max_relative_difference_percent": spread,
        "model_load_ms": {
            "count": len(model_load_values),
            "mean": sum(model_load_values) / len(model_load_values),
            "min": min(model_load_values),
            "max": max(model_load_values),
        },
        "peak_rss_kib": {
            "count": len(peak_rss_values),
            "maximum": max(peak_rss_values),
            "per_round": peak_rss_values,
        },
        "correctness_before_after": "PASS_TARGET",
        "environment": {
            "before": environment_before,
            "after": environment_after,
        },
        "outlier_policy": "all 100 valid samples retained; no latency-based deletion",
        "formal_publication": "PENDING_HUMAN_REVIEW",
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_check_contract(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    contract = load_json(args.contract)
    validate_contract(config, contract, sha256_file(args.config))
    print("task017_contract=PASS")
    print(f"benchmark_config_sha256={sha256_file(args.config)}")
    print("formal_data_collected=false")
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    contract = load_json(args.contract)
    config_sha = sha256_file(args.config)
    validate_contract(config, contract, config_sha)
    raw = load_json(args.raw)
    environment_before = load_json(args.environment_before)
    environment_after = load_json(args.environment_after)
    summary = validate_and_summarize(
        raw, config, config_sha, environment_before, environment_after
    )
    write_json(args.summary, summary)
    validation = {
        "schema_version": 1,
        "evidence_type": "task017_anlogic_arm_benchmark_validation",
        "status": "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        "raw_sha256": sha256_file(args.raw),
        "environment_before_sha256": sha256_file(args.environment_before),
        "environment_after_sha256": sha256_file(args.environment_after),
        "summary_sha256": sha256_file(args.summary),
        "benchmark_config_sha256": config_sha,
        "checks": {
            "five_independent_processes": "PASS",
            "one_hundred_samples": "PASS",
            "exact_stage_sums": "PASS",
            "all_samples_retained": "PASS",
            "correctness_before_after": "PASS_TARGET",
            "frozen_asset_hashes": "PASS",
            "nearest_rank_and_sample_stddev": "PASS",
            "fps_recomputed": "PASS",
            "environment_schema": "PASS",
        },
        "human_review": "PENDING",
    }
    write_json(args.validation, validation)
    print("task017_validation=PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW")
    print("sample_count=100")
    print("valid_process_rounds=5")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-contract", help="validate frozen protocol only")
    check.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    check.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    check.set_defaults(handler=command_check_contract)
    summarize = subparsers.add_parser("summarize", help="validate real raw evidence")
    summarize.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    summarize.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    summarize.add_argument("--raw", type=Path, required=True)
    summarize.add_argument("--environment-before", type=Path, required=True)
    summarize.add_argument("--environment-after", type=Path, required=True)
    summarize.add_argument("--summary", type=Path, required=True)
    summarize.add_argument("--validation", type=Path, required=True)
    summarize.set_defaults(handler=command_summarize)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.handler(args))
    except ValidationError as error:
        print(f"Task 017 validation error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
