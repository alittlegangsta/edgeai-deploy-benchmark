#!/usr/bin/env python3
"""Validate the preregistered Task 018 paired ARM threading experiment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/benchmark_anlogic_arm_threading.json"
DEFAULT_CONTRACT = ROOT / "results/evidence/018/experiment_contract.json"
DEFAULT_ORDER = ROOT / "results/evidence/018/execution_order.json"
TASK017_VALIDATOR_PATH = ROOT / "scripts/vendor/validate_anlogic_arm_benchmark.py"
TASK017_SUMMARY = ROOT / "results/evidence/017/benchmark_summary.json"

_SPEC = importlib.util.spec_from_file_location(
    "task017_benchmark_validator", TASK017_VALIDATOR_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("failed to load the Task 017 benchmark validator")
TASK017 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(TASK017)

STAGES = ("preprocess", "inference", "postprocess", "pipeline")
EXPECTED_SCHEDULE = (
    (1, ((1, 1), (2, 2))),
    (2, ((1, 2), (2, 1))),
    (3, ((1, 1), (2, 2))),
    (4, ((1, 2), (2, 1))),
    (5, ((1, 1), (2, 2))),
)
TASK017_PIPELINE_MEAN_MS = 3513.99235361


class ValidationError(RuntimeError):
    """Raised when a Task 018 contract or evidence object is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"failed to read JSON {path}: {error}") from error
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return TASK017.sha256_file(path)


def finite_number(value: Any, description: str, *, positive: bool = False) -> float:
    try:
        return TASK017.finite_number(value, description, positive=positive)
    except TASK017.ValidationError as error:
        raise ValidationError(str(error)) from error


def integer(value: Any, description: str, *, positive: bool = False) -> int:
    try:
        return TASK017.integer(value, description, positive=positive)
    except TASK017.ValidationError as error:
        raise ValidationError(str(error)) from error


def require_sha256(value: Any, description: str) -> str:
    try:
        return TASK017.require_sha256(value, description)
    except TASK017.ValidationError as error:
        raise ValidationError(str(error)) from error


def expected_order(pair: int, configured_threads: int) -> int:
    require(pair in range(1, 6), "pair index is outside 1..5")
    require(configured_threads in (1, 2), "configured thread condition must be 1 or 2")
    first = 1 if pair % 2 == 1 else 2
    return 1 if configured_threads == first else 2


def validate_execution_order(order: dict[str, Any]) -> None:
    require(order.get("schema_version") == 1, "execution-order schema differs")
    require(order.get("task") == "018", "execution-order task differs")
    require(
        order.get("methodology_id")
        == "task018-anlogic-dr1-arm-cpu-threading-v1",
        "execution-order methodology differs",
    )
    pairs = order.get("pairs")
    require(isinstance(pairs, list) and len(pairs) == 5, "exactly five pairs required")
    observed: list[tuple[int, tuple[tuple[int, int], ...]]] = []
    for value in pairs:
        require(isinstance(value, dict), "execution-order pair must be an object")
        pair = integer(value.get("pair"), "pair", positive=True)
        executions = value.get("executions")
        require(
            isinstance(executions, list) and len(executions) == 2,
            "each pair must contain two executions",
        )
        observed_executions = []
        for execution in executions:
            require(isinstance(execution, dict), "execution must be an object")
            observed_executions.append(
                (
                    integer(execution.get("execution_order"), "execution order", positive=True),
                    integer(
                        execution.get("configured_threads"),
                        "configured threads",
                        positive=True,
                    ),
                )
            )
        observed.append((pair, tuple(observed_executions)))
    require(tuple(observed) == EXPECTED_SCHEDULE, "paired alternating order differs")
    require(order.get("independent_processes") == 10, "process total differs")
    require(order.get("measured_samples_per_condition") == 100, "condition total differs")
    require(order.get("total_measured_samples") == 200, "sample total differs")
    require(order.get("formal_data_collected") is False, "order preregistration changed")


