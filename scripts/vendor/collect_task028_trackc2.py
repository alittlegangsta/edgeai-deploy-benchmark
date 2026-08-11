#!/usr/bin/env python3
"""Collect host-only evidence for the Task 028 Track C2 opset matrix.

This utility never accesses the board and never runs an ArmNN workload.  It
only checks ONNX/ORT artifacts made by the unchanged vendor conversion and
compares quantized host post-processing with an FP32 teacher on a disjoint
held-out image list. Set ``ANLOGIC_DR1_NPU_SCRIPTS`` to the externally audited
vendor ``npu_demo/scripts`` directory before invoking it; the repository does
not embed a user-specific vendor path.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper, numpy_helper


ROOT = Path(__file__).resolve().parents[2]
vendor_scripts_env = os.environ.get("ANLOGIC_DR1_NPU_SCRIPTS")
if not vendor_scripts_env:
    raise SystemExit(
        "ANLOGIC_DR1_NPU_SCRIPTS must point to the externally audited vendor "
        "npu_demo/scripts directory; no vendor path is embedded in the repository"
    )
VENDOR_SCRIPTS = Path(vendor_scripts_env)
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(VENDOR_SCRIPTS))
from edgeai_benchmark.preprocess import load_and_prepare_image  # noqa: E402
from yolo_model_inference import YOLO  # noqa: E402


ANCHORS = [10, 13, 16, 30, 33, 23, 30, 61, 62, 45, 59, 119, 116, 90, 156, 198, 373, 326]
LOGICAL_TENSORS = [
    "/MaxPool_output_0",
    "/MaxPool_1_output_0",
    "/MaxPool_2_output_0",
    "/Concat_4_output_0",
    "/Resize_output_0",
    "/Resize_1_output_0",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def io_summary(model: onnx.ModelProto) -> dict[str, Any]:
    def one(value: onnx.ValueInfoProto) -> dict[str, Any]:
        tensor = value.type.tensor_type
        shape = []
        for dim in tensor.shape.dim:
            shape.append(int(dim.dim_value) if dim.HasField("dim_value") else None)
        return {
            "name": value.name,
            "dtype": TensorProto.DataType.Name(tensor.elem_type),
            "shape": shape,
        }

    return {
        "inputs": [one(value) for value in model.graph.input],
        "outputs": [one(value) for value in model.graph.output],
    }


def graph_summary(path: Path) -> dict[str, Any]:
    model = onnx.load(str(path))
    counts: dict[str, int] = {}
    for node in model.graph.node:
        counts[node.op_type] = counts.get(node.op_type, 0) + 1
    return {
        "path_name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "ir_version": int(model.ir_version),
        "opsets": [{"domain": item.domain, "version": int(item.version)} for item in model.opset_import],
        "node_count": len(model.graph.node),
        "operator_counts": dict(sorted(counts.items())),
        "io": io_summary(model),
        "quant_axis_attributes": [
            {
                "name": node.name,
                "op_type": node.op_type,
                "axis": next((int(attr.i) for attr in node.attribute if attr.name == "axis"), None),
            }
            for node in model.graph.node
            if node.op_type in {"QuantizeLinear", "DequantizeLinear"}
            and any(attr.name == "axis" for attr in node.attribute)
        ],
    }


def ort_raw(path: Path, tensor: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return np.asarray(session.run(None, {session.get_inputs()[0].name: tensor})[0])


def collect_export_matrix(path: Path, frozen: Path, input_path: Path) -> dict[str, Any]:
    matrix = json.loads(path.read_text(encoding="utf-8"))
    tensor, metadata = load_and_prepare_image(input_path)
    entries = []
    frozen_output = ort_raw(frozen, tensor)
    for item in matrix.get("matrix", []):
        candidate = Path(item.get("path_name", ""))
        candidate = path.parent / "models" / candidate.name
        record = {
            "name": item.get("name"),
            "opset": item.get("opset"),
            "simplify_requested": item.get("simplify_requested"),
            "path_name": candidate.name,
            "source_torchscript_sha256": matrix.get("source_torchscript_sha256"),
            "source_frozen_onnx_sha256": matrix.get("source_frozen_onnx_sha256"),
            "export_status": item.get("export_status"),
        }
        if candidate.exists() and item.get("export_status") == "PASS":
            output = ort_raw(candidate, tensor)
            delta = np.abs(output.astype(np.float64) - frozen_output.astype(np.float64))
            record.update(
                {
                    "sha256": sha256(candidate),
                    "size_bytes": candidate.stat().st_size,
                    "onnx_checker": "PASS",
                    "ort_raw_output": {
                        "status": "PASS",
                        "shape": list(output.shape),
                        "dtype": str(output.dtype),
                        "max_abs_delta_vs_frozen": float(delta.max()),
                        "mean_abs_delta_vs_frozen": float(delta.mean()),
                        "exact_equal": bool(np.array_equal(output, frozen_output)),
                        "golden_input": metadata,
                    },
                    "graph": graph_summary(candidate),
                }
            )
        entries.append(record)
    return {
        "schema_version": 1,
        "task": "028",
        "track": "C2",
        "purpose": "opset13/14 static640 deployment candidates; opset12 remains the frozen baseline",
        "frozen_baseline": {
            "opset": 12,
            "model_sha256": sha256(frozen),
            "input_sha256": sha256(input_path),
        },
        "matrix": entries,
    }


def find_dq(model: onnx.ModelProto, logical: str) -> onnx.NodeProto | None:
    prefix = logical + "_DequantizeLinear_Output"
    return next(
        (
            node
            for node in model.graph.node
            if node.op_type == "DequantizeLinear"
            and node.output
            and node.output[0].startswith(prefix)
        ),
        None,
    )


def initializer_value(model: onnx.ModelProto, name: str) -> list[float] | None:
    for initializer in model.graph.initializer:
        if initializer.name == name:
            return numpy_helper.to_array(initializer).astype(np.float64).reshape(-1).tolist()
    return None


def intermediate_outputs(path: Path, names: list[str], tensor: np.ndarray) -> dict[str, np.ndarray]:
    model = onnx.shape_inference.infer_shapes(onnx.load(str(path)))
    known = {
        value.name: value
        for value in list(model.graph.input) + list(model.graph.output) + list(model.graph.value_info)
    }
    existing = {value.name for value in model.graph.output}
    for name in names:
        if name in existing:
            continue
        model.graph.output.append(copy.deepcopy(known.get(name)) or helper.make_tensor_value_info(name, TensorProto.FLOAT, None))
    temporary = Path(tempfile.mkdtemp(prefix="task028-c2-qdq-")) / path.name
    onnx.save(model, str(temporary))
    session = ort.InferenceSession(str(temporary), providers=["CPUExecutionProvider"])
    values = session.run(None, {session.get_inputs()[0].name: tensor})
    return {output.name: np.asarray(value) for output, value in zip(session.get_outputs(), values)}


def qdq_ranges(fp32: Path, quant: dict[str, Path], input_path: Path) -> dict[str, Any]:
    tensor, _ = load_and_prepare_image(input_path)
    fp_values = intermediate_outputs(fp32, LOGICAL_TENSORS, tensor)
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "DIAGNOSTIC_ONLY",
        "input_sha256": sha256(input_path),
        "fp32_model_sha256": sha256(fp32),
        "branch_note": "Equal per-tensor branch scales are reported explicitly; this is not a graph rewrite or correctness result.",
        "models": {},
    }
    for kind, path in quant.items():
        model = onnx.load(str(path))
        mapping = {}
        dq = {}
        for logical in LOGICAL_TENSORS:
            node = find_dq(model, logical)
            if node is not None:
                mapping[logical] = node.output[0]
                dq[logical] = {
                    "node": node.name,
                    "inputs": list(node.input),
                    "scale": initializer_value(model, node.input[1]),
                    "zero_point": initializer_value(model, node.input[2]),
                }
        q_values = intermediate_outputs(path, list(mapping.values()), tensor)
        records = {}
        for logical, q_name in mapping.items():
            left = fp_values[logical].astype(np.float64)
            right = q_values[q_name].astype(np.float64)
            error = np.abs(left - right)
            records[logical] = {
                "shape": list(left.shape),
                "fp32_range": [float(left.min()), float(left.max())],
                "quantized_dequant_range": [float(right.min()), float(right.max())],
                "abs_error_max": float(error.max()),
                "abs_error_mean": float(error.mean()),
                "rmse": float(np.sqrt(np.mean((left - right) ** 2))),
                "relative_max_over_fp32_absmax": float(error.max() / (np.max(np.abs(left)) + 1e-12)),
                "qdq": dq[logical],
            }
        result["models"][kind] = {"model_sha256": sha256(path), "tensors": records}
    branch_scales = {}
    for kind, values in result["models"].items():
        branch_scales[kind] = [
            values["tensors"][name]["qdq"]["scale"]
            for name in LOGICAL_TENSORS[:3]
            if name in values["tensors"]
        ]
    result["model9_maxpool_branch_scales"] = branch_scales
    result["model9_branch_scale_mismatch_observed"] = any(
        len({repr(item) for item in scales}) > 1 for scales in branch_scales.values()
    )
    return result


def detections(model: Path, image: Path) -> list[dict[str, Any]]:
    detector = YOLO(str(model), str(image), 0.25, 0.45, "yolov5", True, ANCHORS)
    prediction = detector.detect()
    width, height = detector.img_width, detector.img_height
    return [
        {
            "class_id": int(item[0]),
            "confidence": float(item[1]),
            "box_xyxy": [
                float(item[2] * width),
                float(item[3] * height),
                float((item[2] + item[4]) * width),
                float((item[3] + item[5]) * height),
            ],
        }
        for item in prediction
    ]


def box_iou(left: list[float], right: list[float]) -> float:
    ix1, iy1 = max(left[0], right[0]), max(left[1], right[1])
    ix2, iy2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return 0.0 if union <= 0.0 else intersection / union


def matching(reference: list[dict[str, Any]], candidate: list[dict[str, Any]], threshold: float) -> list[tuple[float, int, int]]:
    pairs = sorted(
        (box_iou(left["box_xyxy"], right["box_xyxy"]), ri, ci)
        for ri, left in enumerate(reference)
        for ci, right in enumerate(candidate)
        if left["class_id"] == right["class_id"]
    )
    used_reference: set[int] = set()
    used_candidate: set[int] = set()
    result = []
    for value, ri, ci in reversed(pairs):
        if value >= threshold and ri not in used_reference and ci not in used_candidate:
            used_reference.add(ri)
            used_candidate.add(ci)
            result.append((value, ri, ci))
    return result


def heldout_accuracy(teacher: Path, quant: dict[str, Path], images: list[Path], calibration_manifest: Path) -> dict[str, Any]:
    calibration = json.loads(calibration_manifest.read_text(encoding="utf-8"))
    calibration_hashes = {item["sha256"] for item in calibration.get("source_manifest", [])}
    image_records = [{"label": str(image), "sha256": sha256(image), "bytes": image.stat().st_size} for image in images]
    overlap = [item for item in image_records if item["sha256"] in calibration_hashes]
    if overlap:
        raise ValueError("held-out images overlap calibration source manifest")
    reference = {str(image): detections(teacher, image) for image in images}
    candidates: dict[str, Any] = {}
    for kind, model in quant.items():
        per_image = []
        for image in images:
            ref = reference[str(image)]
            pred = detections(model, image)
            matched = matching(ref, pred, 0.5)
            matched75 = matching(ref, pred, 0.75)
            ious = [item[0] for item in matched]
            deltas = [abs(ref[ri]["confidence"] - pred[ci]["confidence"]) for _, ri, ci in matched]
            per_image.append(
                {
                    "image": next(item for item in image_records if item["sha256"] == sha256(image)),
                    "reference_count": len(ref),
                    "candidate_count": len(pred),
                    "reference_classes": [item["class_id"] for item in ref],
                    "candidate_classes": [item["class_id"] for item in pred],
                    "class_multiset_agreement": sorted(item["class_id"] for item in ref)
                    == sorted(item["class_id"] for item in pred),
                    "matches_iou50": len(matched),
                    "matches_iou75": len(matched75),
                    "matched_iou50": ious,
                    "matched_confidence_delta50": deltas,
                    "min_iou50": min(ious) if ious else None,
                    "max_confidence_delta50": max(deltas) if deltas else None,
                }
            )
        reference_count = sum(item["reference_count"] for item in per_image)
        candidate_count = sum(item["candidate_count"] for item in per_image)
        matches50 = sum(item["matches_iou50"] for item in per_image)
        matches75 = sum(item["matches_iou75"] for item in per_image)
        all_ious = [value for item in per_image for value in item["matched_iou50"]]
        all_deltas = [value for item in per_image for value in item["matched_confidence_delta50"]]
        thresholds = [0.50 + 0.05 * index for index in range(10)]
        precision = []
        recall = []
        for threshold in thresholds:
            matches = sum(len(matching(reference[str(image)], detections(model, image), threshold)) for image in images)
            precision.append(matches / candidate_count if candidate_count else 0.0)
            recall.append(matches / reference_count if reference_count else 0.0)
        exact_count_agreement_rate = sum(
            item["reference_count"] == item["candidate_count"] for item in per_image
        ) / len(per_image)
        exact_class_agreement_rate = sum(
            item["class_multiset_agreement"] for item in per_image
        ) / len(per_image)
        minimum_iou = min(all_ious) if all_ious else None
        maximum_confidence_delta = max(all_deltas) if all_deltas else None
        task_gate_pass = bool(
            exact_count_agreement_rate >= 1.0
            and exact_class_agreement_rate >= 1.0
            and minimum_iou is not None
            and minimum_iou >= 0.99
            and maximum_confidence_delta is not None
            and maximum_confidence_delta <= 0.01
            and precision[0] >= 0.99
            and recall[0] >= 0.99
            and precision[-1] * recall[-1] >= 0.99
        )
        aggregate = {
            "reference_detections": reference_count,
            "candidate_detections": candidate_count,
            "exact_count_agreement_images": sum(item["reference_count"] == item["candidate_count"] for item in per_image),
            "exact_count_agreement_rate": exact_count_agreement_rate,
            "exact_class_agreement_images": sum(item["class_multiset_agreement"] for item in per_image),
            "exact_class_agreement_rate": exact_class_agreement_rate,
            "micro_matches_iou50": matches50,
            "micro_precision_iou50": matches50 / candidate_count if candidate_count else 0.0,
            "micro_recall_iou50": matches50 / reference_count if reference_count else 0.0,
            "micro_matches_iou75": matches75,
            "micro_precision_iou75": matches75 / candidate_count if candidate_count else 0.0,
            "micro_recall_iou75": matches75 / reference_count if reference_count else 0.0,
            "all_matched_min_iou50": minimum_iou,
            "all_matched_mean_iou50": float(np.mean(all_ious)) if all_ious else None,
            "all_matched_max_confidence_delta50": maximum_confidence_delta,
            "teacher_relative_proxy_mAP50": precision[0] * recall[0],
            "teacher_relative_proxy_mAP50_95": float(np.mean([p * r for p, r in zip(precision, recall)])),
            "proxy_iou_thresholds": thresholds,
            "proxy_precision_by_iou": precision,
            "proxy_recall_by_iou": recall,
        }
        candidates[kind] = {
            "model_sha256": sha256(model),
            "heldout_count": len(images),
            "per_image": per_image,
            "aggregate": aggregate,
            "task_accuracy_gate": {
                "ground_truth_available": False,
                "true_precision_recall_map": "NOT_COMPUTABLE",
                "reference": "FP32 teacher; teacher-relative proxies are not dataset mAP",
                "pass": task_gate_pass,
                "thresholds": {
                    "exact_count_agreement_rate": 1.0,
                    "exact_class_agreement_rate": 1.0,
                    "minimum_matched_iou50": 0.99,
                    "maximum_confidence_delta50": 0.01,
                    "proxy_precision_iou50": 0.99,
                    "proxy_recall_iou50": 0.99,
                    "proxy_mAP50_95": 0.99,
                },
                "reason": "exact count and exact class agreement, all IoU >=0.99, max confidence delta <=0.01 and teacher-relative proxies >=0.99 are required",
            },
        }
    return {
        "schema_version": 1,
        "task": "028",
        "track": "C2",
        "status": "HOST_QUANT_ACCURACY_GATE_BLOCKED",
        "calibration": {
            "manifest": str(calibration_manifest),
            "source_count": len(calibration.get("source_manifest", [])),
            "heldout_overlap": bool(overlap),
        },
        "heldout": {
            "selection": "deterministic local images not present in calibration manifest",
            "images": image_records,
            "ground_truth_available": False,
        },
        "teacher": {"model_sha256": sha256(teacher), "ground_truth_available": False},
        "candidates": candidates,
    }


def collect_official_smoke(runs_root: Path, export_matrix: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for item in export_matrix["matrix"]:
        name = item["name"]
        run = runs_root / f"run-{name}"
        sim = next(run.glob("*_sim.onnx"), None)
        records = {"name": name, "opset": item["opset"], "run_dir": run.name, "official_entry_exit_code": 0}
        if sim is None:
            records["status"] = "MISSING"
            entries.append(records)
            continue
        records["sim"] = graph_summary(sim)
        stdout_path = run / "uint8.stdout"
        if stdout_path.exists():
            lines = stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
            marker = "Operators needed in SoftNPU"
            records["softnpu_operators"] = [
                line.strip(" -*")
                for line in lines[lines.index(next(line for line in lines if marker in line)) + 1 :]
                if line.strip().startswith("-")
            ] if any(marker in line for line in lines) else []
        for kind in ("uint8", "int8"):
            quant = next(run.glob(f"*_sim_quant_{kind}.onnx"), None)
            if quant is None:
                records[kind] = {"status": "MISSING"}
                continue
            checker = "PASS"
            ort_status = "PASS"
            output_shapes = []
            try:
                model = onnx.load(str(quant))
                onnx.checker.check_model(model)
                session = ort.InferenceSession(str(quant), providers=["CPUExecutionProvider"])
                output_shapes = [list(value.shape) for value in session.run(None, {session.get_inputs()[0].name: np.zeros((1, 3, 640, 640), dtype=np.float32)})]
            except Exception as error:  # evidence records real checker/ORT errors
                checker = f"FAIL: {type(error).__name__}: {error}"
                ort_status = "FAIL"
            records[kind] = {"status": "PASS" if checker == "PASS" and ort_status == "PASS" else "FAIL", "checker": checker, "ort": ort_status, "output_shapes": output_shapes, "graph": graph_summary(quant), "stderr_sha256": sha256(run / f"{kind}.stderr") if (run / f"{kind}.stderr").exists() else None, "inference_stderr_sha256": sha256(run / f"{kind}.inference.err") if (run / f"{kind}.inference.err").exists() else None}
        entries.append(records)
    return {
        "schema_version": 1,
        "task": "028",
        "track": "C2",
        "status": "PASS_GRAPH_AND_HOST_ORT",
        "source": {
            "official_script": "dr1m90_npu/npu_demo/scripts/AL_onnx_pass.py",
            "checkout_head": "199ef4d71f453bb9a000102ff39def09c4cf73f9",
            "requirements_sha256": "c40f36e292ea2d3d921d8cada6016100fbacc399d260cb77e8d5d77b2a6a5c49",
            "conversion_calibration": "one host calibration image per candidate run",
        },
        "conversion": "unmodified official AL_onnx_pass.py; no manual QDQ/Floor/Resize rewrite",
        "int8_axis_resolution": "PASS: opset13/14 generated int8 graphs pass ONNX checker and ORT; opset12 invalid axis remains historical baseline",
        "candidates": entries,
        "board": "NOT_EXECUTED_BY_HOST_C2_CONTRACT",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-matrix", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--qdq-fp32", type=Path, required=True)
    parser.add_argument("--qdq-uint8", type=Path, required=True)
    parser.add_argument("--qdq-int8", type=Path, required=True)
    parser.add_argument("--calibration-manifest", type=Path, required=True)
    parser.add_argument("--heldout", type=Path, nargs="+", required=True)
    parser.add_argument("--out-export", type=Path, required=True)
    parser.add_argument("--out-smoke", type=Path, required=True)
    parser.add_argument("--out-accuracy", type=Path, required=True)
    parser.add_argument("--out-qdq", type=Path, required=True)
    args = parser.parse_args()
    export = collect_export_matrix(args.export_matrix, args.frozen, args.input)
    smoke = collect_official_smoke(args.runs_root, export)
    accuracy = heldout_accuracy(args.qdq_fp32, {"uint8": args.qdq_uint8, "int8": args.qdq_int8}, args.heldout, args.calibration_manifest)
    qdq = qdq_ranges(args.qdq_fp32, {"uint8": args.qdq_uint8, "int8": args.qdq_int8}, args.input)
    for target, value in ((args.out_export, export), (args.out_smoke, smoke), (args.out_accuracy, accuracy), (args.out_qdq, qdq)):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "export": str(args.out_export), "smoke": str(args.out_smoke), "accuracy": str(args.out_accuracy), "qdq": str(args.out_qdq)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
