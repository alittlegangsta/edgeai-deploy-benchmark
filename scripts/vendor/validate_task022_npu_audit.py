#!/usr/bin/env python3
"""Offline consistency checks for Task 022 evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERDICTS = {
    "PASS_VENDOR_ONE_SHOT",
    "BLOCKED_MISSING_VENDOR_ASSETS",
    "BLOCKED_DRIVER_OR_DEVICE",
    "BLOCKED_RUNTIME_ABI",
    "BLOCKED_TOOLCHAIN",
    "BLOCKED_DOCUMENTATION_GAP",
}
REQUIRED = (
    "npu_asset_inventory.json",
    "npu_document_requirements.json",
    "npu_vm_audit.json",
    "npu_board_audit.json",
    "npu_dependency_matrix.json",
    "npu_feasibility_verdict.json",
)
SECONDARY_BLOCKERS = {
    "BLOCKED_MISSING_VENDOR_ASSETS",
    "BLOCKED_RUNTIME_ABI_OR_IDENTITY_UNVERIFIED",
    "BLOCKED_TOOLCHAIN",
    "BLOCKED_DOCUMENTATION_GAP",
    "UNKNOWN_BITSTREAM_DT_MAPPING",
}


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fail(errors: List[str], message: str) -> None:
    errors.append(message)


def validate_consistency(docs: Dict[str, Any], evidence_dir: Path) -> List[str]:
    """Return errors for safety-critical Task 022 evidence relationships."""
    errors: List[str] = []
    verdict = docs.get("npu_feasibility_verdict.json", {})
    verdict_name = verdict.get("verdict")
    if verdict_name not in VERDICTS:
        fail(errors, f"invalid verdict: {verdict_name!r}")

    if verdict.get("audit_status") == "Completed":
        review = verdict.get("audit_review", {})
        if review.get("status") != "PASS" or review.get("source") != "user":
            fail(errors, "completed audit lacks user PASS review")
        if verdict.get("candidate_approved") is not True:
            fail(errors, "completed audit must set candidate_approved=true")

    secondary = verdict.get("secondary_blockers", [])
    if not isinstance(secondary, list) or any(item not in SECONDARY_BLOCKERS for item in secondary):
        fail(errors, "invalid secondary_blockers")

    one_shot = verdict.get("official_one_shot", {})
    one_shot_status = one_shot.get("status")
    one_shot_executed = one_shot.get("executed")
    run_path = evidence_dir / "npu_vendor_one_shot_run.json"
    if one_shot_status == "NOT_EXECUTED" and one_shot_executed is not False:
        fail(errors, "NOT_EXECUTED one-shot must set executed=false")
    if one_shot_executed is True or one_shot_status == "executed_successfully":
        if not run_path.is_file():
            fail(errors, "one-shot marked executed but run evidence is absent")
    if verdict_name and verdict_name.startswith("BLOCKED_"):
        if not verdict.get("blocking_gaps"):
            fail(errors, "blocked verdict has no blocking_gaps")
        if one_shot_executed is True or one_shot_status == "executed_successfully":
            fail(errors, "blocked verdict claims successful one-shot")

    board = docs.get("npu_board_audit.json", {})
    board_modules = board.get("modules", {})
    board_devices = board.get("devices", {})
    board_ready = (
        board_modules.get("npu_or_cma_modules_loaded") is True
        and bool(board_devices.get("npu_nodes"))
        and bool(board_devices.get("cma_nodes"))
    )
    if verdict_name == "PASS_VENDOR_ONE_SHOT" and not board_ready:
        fail(errors, "PASS verdict requires loaded NPU/CMA modules and device nodes")

    matrix = docs.get("npu_dependency_matrix.json", {})
    for item in matrix.get("items", []):
        if not isinstance(item, dict) or not item.get("requirement"):
            fail(errors, "dependency matrix contains malformed item")
    runtime_items = [
        item for item in matrix.get("items", [])
        if isinstance(item, dict) and item.get("requirement") == "npu_runtime library and C API headers"
    ]
    if verdict_name == "PASS_VENDOR_ONE_SHOT" and (
        not runtime_items or runtime_items[0].get("status") != "READY"
    ):
        fail(errors, "PASS verdict requires a READY standalone npu_runtime matrix item")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    errors: List[str] = []
    docs: Dict[str, Any] = {}
    for name in REQUIRED:
        path = args.evidence_dir / name
        if not path.is_file():
            fail(errors, f"missing evidence: {name}")
            continue
        try:
            docs[name] = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            fail(errors, f"invalid JSON {name}: {type(exc).__name__}")

    verdict = docs.get("npu_feasibility_verdict.json", {})
    verdict_name = verdict.get("verdict")
    errors.extend(validate_consistency(docs, args.evidence_dir))
    if verdict_name == "PASS_VENDOR_ONE_SHOT":
        run = verdict.get("official_one_shot", {})
        if run.get("status") != "executed_successfully" or run.get("exit_code") != 0:
            fail(errors, "PASS verdict lacks successful one-shot evidence")

    matrix = docs.get("npu_dependency_matrix.json", {})
    items = matrix.get("items", [])
    if len(items) < 10:
        fail(errors, "dependency matrix is unexpectedly incomplete")
    inventory = docs.get("npu_asset_inventory.json", {})
    for root in inventory.get("roots", []):
        for candidate in root.get("candidates", []):
            digest = candidate.get("sha256")
            if digest is not None and not SHA256_RE.fullmatch(digest):
                fail(errors, f"invalid candidate SHA256: {candidate.get('relative_path')}")

    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "verdict": verdict_name, "required_files": len(REQUIRED)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
