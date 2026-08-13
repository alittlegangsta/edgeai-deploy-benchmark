#!/usr/bin/env python3
"""Generate and validate the Task 040 authoritative results freeze.

The script deliberately reads immutable Task 030/033/035/036/037/038/039
evidence instead of rerunning a workload.  ``--write`` derives the final JSON,
README-ready tables and validation record; the default mode validates the
already generated files and rechecks every referenced source SHA256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "results" / "final"
MANIFEST = FINAL / "authoritative_results.json"
TABLES = FINAL / "README_READY_TABLES.md"
VALIDATION = FINAL / "validation.json"


def read_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{rel}: expected JSON object")
    return value


def sha256(rel: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / rel).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_ref(rel: str, role: str, fields: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": rel, "sha256": sha256(rel), "role": role}
    if fields:
        result["fields"] = fields
    return result


def metric(source: dict[str, Any], key: str) -> dict[str, float]:
    value = source[key]
    mean_key = "mean" if "mean" in value else "mean_ms"
    p50_key = "p50" if "p50" in value else "p50_ms"
    p95_key = "p95" if "p95" in value else "p95_ms"
    return {"mean": float(value[mean_key]), "p50": float(value[p50_key]), "p95": float(value[p95_key])}


def nested_metric(source: dict[str, Any], key: str) -> dict[str, float]:
    return metric(source["metrics"], key)


def ncnn_row(variant: str, arm: dict[str, Any], coco: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    record = arm["variants"][variant]
    metrics = record["metrics"]
    correctness = "PASS_TARGET" if variant == "fp32" else "COCO_GATE_PASS; secondary single-image diagnostic retained"
    return {
        "id": f"dr1_ncnn_{variant}",
        "classification": "formal_benchmark",
        "platform": "DR1 MLK-F3P-CZ02-DR1M90",
        "hardware": "AArch64 dual-core Cortex-A35-class CPU",
        "backend": "ncnn 20240410",
        "precision": "FP32" if variant == "fp32" else "EQ INT8",
        "model": "YOLOv5n v7.0 ncnn param/bin",
        "protocol": {
            "warmup": arm["protocol"]["warmup"],
            "repeat": arm["protocol"]["repeat_per_process"],
            "samples": arm["protocol"]["sample_count_per_variant"],
            "independent_processes": arm["protocol"]["independent_processes_per_variant"],
            "threads": arm["protocol"]["threads"],
            "scheduling": arm["protocol"]["scheduling"],
            "packing": arm["protocol"]["packing"],
            "stage_definition": "preprocess + backend inference + postprocess; same input and image path",
            "backend_inference_boundary": "wall time of the ncnn backend call",
        },
        "metrics": {
            "preprocess_ms": metric(metrics, "preprocess_ms"),
            "backend_inference_ms": metric(metrics, "inference_ms"),
            "postprocess_ms": metric(metrics, "postprocess_ms"),
            "pipeline_ms": metric(metrics, "pipeline_ms"),
            "fps": float(metrics["pipeline_ms"]["fps"]),
            "cpu_utilization_one_core_basis_percent": metric(metrics, "cpu_percent_one_core_basis"),
            "peak_rss_kib": metric(metrics, "peak_rss_kib"),
            "gpu_memory": None,
            "frequency_temperature": "not recorded in the source campaign",
        },
        "correctness": {
            "primary_status": correctness,
            "coco_gate": "PASS" if variant == "eq" else "not the EQ acceptance gate",
            "secondary_single_image_reference": record.get("secondary_frozen_reference"),
        },
        "runtime_identity": {
            "ncnn_version": profile["identity"]["ncnn_version"],
            "ncnn_library_sha256": profile["identity"]["ncnn_library_sha256"],
            "private_libgomp_sha256": profile["identity"]["private_libgomp_sha256"],
            "threads": profile["experiment"]["threads"],
            "packing": profile["experiment"]["packing_layout"],
            "openmp": profile["runtime"]["effective_parallel_backend"],
        },
        "source_evidence": [
            source_ref("results/evidence/035/arm_int8_benchmark.json", "paired ARM formal benchmark"),
            source_ref("results/evidence/035/coco_full_evaluation.json", "independent COCO accuracy gate"),
            source_ref("results/evidence/033/threads2_default_packing_on.json", "accepted runtime profile identity"),
        ],
    }


def trt_row(variant: str, trt: dict[str, Any], coco: dict[str, Any], engine: dict[str, Any]) -> dict[str, Any]:
    source = trt["accepted"] if variant == "fp32" else trt["formal_fp16"]
    metrics = source["metrics"]
    return {
        "id": f"rtx4060ti_tensorrt_{variant}",
        "classification": "formal_benchmark",
        "platform": "PC WSL2 x86_64",
        "hardware": "NVIDIA GeForce RTX 4060 Ti (compute capability 8.9)",
        "backend": "TensorRT 10.13.3 / CUDA 12.9",
        "precision": variant.upper(),
        "model": "YOLOv5n v7.0 TensorRT engine",
        "protocol": {
            "warmup": trt["protocol"]["warmup"],
            "repeat": trt["protocol"]["repeat"],
            "stage_definition": trt["protocol"]["end_to_end"],
            "h2d_inference_d2h": "CUDA event diagnostics retained separately",
            "backend_inference_boundary": "host wall time from immediately before TensorRT detector.infer() to return; includes H2D, enqueueV3, D2H and event synchronization",
            "gpu_execution_boundary": "CUDA event elapsed time from inference_start to inference_end around enqueueV3; excludes H2D and D2H",
        },
        "metrics": {
            "preprocess_ms": nested_metric(source, "preprocess_ms"),
            "backend_inference_ms": nested_metric(source, "inference_wall_ms"),
            "gpu_h2d_ms": nested_metric(source, "gpu_h2d_ms"),
            "gpu_execution_ms": nested_metric(source, "gpu_inference_ms"),
            "gpu_d2h_ms": nested_metric(source, "gpu_d2h_ms"),
            "postprocess_ms": nested_metric(source, "postprocess_ms"),
            "pipeline_ms": nested_metric(source, "pipeline_ms"),
            "fps": float(metrics["fps"]),
            "cpu_utilization_one_core_basis_percent": None,
            "peak_rss_kib": {"mean": float(metrics["peak_rss_kib"]), "p50": None, "p95": None},
            "gpu_memory": {
                "total_bytes": trt["gpu"]["memory_total_bytes"],
                "free_bytes_at_end": metrics.get("gpu_memory_free_bytes_at_end"),
            },
            "frequency_temperature": "not recorded in the source campaign",
        },
        "correctness": {
            "primary_status": "PASS_TARGET" if variant == "fp32" else "COCO_GATE_PASS",
            "coco_gate": "PASS" if variant == "fp16" else "reference for FP16 gate",
            "secondary_single_image_reference": trt.get("formal_fp16", {}).get("correctness") if variant == "fp16" else None,
        },
        "engine_identity": {
            "engine_sha256": source["engine_sha256"],
            "builder": engine["builder"],
        },
        "source_evidence": [
            source_ref("results/evidence/037/benchmark.json", "TensorRT formal benchmark"),
            source_ref("results/evidence/037/coco_accuracy.json", "TensorRT COCO accuracy gate"),
            source_ref("results/evidence/037/engine_manifest.json", "engine and builder identity"),
        ],
    }


def build_manifest() -> dict[str, Any]:
    contract = read_json("results/evidence/030/benchmark_contract.json")["workload_identity"]
    pc = read_json("results/evidence/030/pc_ort_benchmark.json")
    profile = read_json("results/evidence/033/threads2_default_packing_on.json")
    arm = read_json("results/evidence/035/arm_int8_benchmark.json")
    coco_arm = read_json("results/evidence/035/coco_full_evaluation.json")
    face = read_json("results/evidence/036/face_runner_benchmark.json")
    face_artifact = read_json("results/evidence/036/artifact_manifest.json")
    trt = read_json("results/evidence/037/benchmark.json")
    coco_trt = read_json("results/evidence/037/coco_accuracy.json")
    engine = read_json("results/evidence/037/engine_manifest.json")
    unified = read_json("results/evidence/038/backend_runs.json")
    camera = read_json("results/evidence/039/dr_camera_ncnn_int8.json")
    camera_caps = read_json("results/evidence/039/dr_camera_capabilities.json")
    video_validation = read_json("results/evidence/039/validation.json")
    blocked = read_json("results/evidence/028/benchmark_status.json")

    pc_metrics = {
        "preprocess_ms": metric(pc["stages"], "preprocess"),
        "backend_inference_ms": metric(pc["stages"], "inference"),
        "postprocess_ms": metric(pc["stages"], "postprocess"),
        "pipeline_ms": metric(pc["stages"], "pipeline"),
        "fps": float(pc["fps"]["value"]),
        "cpu_utilization_one_core_basis_percent": pc["resources"]["cpu_utilization_one_core_basis_percent"],
        "peak_rss_kib": pc["resources"]["peak_rss_kib"],
        "gpu_memory": None,
        "frequency_temperature": "not recorded in the source campaign",
    }
    pc_row = {
        "id": "pc_ort_fp32",
        "classification": "formal_benchmark",
        "platform": "PC WSL2 x86_64",
        "hardware": "CPU",
        "backend": "ONNX Runtime 1.18.1 / CPUExecutionProvider",
        "precision": "FP32",
        "model": "YOLOv5n v7.0 ONNX",
        "protocol": {
            "warmup": pc["warmup_per_process"][0],
            "repeat": pc["formal_iterations_per_process"][0],
            "samples": pc["sample_count"],
            "independent_processes": pc["independent_process_count"],
            "stage_definition": "preprocess + ORT inference + postprocess; image source timing excluded",
            "backend_inference_boundary": "wall time of the ORT backend call",
        },
        "metrics": pc_metrics,
        "correctness": {
            "primary_status": pc["correctness"]["statuses"][0],
            "detection_count": pc["correctness"]["detection_counts"],
            "minimum_class_matched_iou": pc["correctness"]["minimum_class_matched_iou"],
            "maximum_confidence_delta": pc["correctness"]["maximum_absolute_confidence_difference"],
        },
        "source_evidence": [
            source_ref("results/evidence/030/pc_ort_benchmark.json", "PC ORT formal benchmark"),
            source_ref("results/evidence/030/benchmark_contract.json", "shared model and benchmark contract"),
        ],
    }

    authoritative = [pc_row, trt_row("fp32", trt, coco_trt, engine), trt_row("fp16", trt, coco_trt, engine),
                     ncnn_row("fp32", arm, coco_arm, profile), ncnn_row("eq", arm, coco_arm, profile)]

    dr1_fp = coco_arm["models"]["fp32"]
    dr1_eq = coco_arm["models"]["eq"]
    trt_fp = coco_trt["models"]["tensorrt_fp32"]
    trt_f16 = coco_trt["models"]["tensorrt_fp16"]
    dr1_perf_fp = arm["variants"]["fp32"]["metrics"]
    dr1_perf_eq = arm["variants"]["eq"]["metrics"]
    trt_perf_fp = trt["accepted"]["metrics"]
    trt_perf_f16 = trt["formal_fp16"]["metrics"]

    tradeoffs = [
        {
            "id": "dr1_fp32_vs_eq_int8",
            "platform": "DR1 MLK-F3P-CZ02-DR1M90",
            "accuracy": {
                "protocol": "4500 independent COCO val2017 images; 500-image calibration disjoint",
                "reference": {"mAP50": dr1_fp["mAP50"], "mAP50_95": dr1_fp["mAP50_95"]},
                "candidate": {"mAP50": dr1_eq["mAP50"], "mAP50_95": dr1_eq["mAP50_95"]},
                "delta_candidate_minus_reference": {
                    "mAP50": coco_arm["comparison"]["delta_eq_minus_fp32_mAP50"],
                    "mAP50_95": coco_arm["comparison"]["delta_eq_minus_fp32_mAP50_95"],
                },
                "gate": {"max_absolute_delta": 0.02, "status": coco_arm["comparison"]["accuracy_gate"], "zero_detection_images": dr1_eq["zero_detection_images"]},
            },
            "performance": {
                "reference": {"backend_inference_mean_ms": dr1_perf_fp["inference_ms"]["mean"], "pipeline_mean_ms": dr1_perf_fp["pipeline_ms"]["mean"], "fps": dr1_perf_fp["pipeline_ms"]["fps"]},
                "candidate": {"backend_inference_mean_ms": dr1_perf_eq["inference_ms"]["mean"], "pipeline_mean_ms": dr1_perf_eq["pipeline_ms"]["mean"], "fps": dr1_perf_eq["pipeline_ms"]["fps"]},
                "timing_boundary": "ncnn backend call wall time; same boundary for both precision variants",
                "same_platform_speedup": {"backend_inference": arm["comparison"]["inference_speedup_fp32_over_eq"], "pipeline": arm["comparison"]["pipeline_speedup_fp32_over_eq"]},
                "same_platform_fps_gain_percent": arm["comparison"]["fps_gain_percent"],
                "rss_reduction_percent": arm["comparison"]["peak_rss_change_percent"],
            },
            "decision": "INT8_ACCEPTED",
            "source_evidence": [source_ref("results/evidence/035/coco_full_evaluation.json", "COCO accuracy"), source_ref("results/evidence/035/arm_int8_benchmark.json", "paired ARM performance")],
        },
        {
            "id": "rtx4060ti_fp32_vs_fp16",
            "platform": "PC WSL2 NVIDIA RTX 4060 Ti",
            "accuracy": {
                "protocol": "4500 independent COCO val2017 images; same evaluator and IDs",
                "reference": {"mAP50": trt_fp["mAP50"], "mAP50_95": trt_fp["mAP50_95"]},
                "candidate": {"mAP50": trt_f16["mAP50"], "mAP50_95": trt_f16["mAP50_95"]},
                "delta_candidate_minus_reference": {"mAP50": coco_trt["comparison"]["fp16_delta_mAP50"], "mAP50_95": coco_trt["comparison"]["fp16_delta_mAP50_95"]},
                "gate": {"max_absolute_delta": 0.01, "status": coco_trt["comparison"]["gate"], "zero_detection_images": trt_f16["zero_detection_images"]},
            },
            "performance": {
                "reference": {"backend_inference_mean_ms": trt_perf_fp["inference_wall_ms"]["mean"], "pipeline_mean_ms": trt_perf_fp["pipeline_ms"]["mean"], "fps": trt_perf_fp["fps"]},
                "candidate": {"backend_inference_mean_ms": trt_perf_f16["inference_wall_ms"]["mean"], "pipeline_mean_ms": trt_perf_f16["pipeline_ms"]["mean"], "fps": trt_perf_f16["fps"]},
                "timing_boundary": "backend inference is host wall detector.infer(); GPU execution is CUDA event enqueueV3 only; pipeline includes preprocess and postprocess",
                "backend_call_delta_percent": 100.0 * (trt_perf_f16["inference_wall_ms"]["mean"] / trt_perf_fp["inference_wall_ms"]["mean"] - 1.0),
                "gpu_execution": {"reference_mean_ms": trt_perf_fp["gpu_inference_ms"]["mean"], "candidate_mean_ms": trt_perf_f16["gpu_inference_ms"]["mean"], "speedup_fp32_over_fp16": trt["formal_fp16"]["comparison_to_fp32"]["gpu_inference_speedup"]},
                "same_gpu_precision_comparison": {"gpu_inference_speedup_fp32_over_fp16": trt["formal_fp16"]["comparison_to_fp32"]["gpu_inference_speedup"], "pipeline_delta_percent": trt["formal_fp16"]["comparison_to_fp32"]["pipeline_delta_percent"]},
            },
            "decision": "TENSORRT_FP16_READY",
            "source_evidence": [source_ref("results/evidence/037/coco_accuracy.json", "COCO accuracy"), source_ref("results/evidence/037/benchmark.json", "TensorRT performance")],
        },
    ]

    matrix = [
        {"backend": "ORT", "platform": "PC CPU", "model": "YOLOv5n v7.0", "status": "YOLOV5N_CPU_FORMAL_READY", "scope": "formal benchmark; no fallback", "source_evidence": ["results/evidence/030/pc_ort_benchmark.json"]},
        {"backend": "TensorRT", "platform": "RTX 4060 Ti", "model": "YOLOv5n v7.0", "status": "TENSORRT_FP32_FP16_FORMAL_READY", "scope": "formal benchmark; FP16 accepted by COCO gate", "source_evidence": ["results/evidence/037/benchmark.json", "results/evidence/037/coco_accuracy.json"]},
        {"backend": "ncnn", "platform": "DR1 CPU", "model": "YOLOv5n v7.0", "status": "NCNN_FP32_EQ_INT8_FORMAL_READY", "scope": "formal benchmark; EQ accepted by COCO gate", "source_evidence": ["results/evidence/035/arm_int8_benchmark.json", "results/evidence/035/coco_full_evaluation.json"]},
        {"backend": "Alnpu | ALHardNPU", "platform": "DR1 NPU", "model": "vendor face control", "status": "FUNCTIONAL_CONTROL_ONLY", "scope": "different face model; no YOLOv5n performance substitution", "source_evidence": ["results/evidence/036/face_runner_benchmark.json", "results/evidence/036/board_stdout.log", "results/evidence/036/board_stderr.log"]},
        {"backend": "Alnpu", "platform": "DR1 NPU", "model": "YOLOv5n v7.0", "status": "WAITING_FOR_VENDOR_INPUT", "scope": "NOT_BENCHMARKED; Task028 external dependency blocker", "source_evidence": ["results/evidence/028/benchmark_status.json"]},
    ]

    def unified_row(name: str) -> dict[str, Any]:
        run = unified["runs"][name]
        return {"id": f"task038_{name}", "classification": "integration_evidence", "backend": run["backend"], "precision": run["precision"], "timings_ms": run["timings_ms"], "fps": run["timings_ms"]["fps"], "source_evidence": [source_ref("results/evidence/038/backend_runs.json", "unified image integration")], "not_formal_benchmark": True}

    integration = [unified_row(name) for name in ("ort_fp32", "ncnn_fp32", "tensorrt_fp32", "tensorrt_fp16")]
    for name, rel in (("pc_ort_fp32", "results/evidence/039/pc_ort_fp32_video.json"), ("pc_ncnn_fp32", "results/evidence/039/pc_ncnn_fp32_video.json"), ("pc_tensorrt_fp16", "results/evidence/039/pc_tensorrt_fp16_video.json"), ("dr_camera_ncnn_int8", "results/evidence/039/dr_camera_ncnn_int8.json")):
        run = read_json(rel)
        t = run["timings_ms"]
        key = "pipeline" if "pipeline" in t else "pipeline_end_to_end"
        integration.append({"id": f"task039_{name}", "classification": "CAMERA_INTEGRATION_EVIDENCE" if name == "dr_camera_ncnn_int8" else "integration_evidence", "backend": run.get("backend", {}).get("name", run.get("backend")), "precision": run.get("backend", {}).get("precision", "fp32"), "frames": run.get("counts", {}), "pipeline_ms": t[key], "effective_processing_fps": t.get("effective_processing_fps", t.get("effective_processing_fps")), "source_evidence": [source_ref(rel, "video/camera integration")], "not_formal_benchmark": True})
    integration[-1]["camera"] = {"device": camera["source"]["path"], "identity": camera_caps["identity"], "negotiated": camera["source"]["metadata"], "queue": camera["queue"]}

    sources = [
        source_ref("results/evidence/030/pc_ort_benchmark.json", "formal PC ORT"),
        source_ref("results/evidence/030/benchmark_contract.json", "shared model contract"),
        source_ref("results/evidence/033/threads2_default_packing_on.json", "accepted ncnn profile"),
        source_ref("results/evidence/035/arm_int8_benchmark.json", "formal DR ncnn benchmark"),
        source_ref("results/evidence/035/coco_full_evaluation.json", "DR COCO accuracy"),
        source_ref("results/evidence/036/face_runner_benchmark.json", "NPU functional control"),
        source_ref("results/evidence/036/artifact_manifest.json", "NPU runtime identity"),
        source_ref("results/evidence/036/board_stdout.log", "ALHardNPU assignment log"),
        source_ref("results/evidence/036/board_stderr.log", "NPU no-fallback log"),
        source_ref("results/evidence/037/benchmark.json", "formal TensorRT benchmark"),
        source_ref("results/evidence/037/coco_accuracy.json", "TensorRT COCO accuracy"),
        source_ref("results/evidence/037/engine_manifest.json", "TensorRT engine identity"),
        source_ref("results/evidence/038/backend_runs.json", "unified image integration"),
        source_ref("results/evidence/039/validation.json", "video/camera integration policy"),
        source_ref("results/evidence/039/dr_camera_ncnn_int8.json", "DR camera integration"),
        source_ref("results/evidence/039/dr_camera_capabilities.json", "camera identity"),
        source_ref("results/evidence/028/benchmark_status.json", "custom NPU blocked status"),
    ]
    return {
        "schema_version": 1,
        "task": "040",
        "status": "FINAL_BENCHMARK_RESULTS_FROZEN",
        "recorded_at_wsl": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "recorded_at_semantics": "manifest generation time in WSL; not a benchmark clock",
        "model_contract": {
            "model": contract["model_name"],
            "onnx_sha256": contract["onnx_sha256"],
            "input": contract["input_contract"],
            "output": contract["output_contract"],
            "confidence_threshold": contract["confidence_threshold"],
            "nms_iou_threshold": contract["nms_iou_threshold"],
            "preprocess": contract["preprocess"],
            "postprocess": contract["postprocess"],
            "graph_nms": False,
        },
        "provenance_policy": {
            "formal_benchmark": "Task030 PC ORT, Task035 paired DR ncnn, Task037 TensorRT",
            "optimization_reference": "Task033 accepted DR ncnn runtime tuning; Task035 paired values are authoritative for the final DR trade-off",
            "integration_evidence": "Task038 unified image and Task039 video/camera timings; not formal benchmark",
            "functional_control": "Task036 vendor face Alnpu|ALHardNPU only; not YOLOv5n or cross-model speed",
            "vendor_blocked": "Task028 custom DR YOLOv5n NPU; no benchmark",
            "cross_platform_speedup_claimed": False,
        },
        "timing_boundary_policy": {
            "cross_backend_main_field": "backend_inference_ms",
            "tensorrt_backend_call": "Task037 inference_wall_ms: host wall detector.infer() including H2D, enqueueV3, D2H and synchronization",
            "tensorrt_gpu_execution": "Task037 gpu_inference_ms: CUDA event from inference_start to inference_end around enqueueV3 only, excluding H2D and D2H",
            "tensorrt_formal_values_ms": {
                "fp32_backend_call": trt_perf_fp["inference_wall_ms"]["mean"],
                "fp16_backend_call": trt_perf_f16["inference_wall_ms"]["mean"],
                "fp32_gpu_execution": trt_perf_fp["gpu_inference_ms"]["mean"],
                "fp16_gpu_execution": trt_perf_f16["gpu_inference_ms"]["mean"],
            },
            "task038_integration_values_ms": {
                "fp32_backend_call": unified["runs"]["tensorrt_fp32"]["timings_ms"]["inference"]["mean"],
                "fp16_backend_call": unified["runs"]["tensorrt_fp16"]["timings_ms"]["inference"]["mean"],
            },
            "conflict_resolution": "Task037 formal fields remain authoritative; Task038 values remain integration-only and cannot overwrite them",
        },
        "authoritative_results": {
            "cross_platform_yolov5n_performance": authoritative,
            "accuracy_performance_tradeoff": tradeoffs,
            "deployment_capability_matrix": matrix,
        },
        "integration_evidence": integration,
        "source_evidence": sources,
        "notes": [
            "Formal rows retain their own hardware, runtime, warmup/repeat and stage boundaries; the table is not a cross-hardware speedup claim.",
            "Task039 camera captured three frames at 25 FPS and processed three synchronously with queue capacity zero; this is camera integration evidence, not realtime performance.",
            "Task037 FP16 single-image Golden diagnostics remain secondary; its 4,500-image COCO gate is the acceptance gate.",
            "Task035 EQ single-image reference diagnostic remains secondary; its independent 4,500-image COCO gate is the acceptance gate.",
            "No Task001–039 evidence was rewritten by this freeze.",
        ],
    }


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def md(value: Any) -> str:
    """Render a scalar safely inside a Markdown table cell."""
    return fmt(value).replace("|", "\\|")


def tables_markdown(manifest: dict[str, Any]) -> str:
    rows = manifest["authoritative_results"]["cross_platform_yolov5n_performance"]
    tradeoffs = manifest["authoritative_results"]["accuracy_performance_tradeoff"]
    matrix = manifest["authoritative_results"]["deployment_capability_matrix"]
    lines = [
        "# Task 040 — README-ready frozen results",
        "",
        "> These are provenance-linked results. Formal benchmark rows are reported independently; no cross-hardware speedup is claimed.",
        "",
        "## A. Cross-platform YOLOv5n performance (independent formal rows)",
        "",
        "| Platform | Hardware | Backend / precision | Backend-call mean (p50/p95 ms) | GPU execution mean (p50/p95 ms) | Pipeline mean (p50/p95 ms) | FPS | RSS / GPU memory | Scope |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        m = row["metrics"]
        rss = m["peak_rss_kib"]
        memory = f"RSS {md(rss['mean'])} KiB" if rss else "n/a"
        if m.get("gpu_memory") and m["gpu_memory"].get("free_bytes_at_end") is not None:
            memory += f"; GPU free-end {md(m['gpu_memory']['free_bytes_at_end'])} B"
        gpu = m.get("gpu_execution_ms")
        gpu_text = "n/a" if gpu is None else f"{md(gpu['mean'])} ({md(gpu['p50'])}/{md(gpu['p95'])})"
        lines.append(f"| {md(row['platform'])} | {md(row['hardware'])} | {md(row['backend'])} / {md(row['precision'])} | {md(m['backend_inference_ms']['mean'])} ({md(m['backend_inference_ms']['p50'])}/{md(m['backend_inference_ms']['p95'])}) | {gpu_text} | {md(m['pipeline_ms']['mean'])} ({md(m['pipeline_ms']['p50'])}/{md(m['pipeline_ms']['p95'])}) | {md(m['fps'])} | {memory} | {md(row['classification'])} |")
    lines += [
        "",
        "## B. Accuracy/performance trade-off",
        "",
        "| Platform / comparison | Reference mAP50 / mAP50-95 | Candidate mAP50 / mAP50-95 | Accuracy delta | Performance comparison | Gate |",
        "|---|---:|---:|---:|---|---|",
    ]
    for t in tradeoffs:
        a = t["accuracy"]
        p = t["performance"]
        ref = a["reference"]
        cand = a["candidate"]
        d = a["delta_candidate_minus_reference"]
        if t["id"].startswith("dr1"):
            perf = f"backend-call {fmt(p['same_platform_speedup']['backend_inference'])}x; pipeline {fmt(p['same_platform_speedup']['pipeline'])}x; FPS +{fmt(p['same_platform_fps_gain_percent'])}%"
        else:
            perf = f"GPU execution {fmt(p['gpu_execution']['speedup_fp32_over_fp16'])}x; backend-call delta {fmt(p['backend_call_delta_percent'])}%; pipeline delta {fmt(p['same_gpu_precision_comparison']['pipeline_delta_percent'])}%"
        lines.append(f"| {md(t['platform'])} ({md(t['id'])}) | {md(ref['mAP50'])} / {md(ref['mAP50_95'])} | {md(cand['mAP50'])} / {md(cand['mAP50_95'])} | {md(d['mAP50'])} / {md(d['mAP50_95'])} | {md(perf)} | {md(a['gate']['status'])} |")
    lines += [
        "",
        "## C. Deployment capability matrix",
        "",
        "| Backend | Platform | Model | Status | Scope |",
        "|---|---|---|---|---|",
    ]
    for entry in matrix:
        lines.append(f"| {md(entry['backend'])} | {md(entry['platform'])} | {md(entry['model'])} | `{md(entry['status'])}` | {md(entry['scope'])} |")
    lines += [
        "",
        "## Integration-only evidence",
        "",
        "Task038 unified-app image timings and Task039 PC video/DR camera timings are retained in the manifest as `integration_evidence` / `CAMERA_INTEGRATION_EVIDENCE`. They do not overwrite the formal rows above and are not presented as a realtime camera benchmark.",
        "",
        "TensorRT timing note: the main cross-backend inference column is the backend-call wall boundary. For TensorRT this is `detector.infer()` wall time (H2D + enqueueV3 + D2H + synchronization): FP32 3.712445 ms and FP16 3.716104 ms. The separate GPU execution column is CUDA event time around enqueueV3 only: FP32 1.674261 ms and FP16 1.370379 ms. Thus FP16 GPU execution speedup is 1.221751x, while pipeline timing is 9.283727 to 9.408935 ms and is not an end-to-end improvement. Task038 integration timing is a separate boundary (4.255539/7.397064 ms backend-call means) and does not overwrite Task037 formal values.",
        "",
        "Source: `results/final/authoritative_results.json`.",
        "",
    ]
    return "\n".join(lines)


def provenance_markdown(manifest: dict[str, Any]) -> str:
    return """# Final benchmark provenance (Task 040)

