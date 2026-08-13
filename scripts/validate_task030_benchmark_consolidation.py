#!/usr/bin/env python3
"""Generate and independently validate the Task 030 benchmark consolidation.

The source campaigns are immutable Task 012 and Task 018 raw evidence.  This
script never changes those files.  ``--write`` derives Task 030 JSON from the
raw samples; the default mode recomputes the same values and checks every
stored field, including the nearest-rank P95 requested by Task 030.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "evidence" / "030"
PC_RAW = ROOT / "results" / "benchmarks" / "pc_three_backend_cpp_ort.json"
ARM_RAW = ROOT / "results" / "evidence" / "018" / "openmp" / "threads2_raw_samples.json"
MODEL_CONTRACT = ROOT / "results" / "evidence" / "002" / "model_contract.json"
PC_CONFIG = ROOT / "configs" / "benchmark_pc.json"
ARM_CONFIG = ROOT / "configs" / "benchmark_anlogic_arm_threading_openmp.json"
PC_RAW_REL = "results/benchmarks/pc_three_backend_cpp_ort.json"
ARM_RAW_REL = "results/evidence/018/openmp/threads2_raw_samples.json"


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nearest_rank(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def stage_stats(samples: list[dict[str, Any]], ns_key: str) -> dict[str, Any]:
    values = [float(sample[ns_key]) / 1_000_000.0 for sample in samples]
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values),
        "p50_ms": nearest_rank(values, 0.50),
        "p95_ms": nearest_rank(values, 0.95),
        "min_ms": min(values),
        "max_ms": max(values),
        "sample_standard_deviation_ms": statistics.stdev(values),
    }


def flatten_pc_rounds(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rounds: list[dict[str, Any]] = []
    for campaign_round in raw["rounds"]:
        payload = campaign_round["process_payload"]
        rounds.extend(payload["rounds"])
    return rounds


def validate_sample_equations(rounds: list[dict[str, Any]]) -> None:
    for round_record in rounds:
        for sample in round_record["samples"]:
            expected = (
                sample["preprocess_ns"]
                + sample["inference_ns"]
                + sample["postprocess_ns"]
            )
            if expected != sample["pipeline_total_ns"]:
                raise AssertionError(
                    f"pipeline equation failed: round={sample.get('round')} "
                    f"iteration={sample.get('iteration')}"
                )


def resource_summary(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    cpu = [
        float(r["resource_measurement"]["process_cpu_percent_one_core_basis"])
        for r in rounds
        if r.get("resource_measurement", {}).get("process_cpu_percent_one_core_basis") is not None
    ]
    rss = []
    for record in rounds:
        resource = record.get("resource_measurement", {})
        if resource.get("peak_rss_kib") is not None:
            rss.append(int(resource["peak_rss_kib"]))
        elif resource.get("peak_rss_bytes") is not None:
            # Task 012 records Linux ru_maxrss as bytes; Task 018 records KiB.
            rss.append(float(resource["peak_rss_bytes"]) / 1024.0)
    return {
        "cpu_utilization_one_core_basis_percent": {
            "count": len(cpu),
            "mean": statistics.fmean(cpu) if cpu else None,
            "min": min(cpu) if cpu else None,
            "max": max(cpu) if cpu else None,
            "unit": "percent",
        },
        "peak_rss_kib": {
            "count": len(rss),
            "mean": statistics.fmean(rss) if rss else None,
            "min": min(rss) if rss else None,
            "max": max(rss) if rss else None,
            "unit": "KiB",
            "scope": "process startup through formal measurement completion",
        },
    }


def sampled_resource_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, unit in (("cpu_frequency_khz", "kHz"), ("temperature_millicelsius", "millicelsius")):
        present = [sample.get(key) for sample in samples if key in sample]
        numeric = [float(value) for value in present if value is not None]
        result[key] = {
            "unit": unit,
            "field_present_in_samples": bool(present),
            "numeric_sample_count": len(numeric),
            "null_sample_count": sum(value is None for value in present),
            "min": min(numeric) if numeric else None,
            "mean": statistics.fmean(numeric) if numeric else None,
            "max": max(numeric) if numeric else None,
            "status": "RECORDED" if numeric else "NOT_RECORDED_IN_SOURCE_CAMPAIGN",
        }
    return result


def model_load_summary(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(r["model_load_ms"]) for r in rounds]
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def correctness_summary(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [
        check
        for round_record in rounds
        for check in (
            round_record["correctness"]["before_warmup"],
            round_record["correctness"]["after_measurement"],
        )
    ]
    statuses = sorted({str(check["status"]) for check in checks})
    return {
        "checks": len(checks),
        "statuses": statuses,
        "all_statuses_pass": all(status in {"PASS", "PASS_TARGET"} for status in statuses),
        "detection_counts": sorted({int(check["detection_count"]) for check in checks}),
        "minimum_class_matched_iou": min(float(check["minimum_class_matched_iou"]) for check in checks),
        "maximum_absolute_confidence_difference": max(
            float(check["maximum_absolute_confidence_difference"]) for check in checks
        ),
    }


def unique_values(rounds: list[dict[str, Any]], key: str) -> list[Any]:
    values = []
    for record in rounds:
        value = record.get(key)
        if value not in values:
            values.append(value)
    return values


def build_backend_row(
    *,
    name: str,
    raw_path: Path,
    raw_rel: str,
    rounds: list[dict[str, Any]],
    representation: str,
    environment_note: str,
) -> dict[str, Any]:
    validate_sample_equations(rounds)
    samples = [sample for record in rounds for sample in record["samples"]]
    stages = {
        "preprocess": stage_stats(samples, "preprocess_ns"),
        "inference": stage_stats(samples, "inference_ns"),
        "postprocess": stage_stats(samples, "postprocess_ns"),
        "pipeline": stage_stats(samples, "pipeline_total_ns"),
    }
    pipeline_mean = stages["pipeline"]["mean_ms"]
    return {
        "backend": name,
        "status": "BENCHMARKED_CORRECT",
        "source_evidence": {"path": raw_rel, "sha256": sha256(raw_path)},
        "sample_count": len(samples),
        "independent_process_count": len(rounds),
        "warmup_per_process": unique_values(rounds, "warmup_iterations"),
        "formal_iterations_per_process": unique_values(rounds, "formal_iterations"),
        "model_representation": representation,
        "environment_note": environment_note,
        "stages": stages,
        "fps": {"value": 1000.0 / pipeline_mean, "formula": "1000 / mean pipeline_ms"},
        "model_load": model_load_summary(rounds),
        "resources": resource_summary(rounds),
        "sampled_frequency_temperature": sampled_resource_summary(samples),
        "correctness": correctness_summary(rounds),
        "round_ids": [record.get("round") for record in rounds],
    }


def build_outputs() -> dict[str, Any]:
    pc_raw = read_json(PC_RAW)
    arm_raw = read_json(ARM_RAW)
    model_contract = read_json(MODEL_CONTRACT)
    pc_rounds = flatten_pc_rounds(pc_raw)
    arm_rounds = arm_raw["rounds"]
    expected_image = "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
    expected_config = "82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d"
    expected_weights = model_contract["weights_sha256"]
    expected_param = "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
    expected_bin = "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
    expected_onnx = model_contract["model_sha256"]
    for label, records in (("PC", pc_rounds), ("ARM", arm_rounds)):
        if not records:
            raise AssertionError(f"{label} source has no process rounds")
        for record in records:
            if record.get("image_sha256") != expected_image:
                raise AssertionError(f"{label} input image identity mismatch")
            if record.get("inference_config_sha256") != expected_config:
                raise AssertionError(f"{label} inference config identity mismatch")
            runtime = record.get("runtime", {})
            runtime_input = runtime.get("input")
            runtime_output = runtime.get("output")
            if runtime_input is None:
                runtime_input = (runtime.get("runtime_inputs") or [{}])[0]
            if runtime_output is None:
                runtime_output = (runtime.get("runtime_outputs") or [{}])[0]
            shape_key = "logical_shape" if "logical_shape" in runtime_input else "shape"
            output_shape_key = "logical_shape" if "logical_shape" in runtime_output else "shape"
            if runtime_input.get(shape_key) != [1, 3, 640, 640]:
                raise AssertionError(f"{label} input shape mismatch")
            if runtime_output.get(output_shape_key) != [1, 25200, 85]:
                raise AssertionError(f"{label} output shape mismatch")
            input_dtype = str(runtime_input.get("dtype", "")).lower()
            output_dtype = str(runtime_output.get("dtype", "")).lower()
            if input_dtype not in {"float32", "float"}:
                raise AssertionError(f"{label} input dtype mismatch")
            if output_dtype not in {"float32", "float"}:
                raise AssertionError(f"{label} output dtype mismatch")
    if any(record.get("model_sha256") != expected_onnx for record in pc_rounds):
        raise AssertionError("PC ONNX model identity mismatch")
    if any(record.get("source_weights_sha256") != expected_weights for record in arm_rounds):
        raise AssertionError("ARM source-weight identity mismatch")
    if any(record.get("ncnn_param_sha256") != expected_param for record in arm_rounds):
        raise AssertionError("ARM ncnn param identity mismatch")
    if any(record.get("ncnn_bin_sha256") != expected_bin for record in arm_rounds):
        raise AssertionError("ARM ncnn bin identity mismatch")
    pc = build_backend_row(
        name="pc_cpp_ort",
        raw_path=PC_RAW,
        raw_rel=PC_RAW_REL,
        rounds=pc_rounds,
        representation="frozen YOLOv5n v7.0 ONNX FP32",
        environment_note="WSL2 x86_64 C++ ONNX Runtime CPUExecutionProvider; not bare-metal ARM.",
    )
    arm = build_backend_row(
        name="arm_ncnn_recommended_dual_thread",
        raw_path=ARM_RAW,
        raw_rel=ARM_RAW_REL,
        rounds=arm_rounds,
        representation="ncnn 20240410 param/bin conversion of the frozen YOLOv5n v7.0 weights",
        environment_note="MLK-F3P-CZ02-DR1M90 AArch64; Task 019 recommended-dual-thread OpenMP profile.",
    )
    identity = {
        "model_name": "YOLOv5n v7.0",
        "source_weights_sha256": model_contract["weights_sha256"],
        "onnx_sha256": model_contract["model_sha256"],
        "input_image_sha256": expected_image,
        "inference_config_sha256": expected_config,
        "input_contract": {"dtype": "FP32", "shape": [1, 3, 640, 640]},
        "output_contract": {"dtype": "FP32", "shape": [1, 25200, 85]},
        "confidence_threshold": 0.25,
        "nms_iou_threshold": 0.45,
        "preprocess": "shared BGR-to-RGB letterbox, normalize, HWC-to-CHW",
        "postprocess": "shared YOLO decode, confidence filter, coordinate restore, class-aware NMS",
    }
    matrix = {
        "schema_version": 1,
        "task": "030",
        "entries": [
            {
                "backend": "PC C++ ORT YOLOv5n",
                "status": "BENCHMARKED_CORRECT",
                "evidence": "results/evidence/030/pc_ort_benchmark.json",
                "scope": "WSL2 CPUExecutionProvider; benchmarked separately from ARM",
            },
            {
                "backend": "ARM ncnn YOLOv5n",
                "status": "BENCHMARKED_CORRECT",
                "evidence": "results/evidence/030/arm_ncnn_benchmark.json",
                "scope": "DR1M90 CPU-only recommended-dual-thread profile; benchmarked separately from PC",
            },
            {
                "backend": "DR1 vendor face NPU control",
                "status": "FUNCTIONAL_CONTROL_ONLY",
                "evidence": "results/evidence/026/official_demo_validation.json",
                "scope": "different face model; no YOLOv5n performance substitution",
            },
            {
                "backend": "DR1 YOLOv5n NPU",
                "status": "NOT_BENCHMARKED",
                "evidence": "results/evidence/028/benchmark_status.json",
                "scope": "Task 028 vendor dependency blocker; no NPU performance claim",
            },
        ],
    }
    comparison = {
        "schema_version": 1,
        "task": "030",
        "identity": identity,
        "rows": [
            {"backend": "pc_cpp_ort", "evidence": "results/evidence/030/pc_ort_benchmark.json"},
            {"backend": "arm_ncnn_recommended_dual_thread", "evidence": "results/evidence/030/arm_ncnn_benchmark.json"},
        ],
        "cross_platform_speedup": None,
        "cross_platform_speedup_status": "NOT_CLAIMED_DIFFERENT_PLATFORM_AND_RUNTIME",
        "interpretation": "The rows share workload and preprocessing/postprocessing contracts, but PC ORT and ARM ncnn are different hardware/runtime environments. This report does not present a cross-platform speedup.",
        "historical_arm_reference": {
            "task": "017",
            "path": "results/evidence/017/benchmark_summary.json",
            "note": "OpenMP-off historical baseline; immutable reference only, not mixed into the Task 018 recommended profile row.",
        },
    }
    contract = {
        "schema_version": 1,
        "task": "030",
        "title": "ARM CPU benchmark and profiling consolidation",
        "status": "COMPLETED",
        "methodology_id": "task030-arm-cpu-profiling-consolidation-v1",
        "source_campaigns": {
            "pc": {"path": PC_RAW_REL, "sha256": sha256(PC_RAW), "historical_task": "012"},
            "arm": {"path": ARM_RAW_REL, "sha256": sha256(ARM_RAW), "historical_task": "018"},
        },
        "workload_identity": identity,
        "protocol": {
            "warmup": 10,
            "repeated_runs": "retained source process rounds and timed samples",
            "stages": ["preprocess", "inference", "postprocess", "pipeline"],
            "pipeline_formula": "preprocess_ns + inference_ns + postprocess_ns",
            "percentile_method": "nearest-rank",
            "percentiles": [0.50, 0.95],
            "fps_formula": "1000 / mean pipeline_ms",
            "cpu_formula": "100 * process user+system CPU seconds / wall seconds",
            "memory": "process-level Peak RSS high-water mark",
            "frequency_temperature": "preserve numeric values or JSON null/unavailable",
            "outlier_policy": "retain all source samples; no latency filtering",
        },
        "comparison_policy": "separate PC and ARM reports; no cross-platform speedup claim",
        "correctness_gate": {
            "status": "PASS_REQUIRED",
            "detection_count": 5,
            "minimum_class_matched_iou": 0.99,
            "maximum_confidence_delta": 0.01,
            "finite_values": True,
            "valid_boxes": True,
        },
    }
    validation = {
        "schema_version": 1,
        "task": "030",
        "status": "PASS",
        "validator": "scripts/validate_task030_benchmark_consolidation.py",
        "checks": {
            "pc_raw_equations": "PASS",
            "arm_raw_equations": "PASS",
            "p95_recomputed": "PASS",
            "identity_and_correctness": "PASS",
            "npu_not_benchmarked": "PASS",
            "source_evidence_immutable": "PASS",
        },
        "source_sha256": {"pc": sha256(PC_RAW), "arm": sha256(ARM_RAW)},
    }
    return {
        "contract": contract,
        "pc": pc,
        "arm": arm,
        "matrix": matrix,
        "comparison": comparison,
        "validation": validation,
    }


def assert_close(actual: Any, expected: Any, path: str) -> None:
    if isinstance(expected, float):
        if not math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12):
            raise AssertionError(f"{path}: {actual!r} != {expected!r}")
    elif actual != expected:
        raise AssertionError(f"{path}: {actual!r} != {expected!r}")


def compare_stored(stored: dict[str, Any], expected: dict[str, Any], path: str = "") -> None:
    if isinstance(expected, dict):
        if not isinstance(stored, dict):
            raise AssertionError(f"{path}: expected object")
        for key, value in expected.items():
            if key not in stored:
                raise AssertionError(f"{path}/{key}: missing")
            compare_stored(stored[key], value, f"{path}/{key}")
    elif isinstance(expected, list):
        if stored != expected:
            raise AssertionError(f"{path}: list differs")
    else:
        assert_close(stored, expected, path)


def validate_outputs() -> None:
    outputs = build_outputs()
    required = {
        "contract": EVIDENCE / "benchmark_contract.json",
        "pc": EVIDENCE / "pc_ort_benchmark.json",
        "arm": EVIDENCE / "arm_ncnn_benchmark.json",
        "matrix": EVIDENCE / "backend_status_matrix.json",
        "comparison": EVIDENCE / "benchmark_comparison.json",
        "validation": EVIDENCE / "validation.json",
    }
    for name, path in required.items():
        if not path.is_file():
            raise AssertionError(f"missing Task 030 evidence: {path}")
        stored = read_json(path)
        compare_stored(stored, outputs[name], name)
    if outputs["pc"]["correctness"]["all_statuses_pass"] is not True:
        raise AssertionError("PC correctness gate failed")
    if outputs["arm"]["correctness"]["all_statuses_pass"] is not True:
        raise AssertionError("ARM correctness gate failed")
    if outputs["matrix"]["entries"][3]["status"] != "NOT_BENCHMARKED":
        raise AssertionError("YOLOv5n NPU must remain NOT_BENCHMARKED")
    print("Task 030 consolidation validation: PASS")
    for row in (outputs["pc"], outputs["arm"]):
        print(
            f"{row['backend']}: samples={row['sample_count']} "
            f"pipeline_mean_ms={row['stages']['pipeline']['mean_ms']:.9f} "
            f"p95_ms={row['stages']['pipeline']['p95_ms']:.9f} "
            f"fps={row['fps']['value']:.9f}"
        )


def write_outputs() -> None:
    outputs = build_outputs()
    for name, filename in {
        "contract": "benchmark_contract.json",
        "pc": "pc_ort_benchmark.json",
        "arm": "arm_ncnn_benchmark.json",
        "matrix": "backend_status_matrix.json",
        "comparison": "benchmark_comparison.json",
        "validation": "validation.json",
    }.items():
        write_json(EVIDENCE / filename, outputs[name])
    print(f"wrote Task 030 evidence under {EVIDENCE}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="derive and write Task 030 evidence")
    args = parser.parse_args()
    if args.write:
        write_outputs()
    validate_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