def validate_contract(
    config: dict[str, Any],
    contract: dict[str, Any],
    order: dict[str, Any],
    config_sha: str,
    order_sha: str,
) -> None:
    require(config.get("schema_version") == 3, "Task 018 config schema differs")
    require(
        config.get("methodology_id")
        == "task018-anlogic-dr1-arm-cpu-threading-v1",
        "Task 018 methodology differs",
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
    required_environment = environment.get("required_environment_variables")
    original_environment = {
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    }
    openmp_environment = {
        **original_environment,
        "OMP_NUM_THREADS": "configured_threads",
    }
    is_openmp_instrument = required_environment == openmp_environment
    require(
        required_environment in (original_environment, openmp_environment),
        "non-ncnn thread environment differs",
    )
    if is_openmp_instrument:
        require(
            environment.get("thread_instrument_revision") == "openmp-v2",
            "OpenMP instrument revision differs",
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
        "ncnn_manifest": TASK017.EXPECTED_MANIFEST,
        "model_param": TASK017.EXPECTED_PARAM,
        "model_bin": TASK017.EXPECTED_BIN,
        "image": TASK017.EXPECTED_INPUT,
        "inference_config": TASK017.EXPECTED_CONFIG,
        "golden_result": TASK017.EXPECTED_GOLDEN,
    }
    for name, expected in expected_hashes.items():
        require(workload.get(name, {}).get("sha256") == expected, f"{name} hash differs")
    runtime = config.get("runtime", {})
    require(runtime.get("tag") == "20240410", "ncnn tag differs")
    require(runtime.get("commit") == TASK017.EXPECTED_NCNN_COMMIT, "ncnn commit differs")
    require(runtime.get("thread_conditions") == [1, 2], "thread conditions differ")
    require(runtime.get("opencv_threads") == 1, "OpenCV threads differ")
    require(
        runtime.get("only_experimental_variable") == "configured_threads",
        "experimental variable differs",
    )
    for disabled in ("vulkan", "fp16", "bf16", "int8"):
        require(runtime.get(disabled) == 0, f"{disabled} must remain disabled")
    rounds = config.get("rounds", {})
    require(rounds.get("count_per_condition") == 5, "round count differs")
    require(rounds.get("warmup") == 10, "warmup differs")
    require(rounds.get("repeat") == 20, "repeat differs")
    require(
        rounds.get("required_valid_sample_count_per_condition") == 100,
        "condition sample count differs",
    )
    require(rounds.get("required_total_processes") == 10, "process total differs")
    require(rounds.get("required_total_valid_sample_count") == 200, "sample total differs")
    require(rounds.get("latency_outlier_removal") is False, "outlier policy differs")
    timing = config.get("timing", {})
    require(
        timing.get("pipeline_total_formula")
        == "preprocess_ns + inference_ns + postprocess_ns",
        "pipeline formula differs",
    )
    statistics = config.get("statistics", {})
    require(statistics.get("percentile_method") == "nearest-rank", "percentile differs")
    require(
        statistics.get("standard_deviation") == "sample; denominator count - 1",
        "standard deviation differs",
    )
    require(
        statistics.get("fps_formula") == "1000 / aggregate_mean_pipeline_ms",
        "FPS formula differs",
    )
    require(
        statistics.get("maximum_round_mean_relative_difference_percent") == 10.0,
        "stability gate differs",
    )
    comparison = config.get("comparison", {})
    require(
        comparison.get("beneficial_minimum_pipeline_speedup") == 1.05,
        "beneficial threshold differs",
    )
    require(
        comparison.get("neutral_minimum_pipeline_speedup") == 0.98,
        "neutral threshold differs",
    )
    require(
        comparison.get("classification_values")
        == ["BENEFICIAL", "NEUTRAL", "REGRESSION"],
        "classification values differ",
    )
    history = config.get("historical_consistency", {})
    require(
        math.isclose(
            finite_number(history.get("task017_pipeline_mean_ms"), "Task 017 mean"),
            TASK017_PIPELINE_MEAN_MS,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "Task 017 historical mean differs",
    )
    require(
        history.get("maximum_absolute_mean_pipeline_difference_percent") == 10.0,
        "historical drift gate differs",
    )
    config_pairs = config.get("pairs", {}).get("execution_order")
    require(isinstance(config_pairs, list) and len(config_pairs) == 5, "config pairs differ")
    for expected_pair, value in enumerate(config_pairs, 1):
        require(value.get("pair") == expected_pair, "config pair identity differs")
        expected_conditions = [1, 2] if expected_pair % 2 == 1 else [2, 1]
        require(value.get("conditions") == expected_conditions, "config pair order differs")

    validate_execution_order(order)
    require(contract.get("schema_version") == 1, "contract schema differs")
    require(contract.get("task") == "018", "contract task differs")
    require(contract.get("status") == "protocol_frozen_data_pending", "contract status differs")
    if is_openmp_instrument:
        require(
            contract.get("instrument_revision") == "openmp-v2",
            "contract OpenMP instrument revision differs",
        )
        require(
            contract.get("instrument_correction")
            == "results/evidence/018/openmp/instrument_correction.json",
            "instrument correction evidence differs",
        )
    else:
        require("instrument_revision" not in contract, "original contract gained an instrument")
    require(contract.get("experiment_config_sha256") == config_sha, "config hash differs")
    require(contract.get("execution_order_sha256") == order_sha, "order hash differs")
    require(contract.get("formal_data_collected") is False, "formal data must be pending")
    require(contract.get("published_performance_values") is False, "values must be pending")


def detection_iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_box = left.get("box_xyxy_source")
    right_box = right.get("box_xyxy_source")
    require(
        isinstance(left_box, list) and len(left_box) == 4
        and isinstance(right_box, list) and len(right_box) == 4,
        "cross-condition detection box is invalid",
    )
    l = [finite_number(value, "left detection coordinate") for value in left_box]
    r = [finite_number(value, "right detection coordinate") for value in right_box]
    require(l[2] > l[0] and l[3] > l[1] and r[2] > r[0] and r[3] > r[1], "box is invalid")
    intersection_width = max(0.0, min(l[2], r[2]) - max(l[0], r[0]))
    intersection_height = max(0.0, min(l[3], r[3]) - max(l[1], r[1]))
    intersection = intersection_width * intersection_height
    union = (l[2] - l[0]) * (l[3] - l[1]) + (r[2] - r[0]) * (r[3] - r[1]) - intersection
    require(union > 0.0, "cross-condition detection union is invalid")
    return intersection / union


def validate_detections(value: Any, description: str) -> list[dict[str, Any]]:
    require(isinstance(value, list) and len(value) == 5, f"{description} detections differ")
    result = []
    for expected_rank, detection in enumerate(value, 1):
        require(isinstance(detection, dict), f"{description} detection must be an object")
        require(detection.get("rank") == expected_rank, f"{description} rank differs")
        integer(detection.get("class_id"), f"{description} class id")
        require(isinstance(detection.get("class_name"), str), f"{description} class name")
        finite_number(detection.get("confidence"), f"{description} confidence")
        detection_iou(detection, detection)
        result.append(detection)
    return result


def validate_correctness(value: Any, description: str) -> list[dict[str, Any]]:
    require(isinstance(value, dict), f"{description} is missing")
    require(value.get("status") == "PASS_TARGET", f"{description} status differs")
    require(value.get("detection_count") == 5, f"{description} detection count differs")
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
    return validate_detections(value.get("detections"), description)


def compare_detection_snapshots(
    snapshots: Iterable[list[dict[str, Any]]],
) -> dict[str, float | str]:
    values = list(snapshots)
    require(bool(values), "no correctness snapshots were captured")
    reference = values[0]
    minimum_iou = 1.0
    maximum_confidence_delta = 0.0
    for observed in values[1:]:
        require(len(observed) == len(reference), "cross-condition detection count differs")
        for expected, candidate in zip(reference, observed):
            require(
                candidate.get("rank") == expected.get("rank")
                and candidate.get("class_id") == expected.get("class_id")
                and candidate.get("class_name") == expected.get("class_name"),
                "cross-condition class identity differs",
            )
            minimum_iou = min(minimum_iou, detection_iou(expected, candidate))
            maximum_confidence_delta = max(
                maximum_confidence_delta,
                abs(
                    finite_number(expected.get("confidence"), "reference confidence")
                    - finite_number(candidate.get("confidence"), "candidate confidence")
                ),
            )
    require(minimum_iou >= 0.99, "cross-condition IoU is below target")
    require(maximum_confidence_delta <= 0.01, "cross-condition confidence exceeds target")
    return {
        "status": "PASS_TARGET",
        "minimum_class_matched_iou": minimum_iou,
        "maximum_absolute_confidence_difference": maximum_confidence_delta,
    }


def summarize_condition(
    raw: dict[str, Any],
    *,
    configured_threads: int,
    config_sha: str,
    openmp_instrument: bool,
    all_process_ids: set[int],
    all_process_starts: set[int],
) -> tuple[dict[str, Any], list[list[dict[str, Any]]]]:
    require(raw.get("schema_version") == 3, "raw schema differs")
    require(
        raw.get("evidence_type") == "task018_anlogic_arm_threading_raw_benchmark",
        "raw evidence type differs",
    )
    require(raw.get("backend") == "cpp_ncnn", "raw backend differs")
    require(raw.get("benchmark_config_sha256") == config_sha, "raw config hash differs")
    rounds = raw.get("rounds")
    require(isinstance(rounds, list) and len(rounds) == 5, "exactly five rounds required")
    stage_values: dict[str, list[int]] = {stage: [] for stage in STAGES}
    round_summaries = []
    model_load_values = []
    peak_rss_values = []
    executable_hashes: set[str] = set()
    correctness_snapshots: list[list[dict[str, Any]]] = []
    for pair_index, round_value in enumerate(rounds, 1):
        require(isinstance(round_value, dict), "round must be an object")
        execution_order = expected_order(pair_index, configured_threads)
        require(round_value.get("round") == pair_index, "round identity differs")
        require(round_value.get("pair_index") == pair_index, "pair identity differs")
        require(round_value.get("execution_order") == execution_order, "execution order differs")
        require(
            round_value.get("thread_condition") == configured_threads,
            "round thread condition differs",
        )
        process_id = integer(round_value.get("process_id"), "process id", positive=True)
        process_start = integer(
            round_value.get("process_started_unix_ns"), "process start", positive=True
        )
        require(process_id not in all_process_ids, "process id was reused")
        require(process_start not in all_process_starts, "process start was reused")
        all_process_ids.add(process_id)
        all_process_starts.add(process_start)
        executable_hashes.add(
            require_sha256(round_value.get("executable_sha256"), "executable SHA256")
        )
        require(round_value.get("warmup_iterations") == 10, "warmup count differs")
        require(round_value.get("formal_iterations") == 20, "repeat count differs")
        require(
            round_value.get("ncnn_manifest_sha256") == TASK017.EXPECTED_MANIFEST,
            "manifest hash differs",
        )
        require(round_value.get("ncnn_param_sha256") == TASK017.EXPECTED_PARAM, "param differs")
        require(round_value.get("ncnn_bin_sha256") == TASK017.EXPECTED_BIN, "bin differs")
        require(round_value.get("image_sha256") == TASK017.EXPECTED_INPUT, "input differs")
        require(
            round_value.get("inference_config_sha256") == TASK017.EXPECTED_CONFIG,
            "inference config differs",
        )
        require(
            round_value.get("golden_result_sha256") == TASK017.EXPECTED_GOLDEN,
            "golden differs",
        )
        runtime = round_value.get("runtime", {})
        require(runtime.get("ncnn_version") == "1.0.20240410", "ncnn version differs")
        require(runtime.get("threads") == configured_threads, "runtime threads differ")
        require(
            runtime.get("configured_threads") == configured_threads,
            "configured threads differ",
        )
        for disabled in ("vulkan", "fp16", "bf16", "int8"):
            require(runtime.get(disabled) is False, f"runtime {disabled} differs")
        environment_variables = round_value.get("environment", {}).get(
            "environment_variables", {}
        )
        require(
            environment_variables.get("OMP_NUM_THREADS")
            == str(configured_threads if openmp_instrument else 1),
            "observed OMP_NUM_THREADS differs",
        )
        if openmp_instrument:
            capabilities = runtime.get("thread_capabilities", {})
            require(
                capabilities.get("ncnn_openmp_compiled") is True,
                "OpenMP-enabled instrument reports OpenMP disabled",
            )
            require(
                capabilities.get("ncnn_threads_compiled") is True,
                "OpenMP-enabled instrument reports ncnn threads disabled",
            )
            require(
                capabilities.get("ncnn_simpleomp_compiled") is False,
                "standard libgomp instrument unexpectedly reports simpleomp",
            )
            require(
                capabilities.get("compiler_openmp_macro_defined") is True,
                "OpenMP compiler macro is missing",
            )
            require(
                capabilities.get("effective_parallel_backend") == "openmp",
                "effective parallel backend differs",
            )
        require(
            round_value.get("environment", {}).get("architecture") in ("aarch64", "arm64"),
            "round architecture differs",
        )
        correctness = round_value.get("correctness", {})
        correctness_snapshots.append(
            validate_correctness(correctness.get("before_warmup"), "before correctness")
        )
        correctness_snapshots.append(
            validate_correctness(correctness.get("after_measurement"), "after correctness")
        )
        model_load_values.append(
            finite_number(round_value.get("model_load_ms"), "model load", positive=True)
        )
        resources = round_value.get("resource_measurement", {})
        peak_rss = integer(resources.get("peak_rss_kib"), "Peak RSS", positive=True)
        require(resources.get("peak_rss_bytes") == peak_rss * 1024, "Peak RSS conversion differs")
        finite_number(
            resources.get("process_cpu_percent_one_core_basis"),
            "process CPU percent",
        )
        peak_rss_values.append(peak_rss)
        samples = round_value.get("samples")
        require(isinstance(samples, list) and len(samples) == 20, "round must have 20 samples")
        per_round: dict[str, list[int]] = {stage: [] for stage in STAGES}
        for iteration, sample in enumerate(samples, 1):
            require(isinstance(sample, dict), "sample must be an object")
            require(sample.get("round") == pair_index, "sample round differs")
            require(sample.get("pair_index") == pair_index, "sample pair differs")
            require(sample.get("execution_order") == execution_order, "sample order differs")
            require(
                sample.get("configured_threads") == configured_threads,
                "sample thread condition differs",
            )
            require(sample.get("iteration") == iteration, "sample iteration differs")
            require(
                sample.get("aggregate_sample_index") == (pair_index - 1) * 20 + iteration,
                "aggregate sample index differs",
            )
            preprocess = integer(sample.get("preprocess_ns"), "preprocess", positive=True)
            inference = integer(sample.get("inference_ns"), "inference", positive=True)
            postprocess = integer(sample.get("postprocess_ns"), "postprocess", positive=True)
            pipeline = integer(sample.get("pipeline_total_ns"), "pipeline", positive=True)
            require(
                pipeline == preprocess + inference + postprocess,
                "pipeline is not the exact stage sum",
            )
            values = {
                "preprocess": preprocess,
                "inference": inference,
                "postprocess": postprocess,
                "pipeline": pipeline,
            }
            for stage, nanoseconds in values.items():
                expected_ms = nanoseconds / 1_000_000.0
                observed_ms = finite_number(sample.get(f"{stage}_ms"), f"{stage} ms")
                require(
                    math.isclose(observed_ms, expected_ms, rel_tol=0.0, abs_tol=1e-12),
                    f"{stage} millisecond conversion differs",
                )
                per_round[stage].append(nanoseconds)
                stage_values[stage].append(nanoseconds)
            for optional_field in ("cpu_frequency_khz", "temperature_millicelsius"):
                observed = sample.get(optional_field)
                require(
                    observed is None or (
                        not isinstance(observed, bool)
                        and isinstance(observed, int)
                        and observed >= 0
                    ),
                    f"{optional_field} must be JSON null or nonnegative integer",
                )
            require(sample.get("error_status") is None, "valid sample error differs")
        round_summaries.append(
            {
                "round": pair_index,
                "pair_index": pair_index,
                "execution_order": execution_order,
                "configured_threads": configured_threads,
                "process_id": process_id,
                "process_started_unix_ns": process_start,
                "exit_code": 0,
                "model_load_ms": model_load_values[-1],
                "peak_rss_kib": peak_rss,
                "statistics": {
                    stage: TASK017.summarize_ns(values)
                    for stage, values in per_round.items()
                },
            }
        )
    require(len(executable_hashes) == 1, "conditions must use one executable")
    aggregate = {
        stage: TASK017.summarize_ns(values) for stage, values in stage_values.items()
    }
    round_means = [value["statistics"]["pipeline"]["mean_ms"] for value in round_summaries]
    spread = (max(round_means) - min(round_means)) / min(round_means) * 100.0
    return (
        {
            "schema_version": 1,
            "configured_threads": configured_threads,
            "sample_count": sum(len(value["samples"]) for value in rounds),
            "valid_process_rounds": len(rounds),
            "warmup_per_round": 10,
            "measured_per_round": 20,
            "statistics": aggregate,
            "rounds": round_summaries,
            "pipeline_fps_batch1_sequential": 1000.0
            / float(aggregate["pipeline"]["mean_ms"]),
            "five_round_pipeline_mean_max_relative_difference_percent": spread,
            "stability_gate_percent": 10.0,
            "stability_status": "PASS" if spread <= 10.0 else "FAIL",
            "model_load_ms": {
                "count": 5,
                "mean": sum(model_load_values) / len(model_load_values),
                "min": min(model_load_values),
                "max": max(model_load_values),
            },
            "peak_rss_kib": {
                "count": 5,
                "maximum": max(peak_rss_values),
                "per_round": peak_rss_values,
            },
            "executable_sha256": next(iter(executable_hashes)),
            "correctness_before_after": "PASS_TARGET",
        },
        correctness_snapshots,
    )


def validate_process_environment(
    value: dict[str, Any],
) -> None:
    require(value.get("schema_version") == 1, "process environment schema differs")
    require(
        value.get("evidence_type") == "task018_process_environment",
        "process environment type differs",
    )
    require(value.get("system_modification") is False, "system modification is forbidden")
    require(
        value.get("new_runtime_dependencies") is False,
        "new runtime dependency was introduced",
    )
    events = value.get("events")
    require(isinstance(events, list) and len(events) == 20, "20 environment events required")
    expected = []
    for pair, executions in EXPECTED_SCHEDULE:
        for execution_order, configured_threads in executions:
            expected.extend(
                [
                    (pair, execution_order, configured_threads, "before"),
                    (pair, execution_order, configured_threads, "after"),
                ]
            )
    observed = []
    for event in events:
        require(isinstance(event, dict), "environment event must be an object")
        identity = (
            integer(event.get("pair_index"), "environment pair", positive=True),
            integer(event.get("execution_order"), "environment order", positive=True),
            integer(event.get("configured_threads"), "environment threads", positive=True),
            event.get("phase"),
        )
        observed.append(identity)
        require(event.get("board_model") == "MLK-F3P-CZ02-DR1M90", "environment board differs")
        require(event.get("architecture") in ("aarch64", "arm64"), "environment arch differs")
        require(isinstance(event.get("load_average"), list), "load average must be a list")
        for field in ("cpu_frequency_khz", "temperature_millicelsius"):
            sensor = event.get(field)
            require(
                sensor is None or (
                    not isinstance(sensor, bool) and isinstance(sensor, int) and sensor >= 0
                ),
                f"environment {field} must be JSON null or nonnegative integer",
            )
    require(observed == expected, "process environment order differs")


def classify_result(
    *,
    pipeline_speedup: float,
    threads1_p90_ms: float,
    threads2_p90_ms: float,
    threads1_correctness: bool = True,
    threads2_correctness: bool = True,
    threads1_stability: bool = True,
    threads2_stability: bool = True,
    runtime_resource_issue: bool = False,
) -> str:
    values = (
        pipeline_speedup,
        threads1_p90_ms,
        threads2_p90_ms,
    )
    require(all(math.isfinite(value) and value > 0.0 for value in values), "classification input")
    if (
        not threads1_correctness
        or not threads2_correctness
        or not threads1_stability
        or not threads2_stability
        or runtime_resource_issue
        or pipeline_speedup < 0.98
    ):
        return "REGRESSION"
    if pipeline_speedup < 1.05:
        return "NEUTRAL"
    if threads2_p90_ms <= threads1_p90_ms:
        return "BENEFICIAL"
    return "REGRESSION"


def human_review_record(
    *,
    approve_candidate: bool,
    source: str | None,
    recorded_at: str | None,
) -> dict[str, Any]:
    if not approve_candidate:
        require(source is None and recorded_at is None, "approval metadata requires approval")
        return {
            "human_review": "PENDING",
            "human_review_source": None,
            "candidate_approved": False,
            "human_review_recorded_at": None,
        }
    require(source == "user", "approved review source must be user")
    require(isinstance(recorded_at, str) and bool(recorded_at), "approval time is required")
    try:
        parsed = datetime.fromisoformat(recorded_at)
    except ValueError as error:
        raise ValidationError("approval time must be ISO 8601") from error
    require(parsed.tzinfo is not None, "approval time must include timezone")
    return {
        "human_review": "PASS",
        "human_review_source": "user",
        "candidate_approved": True,
        "human_review_recorded_at": recorded_at,
    }


def validate_and_summarize(
    *,
    threads1_raw: dict[str, Any],
    threads2_raw: dict[str, Any],
    process_environment: dict[str, Any],
    config: dict[str, Any],
    config_sha: str,
    review: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if review is None:
        review = human_review_record(
            approve_candidate=False, source=None, recorded_at=None
        )
    process_ids: set[int] = set()
    process_starts: set[int] = set()
    openmp_instrument = (
        config.get("environment", {})
        .get("required_environment_variables", {})
        .get("OMP_NUM_THREADS")
        == "configured_threads"
    )
    threads1, snapshots1 = summarize_condition(
        threads1_raw,
        configured_threads=1,
        config_sha=config_sha,
        openmp_instrument=openmp_instrument,
        all_process_ids=process_ids,
        all_process_starts=process_starts,
    )
    threads2, snapshots2 = summarize_condition(
        threads2_raw,
        configured_threads=2,
        config_sha=config_sha,
        openmp_instrument=openmp_instrument,
        all_process_ids=process_ids,
        all_process_starts=process_starts,
    )
    require(len(process_ids) == 10, "ten independent process IDs required")
    require(
        threads1["executable_sha256"] == threads2["executable_sha256"],
        "thread conditions must use the same executable",
    )
    validate_process_environment(process_environment)
    cross_correctness = compare_detection_snapshots(snapshots1 + snapshots2)
    t1_pipeline = float(threads1["statistics"]["pipeline"]["mean_ms"])
    t2_pipeline = float(threads2["statistics"]["pipeline"]["mean_ms"])
    t1_inference = float(threads1["statistics"]["inference"]["mean_ms"])
    t2_inference = float(threads2["statistics"]["inference"]["mean_ms"])
    t1_fps = float(threads1["pipeline_fps_batch1_sequential"])
    t2_fps = float(threads2["pipeline_fps_batch1_sequential"])
    t1_rss = int(threads1["peak_rss_kib"]["maximum"])
    t2_rss = int(threads2["peak_rss_kib"]["maximum"])
    comparison = {
        "schema_version": 1,
        "evidence_type": "task018_anlogic_arm_threading_comparison",
        "pipeline_speedup": t1_pipeline / t2_pipeline,
        "inference_speedup": t1_inference / t2_inference,
        "fps_gain_percent": (t2_fps / t1_fps - 1.0) * 100.0,
        "rss_change_percent": (t2_rss / t1_rss - 1.0) * 100.0,
        "cross_condition_correctness": cross_correctness,
        "task017_historical_consistency": {
            "historical_pipeline_mean_ms": TASK017_PIPELINE_MEAN_MS,
            "contemporaneous_threads1_pipeline_mean_ms": t1_pipeline,
            "absolute_difference_percent": abs(
                t1_pipeline - TASK017_PIPELINE_MEAN_MS
            )
            / TASK017_PIPELINE_MEAN_MS
            * 100.0,
        },
    }
    history_difference = float(
        comparison["task017_historical_consistency"]["absolute_difference_percent"]
    )
    comparison["task017_historical_consistency"]["status"] = (
        "PASS" if history_difference <= 10.0 else "WARNING_ENVIRONMENT_DRIFT"
    )
    classification = classify_result(
        pipeline_speedup=float(comparison["pipeline_speedup"]),
        threads1_p90_ms=float(threads1["statistics"]["pipeline"]["p90_ms"]),
        threads2_p90_ms=float(threads2["statistics"]["pipeline"]["p90_ms"]),
        threads1_stability=threads1["stability_status"] == "PASS",
        threads2_stability=threads2["stability_status"] == "PASS",
    )
    comparison["classification"] = classification
    comparison["resource_policy"] = (
        "Peak RSS change disclosed; no preregistered RSS rejection threshold"
    )
    comparison.update(review)
    approved = review["candidate_approved"] is True
    comparison["experiment_status"] = (
        "PASS" if approved else "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW"
    )
    validation = {
        "schema_version": 1,
        "evidence_type": "task018_anlogic_arm_threading_validation",
        "status": "PASS" if approved else "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        "checks": {
            "ten_independent_processes": "PASS",
            "one_hundred_samples_per_condition": "PASS",
            "alternating_execution_order": "PASS",
            "only_variable_configured_threads": "PASS",
            "exact_stage_sums": "PASS",
            "all_samples_retained": "PASS",
            "correctness_before_after": "PASS_TARGET",
            "cross_condition_correctness": "PASS_TARGET",
            "statistics_and_speedup_recomputed": "PASS",
            "environment_schema": "PASS",
            "task017_history_immutable": "PASS",
        },
        "classification": classification,
        "historical_consistency_status": comparison[
            "task017_historical_consistency"
        ]["status"],
    }
    validation.update(review)
    return threads1, threads2, comparison, validation


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assemble_process_environment(path: Path) -> dict[str, Any]:
    events = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValidationError(f"failed to read environment NDJSON {path}: {error}") from error
    for line_number, line in enumerate(lines, 1):
        require(bool(line.strip()), f"environment NDJSON line {line_number} is empty")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValidationError(
                f"environment NDJSON line {line_number} is invalid: {error}"
            ) from error
        require(isinstance(value, dict), "environment NDJSON event must be an object")
        events.append(value)
    result = {
        "schema_version": 1,
        "evidence_type": "task018_process_environment",
        "system_modification": False,
        "new_runtime_dependencies": False,
        "events": events,
    }
    validate_process_environment(result)
    return result


def command_check_contract(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    contract = load_json(args.contract)
    order = load_json(args.execution_order)
    validate_contract(
        config,
        contract,
        order,
        sha256_file(args.config),
        sha256_file(args.execution_order),
    )
    history = contract.get("historical_task017", {})
    for name in ("raw_samples", "summary", "validation"):
        item = history.get(name, {})
        path = ROOT / item.get("path", "")
        require(path.is_file(), f"Task 017 {name} evidence is missing")
        require(sha256_file(path) == item.get("sha256"), f"Task 017 {name} changed")
    task017_summary = load_json(TASK017_SUMMARY)
    require(task017_summary.get("benchmark_status") == "PASS", "Task 017 is not PASS")
    print("task018_contract=PASS")
    print(f"experiment_config_sha256={sha256_file(args.config)}")
    print(f"execution_order_sha256={sha256_file(args.execution_order)}")
    print("formal_data_collected=false")
    return 0


def command_assemble_environment(args: argparse.Namespace) -> int:
    result = assemble_process_environment(args.ndjson)
    write_json(args.output, result)
    print("task018_process_environment=PASS")
    print(f"environment_events={len(result['events'])}")
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    config = load_json(args.config)
    contract = load_json(args.contract)
    order = load_json(args.execution_order)
    config_sha = sha256_file(args.config)
    validate_contract(
        config,
        contract,
        order,
        config_sha,
        sha256_file(args.execution_order),
    )
    review = human_review_record(
        approve_candidate=args.approve_candidate,
        source=args.human_review_source,
        recorded_at=args.human_review_recorded_at,
    )
    threads1, threads2, comparison, validation = validate_and_summarize(
        threads1_raw=load_json(args.threads1_raw),
        threads2_raw=load_json(args.threads2_raw),
        process_environment=load_json(args.process_environment),
        config=config,
        config_sha=config_sha,
        review=review,
    )
    write_json(args.threads1_summary, threads1)
    write_json(args.threads2_summary, threads2)
    comparison["source_sha256"] = {
        "threads1_raw": sha256_file(args.threads1_raw),
        "threads2_raw": sha256_file(args.threads2_raw),
        "process_environment": sha256_file(args.process_environment),
        "threads1_summary": sha256_file(args.threads1_summary),
        "threads2_summary": sha256_file(args.threads2_summary),
        "experiment_config": config_sha,
    }
    write_json(args.comparison_summary, comparison)
    validation["source_sha256"] = {
        "comparison_summary": sha256_file(args.comparison_summary),
        **comparison["source_sha256"],
    }
    write_json(args.validation, validation)
    print(f"task018_validation={validation['status']}")
    print(f"classification={validation['classification']}")
    print("threads1_samples=100")
    print("threads2_samples=100")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-contract", help="validate frozen protocol only")
    check.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    check.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    check.add_argument("--execution-order", type=Path, default=DEFAULT_ORDER)
    check.set_defaults(handler=command_check_contract)
    assemble = subparsers.add_parser(
        "assemble-environment",
        help="convert ordered board NDJSON events into validated JSON",
    )
    assemble.add_argument("--ndjson", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.set_defaults(handler=command_assemble_environment)
    summarize = subparsers.add_parser("summarize", help="validate real paired evidence")
    summarize.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    summarize.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    summarize.add_argument("--execution-order", type=Path, default=DEFAULT_ORDER)
    summarize.add_argument("--threads1-raw", type=Path, required=True)
    summarize.add_argument("--threads2-raw", type=Path, required=True)
    summarize.add_argument("--process-environment", type=Path, required=True)
    summarize.add_argument("--threads1-summary", type=Path, required=True)
    summarize.add_argument("--threads2-summary", type=Path, required=True)
    summarize.add_argument("--comparison-summary", type=Path, required=True)
    summarize.add_argument("--validation", type=Path, required=True)
    summarize.add_argument("--approve-candidate", action="store_true")
    summarize.add_argument("--human-review-source", choices=("user",))
    summarize.add_argument("--human-review-recorded-at")
    summarize.set_defaults(handler=command_summarize)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.handler(args))
    except (ValidationError, TASK017.ValidationError) as error:
        print(f"Task 018 validation error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