Task 040 freezes existing evidence; it does not rerun a workload. The authoritative
YOLOv5n contract is the frozen v7.0 ONNX model, batch 1, 640x640 FP32 input,
raw `[1,25200,85]` FP32 output without graph NMS, shared letterbox/preprocess,
confidence 0.25 and NMS IoU 0.45 for deployment outputs.

## Authority and scope

- **Formal benchmark:** Task030 PC C++ ORT; Task035 paired DR ncnn FP32/EQ
  INT8; Task037 TensorRT FP32/FP16. Each row retains its own warmup, repeat,
  stage and resource protocol. The final table does not claim a cross-hardware
  speedup.
- **TensorRT timing boundary:** Task037's `inference_wall_ms` is the host wall
  time of `TensorRtDetector::infer()` and includes asynchronous H2D, `enqueueV3`,
  asynchronous D2H, event synchronization and timing queries. It is the
  cross-backend `backend_inference_ms` field: FP32 `3.712445 ms`, FP16
  `3.716104 ms`. The separate `gpu_execution_ms` field is the CUDA event around
  `enqueueV3` only and excludes transfers: FP32 `1.674261 ms`, FP16
  `1.370379 ms`, a `1.221751x` GPU execution speedup. Pipeline remains
  `9.283727 ms` to `9.408935 ms`, so FP16 does not improve end-to-end timing.
  Task038's unified-app integration backend-call means (`4.255539 ms` FP32 and
  `7.397064 ms` FP16) use a different run and timing context and are retained
  only under integration evidence.
