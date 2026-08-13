#!/usr/bin/env python3
"""Validate Task 028 Track C2 host-only evidence independently."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "results" / "evidence" / "028"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {
    f"yolov5n_opset{opset}_static640_simplify_{switch}"
    for opset in (13, 14)
    for switch in ("off", "on")
}


def load(name: str) -> dict:
    try:
        value = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot read {name}: {error}") from error
    if not isinstance(value, dict):
        raise AssertionError(f"{name} is not an object")
    return value


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    export = load("trackc2_export_matrix.json")
    smoke = load("trackc2_official_smoke.json")
    accuracy = load("trackc2_heldout_accuracy.json")
    qdq = load("trackc2_qdq_ranges.json")
    checks: dict[str, bool] = {}

    entries = export.get("matrix", [])
    names = {entry.get("name") for entry in entries}
    checks["export_set"] = names == EXPECTED
    check(checks["export_set"], f"unexpected C2 export names: {sorted(names)}")
    checks["frozen_baseline_preserved"] = (
        export.get("frozen_baseline", {}).get("opset") == 12
        and export.get("frozen_baseline", {}).get("input_sha256")
        == "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
    )
    check(checks["frozen_baseline_preserved"], "frozen opset12/input baseline is not recorded")
    for entry in entries:
        check(entry.get("export_status") == "PASS", f"export failed: {entry.get('name')}")
        check(entry.get("onnx_checker") == "PASS", f"checker failed: {entry.get('name')}")
        check(SHA256_RE.match(str(entry.get("sha256", ""))) is not None, f"bad export hash: {entry.get('name')}")
        raw = entry.get("ort_raw_output", {})
        check(raw.get("exact_equal") is True and raw.get("shape") == [1, 25200, 85], f"raw gate failed: {entry.get('name')}")
    checks["export_raw_contract"] = True

    check(smoke.get("status") == "PASS_GRAPH_AND_HOST_ORT", "C2 smoke status is not PASS_GRAPH_AND_HOST_ORT")
    smoke_entries = {entry.get("name"): entry for entry in smoke.get("candidates", [])}
    check(set(smoke_entries) == EXPECTED, "C2 smoke set differs from exports")
    for name, entry in smoke_entries.items():
        check(entry.get("official_entry_exit_code") == 0, f"official conversion did not exit 0: {name}")
        check(set(entry.get("softnpu_operators", [])) >= {"Add", "MaxPool", "Concat", "Resize"}, f"SoftNPU operator audit incomplete: {name}")
        for kind in ("uint8", "int8"):
            item = entry.get(kind, {})
            check(item.get("status") == "PASS", f"{kind} checker/ORT failed: {name}")
            check(item.get("checker") == "PASS" and item.get("ort") == "PASS", f"{kind} graph invalid: {name}")
    checks["official_conversion_and_ort"] = True
    checks["int8_axis_resolution"] = (
        "opset13/14" in smoke.get("int8_axis_resolution", "")
        and "PASS" in smoke.get("int8_axis_resolution", "")
        and "opset12" in smoke.get("int8_axis_resolution", "")
    )
    check(checks["int8_axis_resolution"], "int8 opset resolution statement is missing")

    check(accuracy.get("status") == "HOST_QUANT_ACCURACY_GATE_BLOCKED", "held-out status unexpectedly passed")
    check(accuracy.get("calibration", {}).get("heldout_overlap") is False, "calibration/held-out overlap")
    check(accuracy.get("heldout", {}).get("ground_truth_available") is False, "ground truth status must be explicit")
    check(accuracy.get("teacher", {}).get("ground_truth_available") is False, "teacher ground truth status must be explicit")
    for kind in ("uint8", "int8"):
        aggregate = accuracy.get("candidates", {}).get(kind, {}).get("aggregate", {})
        gate = accuracy.get("candidates", {}).get(kind, {}).get("task_accuracy_gate", {})
        check(gate.get("pass") is False, f"{kind} task gate was incorrectly promoted")
        check(gate.get("true_precision_recall_map") == "NOT_COMPUTABLE", f"{kind} true mAP was fabricated")
        check(aggregate.get("exact_count_agreement_rate", 0.0) <= 1.0, f"{kind} count metric invalid")
        check(0.0 <= aggregate.get("exact_class_agreement_rate", -1.0) <= 1.0, f"{kind} class metric invalid")
        check(aggregate.get("exact_class_agreement_images") is not None, f"{kind} class agreement missing")
        thresholds = gate.get("thresholds", {})
        check(thresholds.get("exact_class_agreement_rate") == 1.0, f"{kind} class gate threshold missing")
        check("proxy_mAP50_95" in thresholds, f"{kind} proxy mAP gate threshold missing")
        check("exact class agreement" in gate.get("reason", ""), f"{kind} class gate reason missing")
        check(aggregate.get("all_matched_min_iou50") is not None, f"{kind} held-out IoU missing")
        check(aggregate.get("all_matched_max_confidence_delta50") is not None, f"{kind} confidence metric missing")
    checks["heldout_accuracy_gate"] = True

    check(qdq.get("status") == "DIAGNOSTIC_ONLY", "QDQ evidence is not diagnostic-only")
    check(qdq.get("input_sha256") == "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071", "QDQ input hash changed")
    for kind in ("uint8", "int8"):
        tensors = qdq.get("models", {}).get(kind, {}).get("tensors", {})
        check(all(name in tensors for name in ("/MaxPool_output_0", "/MaxPool_1_output_0", "/MaxPool_2_output_0", "/Concat_4_output_0", "/Resize_output_0", "/Resize_1_output_0")), f"{kind} QDQ branch diagnostics incomplete")
        for record in tensors.values():
            check(record.get("qdq", {}).get("scale") is not None, f"{kind} QDQ scale missing")
            check(record.get("qdq", {}).get("zero_point") is not None, f"{kind} QDQ zero point missing")
            check(record.get("fp32_range") and record.get("quantized_dequant_range"), f"{kind} QDQ range missing")
    checks["qdq_branch_diagnostic"] = True
    checks["board_and_benchmark"] = smoke.get("board") == "NOT_EXECUTED_BY_HOST_C2_CONTRACT"
    check(checks["board_and_benchmark"], "C2 must not claim a board or benchmark result")

    result = {
        "schema_version": 1,
        "task": "028",
        "track": "C2",
        "status": "PASS",
        "checks": checks,
        "interpretation": "opset13/14 official host graphs are valid and resolve the opset12 int8 axis error; quantized held-out task accuracy remains blocked, so no board or benchmark was run.",
    }
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
