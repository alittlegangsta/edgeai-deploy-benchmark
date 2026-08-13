#!/usr/bin/env python3
"""Parse and validate Task 034's switchable ncnn layer benchmark output."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

LAYER_RE = re.compile(
    r"^\s*(?P<type>\S+)\s+(?P<name>\S+)\s+(?P<ms>[0-9]+(?:\.[0-9]+)?)ms\s+\|"
)
SHAPE_RE = re.compile(r"\[(?P<body>[^\]]+)\]")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    raise ValueError(message)


def parse_shape(value: str | None) -> str | None:
    if value is None:
        return None
    match = SHAPE_RE.search(value)
    return match.group(0).replace(" ", "") if match else None


def parse_log(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ignored = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        match = LAYER_RE.match(line)
        if not match:
            ignored += 1
            continue
        left, _, right = line.partition("|")
        parts = left.split()
        if len(parts) < 3:
            fail(f"malformed layer line {line_number}: {line}")
        details = right.strip()
        shape_parts = details.split("kernel:", 1)[0].strip()
        input_shape: str | None = None
        output_shape: str | None = None
        if "->" in shape_parts:
            input_shape = parse_shape(shape_parts.split("->", 1)[0])
            output_shape = parse_shape(shape_parts.split("->", 1)[1])
        kernel = None
        stride = None
        kernel_match = re.search(r"kernel:\s*([^ ]+\s*x\s*[^ ]+)", details)
        stride_match = re.search(r"stride:\s*([^ ]+\s*x\s*[^ ]+)", details)
        if kernel_match:
            kernel = kernel_match.group(1).replace(" ", "")
        if stride_match:
            stride = stride_match.group(1).replace(" ", "")
        rows.append(
            {
                "type": match.group("type"),
                "name": match.group("name"),
                "latency_ms": float(match.group("ms")),
                "input_shape": input_shape,
                "output_shape": output_shape,
                "kernel": kernel,
                "stride": stride,
            }
        )
    if not rows:
        fail(f"no ncnn benchmark lines found in {path}")
    first_key = (rows[0]["type"], rows[0]["name"])
    runs: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for row in rows:
        if current and (row["type"], row["name"]) == first_key:
            runs.append(current)
            current = []
        current.append(row)
    if current:
        runs.append(current)
    if len(runs) < 2:
        fail(f"expected repeated runs, observed {len(runs)}")
    sequence = [(row["type"], row["name"]) for row in runs[0]]
    for index, run in enumerate(runs):
        if [(row["type"], row["name"]) for row in run] != sequence:
            fail(f"layer sequence differs in run {index}")
    layer_count = len(sequence)
    layer_stats: list[dict[str, Any]] = []
    for position, (layer_type, layer_name) in enumerate(sequence):
        samples = [run[position] for run in runs]
        mean_ms = statistics.fmean(item["latency_ms"] for item in samples)
        layer_stats.append(
            {
                "index": position,
                "type": layer_type,
                "name": layer_name,
                "mean_ms": mean_ms,
                "p50_ms": statistics.median(item["latency_ms"] for item in samples),
                "min_ms": min(item["latency_ms"] for item in samples),
                "max_ms": max(item["latency_ms"] for item in samples),
                "input_shape": samples[0]["input_shape"],
                "output_shape": samples[0]["output_shape"],
                "kernel": samples[0]["kernel"],
                "stride": samples[0]["stride"],
            }
        )
    total_ms = statistics.fmean(sum(row["latency_ms"] for row in run) for run in runs)
    for row in layer_stats:
        row["cumulative_percent"] = 100.0 * sum(
            item["mean_ms"] for item in layer_stats[: row["index"] + 1]
        ) / total_ms
        row["share_percent"] = 100.0 * row["mean_ms"] / total_ms
    aggregates: dict[str, list[float]] = defaultdict(list)
    for row in layer_stats:
        aggregates[row["type"]].append(row["mean_ms"])
    aggregate_rows = [
        {
            "type": layer_type,
            "layer_count": len(values),
            "mean_total_ms": sum(values),
            "share_percent": 100.0 * sum(values) / total_ms,
        }
        for layer_type, values in aggregates.items()
    ]
    aggregate_rows.sort(key=lambda row: row["mean_total_ms"], reverse=True)
    top = sorted(layer_stats, key=lambda row: row["mean_ms"], reverse=True)[:10]
    return {
        "schema_version": 1,
        "task": "034",
        "instrumentation": {
            "facility": "ncnn NCNN_BENCHMARK",
            "enabled_for_this_run": True,
            "production_default": False,
            "semantics_changed": False,
        },
        "source_log": str(path),
        "run_count": len(runs),
        "layer_count": layer_count,
        "ignored_non_layer_lines": ignored,
        "total_layer_time_mean_ms": total_ms,
        "operator_aggregates": aggregate_rows,
        "top_10_hottest_layers": top,
        "layers": layer_stats,
    }


def validate_run(path: Path, label: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "PASS_TARGET":
        fail(f"{label}: status is not PASS_TARGET")
    runtime = data.get("runtime", {})
    identity = data.get("identity", {})
    if identity.get("ncnn_version") != "1.0.20240410":
        fail(f"{label}: ncnn version differs")
    if runtime.get("effective_parallel_backend") != "openmp":
        fail(f"{label}: OpenMP backend is not reported")
    experiment = data.get("experiment", {})
    if experiment.get("threads") != 2 or experiment.get("packing_layout") is not True:
        fail(f"{label}: frozen runtime controls differ")
    if any(experiment.get(key) for key in ("fp16_packed", "fp16_storage", "fp16_arithmetic")):
        fail(f"{label}: FP16 option was enabled")
    correctness = data.get("correctness", {})
    if correctness.get("status") != "PASS_TARGET":
        fail(f"{label}: correctness is not PASS_TARGET")
    for digest in (
        identity.get("param_sha256"),
        identity.get("bin_sha256"),
        identity.get("input_sha256"),
    ):
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            fail(f"{label}: missing identity SHA256")
    return data


def summarize_candidate(path: Path, label: str) -> dict[str, Any]:
    data = validate_run(path, label)
    stage = data["summary"]["stages"]
    samples = data.get("samples", [])
    cpu_values = [item.get("cpu_percent_one_core_basis") for item in samples]
    user_values = [item.get("user_cpu_seconds") for item in samples]
    system_values = [item.get("system_cpu_seconds") for item in samples]
    rss_values = [item.get("peak_rss_kib") for item in samples]
    return {
        "label": label,
        "path": str(path),
        "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
        "status": data["status"],
        "correctness": data["correctness"],
        "runtime": data["runtime"],
        "experiment": data["experiment"],
        "summary": {
            name: {
                "mean_ms": values["mean_ms"],
                "p50_ms": values["p50_ms"],
                "p95_ms": values["p95_ms"],
                "fps": values["fps"],
            }
            for name, values in stage.items()
        },
        "resources": {
            "peak_rss_kib_max": max(rss_values) if rss_values else None,
            "peak_rss_kib_samples": rss_values,
            "cpu_percent_one_core_basis_mean": statistics.fmean(cpu_values) if all(isinstance(v, (int, float)) for v in cpu_values) else None,
            "user_cpu_seconds_mean": statistics.fmean(user_values) if all(isinstance(v, (int, float)) for v in user_values) else None,
            "system_cpu_seconds_mean": statistics.fmean(system_values) if all(isinstance(v, (int, float)) for v in system_values) else None,
            "cpu_frequency_khz": sorted({item.get("cpu_frequency_khz") for item in samples}, key=str),
            "temperature_millicelsius": sorted({item.get("temperature_millicelsius") for item in samples}, key=str),
            "threads_before": sorted({item.get("threads_before") for item in samples}, key=str),
            "threads_after": sorted({item.get("threads_after") for item in samples}, key=str),
        },
    }


def self_test() -> None:
    sample = "Convolution conv_0 1.00ms    | [ 1, 2 *4] -> [ 3, 4 *4] kernel: 3 x 3     stride: 1 x 1\n"
    sample += "Swish silu_0 0.50ms    |\n"
    sample += sample
    path = Path("/tmp/task034-layer-parser-self-test.log")
    path.write_text(sample, encoding="utf-8")
    parsed = parse_log(path)
    assert parsed["run_count"] == 2
    assert parsed["layer_count"] == 2
    assert parsed["top_10_hottest_layers"][0]["type"] == "Convolution"
    path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--layer-log", type=Path)
    parser.add_argument("--layer-run-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate-a", type=Path)
    parser.add_argument("--candidate-b", type=Path)
    parser.add_argument("--candidate-output", type=Path)
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"status": "PASS", "task": "034", "test": "layer_parser"}))
            return 0
        if not args.layer_log or not args.layer_run_json or not args.output:
            parser.error("--layer-log, --layer-run-json and --output are required")
        profile = parse_log(args.layer_log)
        run = validate_run(args.layer_run_json, "layer profile")
        profile["run_json"] = {
            "path": str(args.layer_run_json),
            "sha256": __import__("hashlib").sha256(args.layer_run_json.read_bytes()).hexdigest(),
            "status": run["status"],
            "correctness": run["correctness"],
            "summary": run["summary"],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.candidate_a and args.candidate_b and args.candidate_output:
            matrix = {
                "schema_version": 1,
                "task": "034",
                "candidate_a": summarize_candidate(args.candidate_a, "A"),
                "candidate_b": summarize_candidate(args.candidate_b, "B"),
                "comparison": {},
            }
            a = matrix["candidate_a"]["summary"]
            b = matrix["candidate_b"]["summary"]
            for stage in ("pipeline", "inference"):
                matrix["comparison"][stage] = {
                    "a_mean_ms": a[stage]["mean_ms"],
                    "b_mean_ms": b[stage]["mean_ms"],
                    "b_over_a": b[stage]["mean_ms"] / a[stage]["mean_ms"],
                    "b_delta_percent": 100.0 * (b[stage]["mean_ms"] / a[stage]["mean_ms"] - 1.0),
                    "accepted": b[stage]["mean_ms"] < a[stage]["mean_ms"],
                }
            args.candidate_output.parent.mkdir(parents=True, exist_ok=True)
            args.candidate_output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "task": "034", "layer_count": profile["layer_count"], "run_count": profile["run_count"]}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        print(json.dumps({"status": "FAIL", "task": "034", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