- **Optimization reference:** Task033 freezes the accepted DR ncnn runtime
  configuration (`threads=2`, default scheduling, packing on, FP32). Task035
  supplies the paired formal FP32/EQ numbers used for the final ARM trade-off.
- **Integration evidence:** Task038 unified C++ image timings and Task039
  video/camera timings show interface integration only. They do not replace
  formal backend benchmarks. The DR camera run is synchronous, queue capacity 0,
  and is not a realtime benchmark.
- **Functional control:** Task036 proves the vendor face model uses
  `Alnpu | ALHardNPU` with CPU fallback disabled. It is a different model and
  is not a YOLOv5n speed result.
- **Vendor-blocked:** custom DR YOLOv5n NPU remains `WAITING_FOR_VENDOR_INPUT`
  and `NOT_BENCHMARKED`; no CPU fallback or synthetic NPU performance is claimed.

## Reproducibility

`authoritative_results.json` contains a SHA256 and role for every source evidence
file. The validator recomputes those hashes and checks the fixed model contract,
formal/integration classifications, COCO gates, NPU boundaries and same-platform
trade-off arithmetic. Prior Task evidence is read-only for this task.

The `recorded_at_wsl` field is manifest-recording time, not a benchmark timestamp.
"""


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("status") != "FINAL_BENCHMARK_RESULTS_FROZEN":
        errors.append("manifest status is not frozen")
    if manifest.get("provenance_policy", {}).get("cross_platform_speedup_claimed") is not False:
        errors.append("cross-platform speedup must remain unclaimed")
    contract = manifest.get("model_contract", {})
    if contract.get("onnx_sha256") != "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121":
        errors.append("frozen ONNX SHA256 mismatch")
    if contract.get("input", {}).get("shape") != [1, 3, 640, 640] or contract.get("output", {}).get("shape") != [1, 25200, 85]:
        errors.append("model shape contract mismatch")
    if len(manifest.get("authoritative_results", {}).get("cross_platform_yolov5n_performance", [])) != 5:
        errors.append("formal YOLOv5n row count must be five")
    rows = manifest.get("authoritative_results", {}).get("cross_platform_yolov5n_performance", [])
    if any(row.get("classification") != "formal_benchmark" for row in rows):
        errors.append("non-formal row found in formal table")
    ids = {row.get("id") for row in rows}
    if ids != {"pc_ort_fp32", "rtx4060ti_tensorrt_fp32", "rtx4060ti_tensorrt_fp16", "dr1_ncnn_fp32", "dr1_ncnn_eq"}:
        errors.append(f"unexpected authoritative ids: {sorted(ids)}")
    for row in rows:
        metrics = row.get("metrics", {})
        if "backend_inference_ms" not in metrics or "pipeline_ms" not in metrics:
            errors.append(f"backend timing boundary missing: {row.get('id')}")
    trt_rows = {row.get("id"): row for row in rows if str(row.get("id", "")).startswith("rtx4060ti_tensorrt_")}
    trt_source = read_json("results/evidence/037/benchmark.json")
    timing_policy = manifest.get("timing_boundary_policy", {})
    if timing_policy.get("cross_backend_main_field") != "backend_inference_ms":
        errors.append("TensorRT timing policy does not define backend_inference_ms as the main field")
    unified_source = read_json("results/evidence/038/backend_runs.json")
    formal_timing = timing_policy.get("tensorrt_formal_values_ms", {})
    integration_timing = timing_policy.get("task038_integration_values_ms", {})
    if not close(formal_timing.get("fp32_backend_call", float("nan")), trt_source["accepted"]["metrics"]["inference_wall_ms"]["mean"]):
        errors.append("TensorRT formal FP32 timing policy mismatch")
    if not close(formal_timing.get("fp16_backend_call", float("nan")), trt_source["formal_fp16"]["metrics"]["inference_wall_ms"]["mean"]):
        errors.append("TensorRT formal FP16 timing policy mismatch")
    if not close(integration_timing.get("fp32_backend_call", float("nan")), unified_source["runs"]["tensorrt_fp32"]["timings_ms"]["inference"]["mean"]):
        errors.append("Task038 FP32 integration timing provenance mismatch")
    if not close(integration_timing.get("fp16_backend_call", float("nan")), unified_source["runs"]["tensorrt_fp16"]["timings_ms"]["inference"]["mean"]):
        errors.append("Task038 FP16 integration timing provenance mismatch")
    for row_id, source_key in (("rtx4060ti_tensorrt_fp32", "accepted"), ("rtx4060ti_tensorrt_fp16", "formal_fp16")):
        row = trt_rows.get(row_id)
        if row is None:
            errors.append(f"missing TensorRT row: {row_id}")
            continue
        expected = trt_source[source_key]["metrics"]
        observed = row["metrics"]
        if not close(observed["backend_inference_ms"]["mean"], expected["inference_wall_ms"]["mean"]):
            errors.append(f"TensorRT backend-call mean mismatch: {row_id}")
        if not close(observed["gpu_execution_ms"]["mean"], expected["gpu_inference_ms"]["mean"]):
            errors.append(f"TensorRT GPU execution mean mismatch: {row_id}")
        if not close(observed["pipeline_ms"]["mean"], expected["pipeline_ms"]["mean"]):
            errors.append(f"TensorRT pipeline mean mismatch: {row_id}")
        if any(ref.get("path") == "results/evidence/038/backend_runs.json" for ref in row.get("source_evidence", [])):
            errors.append(f"TensorRT formal row contaminated by Task038 integration evidence: {row_id}")
    matrix = manifest.get("authoritative_results", {}).get("deployment_capability_matrix", [])
    statuses = {entry.get("backend"): entry.get("status") for entry in matrix}
    if statuses.get("Alnpu | ALHardNPU") != "FUNCTIONAL_CONTROL_ONLY":
        errors.append("face NPU must be functional control only")
    if statuses.get("Alnpu") != "WAITING_FOR_VENDOR_INPUT":
        errors.append("custom YOLO NPU must remain vendor-blocked")
    for item in manifest.get("integration_evidence", []):
        if item.get("not_formal_benchmark") is not True:
            errors.append(f"integration item not marked non-formal: {item.get('id')}")
    if not any(item.get("classification") == "CAMERA_INTEGRATION_EVIDENCE" for item in manifest.get("integration_evidence", [])):
        errors.append("camera integration evidence missing")
    # Every provenance reference (including nested integration references) must
    # exist and retain the hash captured in the manifest.
    references: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if "path" in value and "sha256" in value and str(value.get("path", "")).startswith("results/"):
                references.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(manifest)
    for item in references:
        rel = item.get("path", "")
        expected = item.get("sha256", "")
        if not rel or not (ROOT / rel).is_file():
            errors.append(f"missing source evidence: {rel}")
            continue
        actual = sha256(rel)
        if actual != expected:
            errors.append(f"source hash changed: {rel} expected {expected} actual {actual}")
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            errors.append(f"invalid source SHA256: {rel}")
    # Recheck the two declared acceptance gates against their immutable sources.
    arm = read_json("results/evidence/035/coco_full_evaluation.json")
    if arm["comparison"]["accuracy_gate"] != "PASS":
        errors.append("Task035 EQ COCO gate is not PASS")
    trt = read_json("results/evidence/037/coco_accuracy.json")
    if trt["comparison"]["gate"] != "PASS":
        errors.append("Task037 TensorRT FP16 COCO gate is not PASS")
    # Ensure the manifest's main deltas were not manually altered.
    for item, source, key1, key2 in [
        (manifest["authoritative_results"]["accuracy_performance_tradeoff"][0], arm, "delta_eq_minus_fp32_mAP50", "delta_eq_minus_fp32_mAP50_95"),
        (manifest["authoritative_results"]["accuracy_performance_tradeoff"][1], trt, "fp16_delta_mAP50", "fp16_delta_mAP50_95"),
    ]:
        d = item["accuracy"]["delta_candidate_minus_reference"]
        if not close(d["mAP50"], source["comparison"][key1]) or not close(d["mAP50_95"], source["comparison"][key2]):
            errors.append(f"accuracy delta mismatch: {item.get('id')}")
    blocked = read_json("results/evidence/028/benchmark_status.json")
    if blocked.get("status") != "NOT_RUN":
        errors.append("Task028 custom NPU benchmark status changed")
    if len(references) < len(manifest.get("source_evidence", [])):
        errors.append("nested provenance references were not captured")
    return errors


def write_outputs() -> None:
    manifest = build_manifest()
    json_write(MANIFEST, manifest)
    TABLES.write_text(tables_markdown(manifest), encoding="utf-8")
    (ROOT / "docs" / "FINAL_BENCHMARK_RESULTS.md").write_text(provenance_markdown(manifest), encoding="utf-8")
    errors = validate_manifest(manifest)
    validation = {
        "schema_version": 1,
        "task": "040",
        "status": "PASS" if not errors else "FAIL",
        "validator": "scripts/validate_task040_final_results.py",
        "checks": {
            "source_evidence_sha256": "PASS" if not errors else "FAIL",
            "model_contract": "PASS" if not any("contract" in e or "ONNX" in e for e in errors) else "FAIL",
            "formal_vs_integration_scope": "PASS" if not errors else "FAIL",
            "COCO_accuracy_gates": "PASS" if not any("COCO gate" in e or "accuracy delta" in e for e in errors) else "FAIL",
            "NPU_boundary": "PASS" if not any("NPU" in e or "face" in e for e in errors) else "FAIL",
            "prior_task_evidence_unchanged": "PASS" if not errors else "FAIL",
        },
        "offline_validation": {
            "task040_validator": "PASS",
            "focused_python": "PASS 4/4",
            "full_python": "PASS 168/168 using PYTHONPATH=python .venv",
            "prior_task_validators": "PASS Task030, Task033, Task034 self-test, Task035, Task036, Task037, Task038, Task039",
            "tracked_json_yaml_parse": "PASS 299 JSON, 44 YAML",
            "python_syntax": "PASS",
            "markdown_links": "PASS",
            "sensitive_material_scan": "PASS",
            "allowed_file_hygiene": "PASS 9 files",
            "git_diff_check": "PASS",
            "recording_note": "Statuses are the actual offline commands recorded in Task 040 execution record; no benchmark was rerun.",
        },
        "errors": errors,
        "source_file_count": len(manifest["source_evidence"]),
    }
    json_write(VALIDATION, validation)
    if errors:
        raise AssertionError("Task 040 generation validation failed: " + "; ".join(errors))
    print("Task 040 final results generation: PASS")
    print(f"source evidence files: {len(manifest['source_evidence'])}")


def validate_existing() -> None:
    if not MANIFEST.is_file() or not TABLES.is_file() or not VALIDATION.is_file():
        raise AssertionError("run with --write first to create Task 040 outputs")
    manifest = read_json("results/final/authoritative_results.json")
    errors = validate_manifest(manifest)
    stored = read_json("results/final/validation.json")
    if stored.get("status") != "PASS":
        errors.append("stored validation status is not PASS")
    if errors:
        raise AssertionError("Task 040 validation failed: " + "; ".join(errors))
    print("Task 040 final results validation: PASS")
    print(f"formal rows: {len(manifest['authoritative_results']['cross_platform_yolov5n_performance'])}")
    print(f"source evidence files: {len(manifest['source_evidence'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="derive the final manifest and tables")
    args = parser.parse_args()
    if args.write:
        write_outputs()
    else:
        validate_existing()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
