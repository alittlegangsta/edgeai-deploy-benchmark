#!/usr/bin/env python3
"""Independent offline checks for Task 028 graph-dialect evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_NAMES = {
    f"yolov5n_opset{opset}_static640_simplify_{switch}"
    for opset in (10, 11, 12)
    for switch in ("off", "on")
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--bisection", type=Path, required=True)
    args = parser.parse_args()
    graph, matrix, board, bisection = map(load, (args.graph, args.matrix, args.board, args.bisection))

    positive = graph.get("positive_control", {})
    frozen = graph.get("frozen_yolov5n", {})
    if positive.get("opsets") != [{"domain": "", "version": 14}]:
        fail("positive-control opset is not the observed opset14")
    if frozen.get("opsets") != [{"domain": "", "version": 12}]:
        fail("frozen graph opset is not 12")
    if positive.get("operator_counts", {}).get("QuantizeLinear", 0) <= 0:
        fail("positive-control QDQ evidence is missing")
    if frozen.get("operator_counts", {}).get("Floor") != 4:
        fail("frozen Floor count is not four")
    if frozen.get("inputs", [{}])[0].get("shape") != [1, 3, 640, 640]:
        fail("frozen input shape changed")
    if frozen.get("outputs", [{}])[0].get("shape") != [1, 25200, 85]:
        fail("frozen output shape changed")

    entries = matrix.get("matrix", [])
    names = {entry.get("name") for entry in entries}
    if names != EXPECTED_NAMES:
        fail(f"export matrix names differ: {sorted(names)}")
    for entry in entries:
        if entry.get("export_status") != "PASS" or entry.get("onnx_checker") != "PASS":
            fail(f"export did not pass checker: {entry.get('name')}")
        if entry.get("sha256") and not SHA256_RE.match(entry["sha256"]):
            fail(f"invalid export SHA256: {entry.get('name')}")
        raw = entry.get("ort_raw_output", {})
        if raw.get("exact_equal") is not True or raw.get("shape") != [1, 25200, 85]:
            fail(f"ORT raw/golden gate failed: {entry.get('name')}")

    board_entries = {entry.get("name"): entry for entry in board.get("candidates", [])}
    if set(board_entries) != EXPECTED_NAMES:
        fail("board candidate set does not match export matrix")
    for name, entry in board_entries.items():
        if entry.get("exit_code") == 0 or entry.get("board_result") == "PASS_ALNPU_LOAD":
            fail(f"board candidate unexpectedly passed without correctness evidence: {name}")
        if "Floor" not in entry.get("stderr", ""):
            fail(f"board candidate lacks the observed Floor gate: {name}")

    probes = {entry.get("model_name"): entry for entry in bisection.get("minimal_probe_results", [])}
    if probes.get("parser_probe_qdq", {}).get("result") != "PASS_ALNPU_LOAD":
        fail("minimal QDQ Alnpu load control is missing")
    if probes.get("parser_probe_floor", {}).get("result") != "UNSUPPORTED_OPERATOR":
        fail("minimal Floor unsupported evidence is missing")
    if not any(entry.get("board_exit_code") == 139 for entry in bisection.get("full_graph_sigsegv_results", [])):
        fail("full-graph SIGSEGV evidence is missing")
    print(json.dumps({
        "status": "PASS",
        "positive_control": "opset14 QDQ; prior Alnpu/ALHardNPU board evidence",
        "export_candidates": len(entries),
        "board_candidates": len(board_entries),
        "minimal_qdq": "PASS_ALNPU_LOAD",
        "full_graph_sigsegv": "reproduced",
        "benchmark": "not run",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
