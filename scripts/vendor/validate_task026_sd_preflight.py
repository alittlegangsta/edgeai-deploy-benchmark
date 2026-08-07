#!/usr/bin/env python3
"""Offline validation for the read-only Task 026 SD preflight."""

import argparse
import json
import re
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = (
    "candidate_manifest_verification.json",
    "block_device_inventory.json",
    "write_script_audit.json",
    "sd_write_plan.json",
    "preflight_summary.json",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    errors = []
    docs = {}
    for name in REQUIRED:
        path = args.evidence_dir / name
        if not path.is_file():
            errors.append(f"missing evidence: {name}")
            continue
        try:
            docs[name] = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {name}: {type(exc).__name__}")

    candidate = docs.get(REQUIRED[0], {})
    if candidate.get("manifest_structure", {}).get("entry_count") != 13:
        errors.append("Task 025 candidate manifest entry count is not 13")
    candidate_status = candidate.get("status")
    if candidate_status == "PASS_HASHES_RECOMPUTED":
        if candidate.get("recompute_performed") is not True:
            errors.append("recomputed candidate must set recompute_performed=true")
        if candidate.get("missing_or_unavailable") != []:
            errors.append("recomputed candidate still has missing files")
        files = candidate.get("files", {})
        if len(files) != 13 or not all(item.get("match") is True for item in files.values()):
            errors.append("all 13 candidate file hashes must match")
        if candidate.get("aggregate_manifest", {}).get("match") is not True:
            errors.append("candidate aggregate manifest hash must match")
    elif candidate_status == "BLOCKED_CANDIDATE_FILES_UNAVAILABLE":
        if candidate.get("recompute_performed") is not False:
            errors.append("unavailable VM candidate must not claim hash recomputation")
    else:
        errors.append("unknown candidate status")

    devices = docs.get(REQUIRED[1], {})
    if devices.get("status") == "PASS_REMOVABLE_CANDIDATE_IDENTIFIED":
        candidates = devices.get("removable_candidates", [])
        if len(candidates) != 1 or candidates[0].get("path") != "/dev/sdb":
            errors.append("exactly /dev/sdb must be the removable candidate")
        elif candidates[0].get("removable") is not True or candidates[0].get("read_only") is not False:
            errors.append("candidate must be removable and writable")
        excluded = {item.get("path"): item for item in devices.get("devices", [])}
        for path in ("/dev/sda", "/dev/sr0"):
            if path not in excluded or excluded[path].get("candidate") is not False:
                errors.append(f"device must be explicitly excluded: {path}")
        if not any(item.get("path", "").startswith("/dev/loop") and item.get("candidate") is False for item in devices.get("devices", [])):
            errors.append("loop devices must be explicitly excluded")
    elif devices.get("status") == "BLOCKED_NO_CONFIRMED_REMOVABLE_SD":
        if devices.get("removable_candidates") != []:
            errors.append("blocked inventory cannot contain removable candidates")
    else:
        errors.append("block-device status mismatch")

    audit = docs.get(REQUIRED[2], {})
    audit_safety = audit.get("safety", {})
    vendor_script_executed = audit_safety.get("destructive_vendor_script_executed", audit_safety.get("destructive_script_executed"))
    vendor_wrote = audit_safety.get("block_device_written_by_vendor_script", audit_safety.get("block_device_written"))
    if vendor_script_executed is not False:
        errors.append("destructive scripts must not be executed")
    if vendor_wrote is not False:
        errors.append("block device must not be written")
    if audit.get("status") not in {"PASS_STATIC_REVIEW", "PARTIAL_PRIOR_EVIDENCE_VM_UNAVAILABLE"}:
        errors.append("unknown script audit status")
    for item in audit.get("scripts", []):
        if item.get("executed_in_this_phase") is not False:
            errors.append(f"script executed: {item.get('name')}")
        if audit.get("status") == "PASS_STATIC_REVIEW" and item.get("source_read_in_this_phase") is not True:
            errors.append(f"script source not read: {item.get('name')}")

    plan = docs.get(REQUIRED[3], {})
    if plan.get("deployment_approval") not in {"PENDING", "APPROVED_BY_USER"}:
        errors.append("deployment approval state mismatch")
    if plan.get("sd_write") not in {"NOT_PERFORMED", "COMPLETED"}:
        errors.append("deployment approval/write state mismatch")
    if plan.get("status") == "AWAITING_EXPLICIT_SD_WRITE_APPROVAL":
        if plan.get("target_device", {}).get("path") != "/dev/sdb":
            errors.append("approval-ready plan must target /dev/sdb")
        if plan.get("awaiting_explicit_sd_write_approval") is not True:
            errors.append("approval-ready plan must set awaiting=true")
    elif plan.get("status") == "SD_WRITE_COMPLETED_FIRST_BOOT_PENDING":
        if plan.get("target_device", {}).get("path") != "/dev/sdb":
            errors.append("completed write plan must retain /dev/sdb target")
        if plan.get("deployment_approval") != "APPROVED_BY_USER" or plan.get("sd_write") != "COMPLETED":
            errors.append("completed write plan approval state mismatch")
        if plan.get("awaiting_explicit_sd_write_approval") is not False:
            errors.append("completed write plan must clear awaiting flag")
    elif plan.get("awaiting_explicit_sd_write_approval") is not False:
        errors.append("blocked plan must not claim approval-ready")

    summary = docs.get(REQUIRED[4], {})
    if summary.get("status") not in {"BLOCKED_PREWRITE_INPUTS_UNAVAILABLE", "AWAITING_EXPLICIT_SD_WRITE_APPROVAL", "SD_WRITE_COMPLETED_FIRST_BOOT_PENDING", "FIRST_BOOT_PASS_DRIVER_BLOCKED", "FIRST_BOOT_PASS_DEMO_BLOCKED", "FIRST_BOOT_PASS_NPU_DEMO_PASS"}:
        errors.append("summary status mismatch")
    if summary.get("status") == "AWAITING_EXPLICIT_SD_WRITE_APPROVAL":
        if summary.get("candidate_manifest") != "PASS_HASHES_RECOMPUTED":
            errors.append("approval-ready summary candidate status mismatch")
        if summary.get("block_devices") != "PASS_REMOVABLE_CANDIDATE_IDENTIFIED":
            errors.append("approval-ready summary device status mismatch")
        if summary.get("script_audit") != "PASS_STATIC_REVIEW":
            errors.append("approval-ready summary script status mismatch")
        if summary.get("awaiting_explicit_sd_write_approval") is not True:
            errors.append("approval-ready summary must set awaiting=true")
    if summary.get("status") in {"SD_WRITE_COMPLETED_FIRST_BOOT_PENDING", "FIRST_BOOT_PASS_DRIVER_BLOCKED", "FIRST_BOOT_PASS_DEMO_BLOCKED", "FIRST_BOOT_PASS_NPU_DEMO_PASS"}:
        if summary.get("deployment_approval") != "APPROVED_BY_USER" or summary.get("sd_write") != "COMPLETED":
            errors.append("completed write summary approval state mismatch")
        if summary.get("post_write_verification") != "PASS":
            errors.append("completed write summary must record post-write PASS")
        if summary.get("awaiting_explicit_sd_write_approval") is not False:
            errors.append("completed write summary must clear awaiting flag")
        execution_path = args.evidence_dir / "sd_write_execution.json"
        if not execution_path.is_file():
            errors.append("completed write requires sd_write_execution.json")
        else:
            try:
                execution = load(execution_path)
                if execution.get("status") != "SD_WRITE_COMPLETED_FIRST_BOOT_PENDING":
                    errors.append("sd_write_execution status mismatch")
                if execution.get("verification", {}).get("read_only_mount") != "PASS":
                    errors.append("sd_write_execution readback status mismatch")
                if execution.get("verification", {}).get("all_8_boot_root_hashes") != "PASS":
                    errors.append("sd_write_execution file hash status mismatch")
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid sd_write_execution.json: {type(exc).__name__}")
    if summary.get("status") not in {"SD_WRITE_COMPLETED_FIRST_BOOT_PENDING", "FIRST_BOOT_PASS_DRIVER_BLOCKED", "FIRST_BOOT_PASS_DEMO_BLOCKED", "FIRST_BOOT_PASS_NPU_DEMO_PASS"} and summary.get("destructive_commands_run") is not False:
        errors.append("pre-write summary must not claim a destructive command ran")

    if summary.get("status") in {"FIRST_BOOT_PASS_DRIVER_BLOCKED", "FIRST_BOOT_PASS_DEMO_BLOCKED", "FIRST_BOOT_PASS_NPU_DEMO_PASS"}:
        if summary.get("first_boot") != "PASS_PRELIMINARY":
            errors.append("first-boot summary must record PASS_PRELIMINARY")
        if summary.get("physical_first_boot") != "COMPLETED":
            errors.append("first-boot summary must record physical completion")
        if summary.get("serial_boot_observed") != "PASS" or summary.get("linux_login") != "PASS":
            errors.append("first-boot serial/login status mismatch")
        if summary.get("status") == "FIRST_BOOT_PASS_DRIVER_BLOCKED":
            if summary.get("driver_gate") != "BLOCKED_UNCONFIRMED_VENDOR_ORDER":
                errors.append("first-boot driver gate mismatch")
            if summary.get("npu_modules_loaded") is not False or summary.get("official_demo") != "NOT_EXECUTED":
                errors.append("first-boot summary must show no module/demo execution")
        elif summary.get("status") == "FIRST_BOOT_PASS_DEMO_BLOCKED":
            if summary.get("driver_gate") != "PASS_INFERRED_ORDER":
                errors.append("loaded first-boot driver gate mismatch")
            if summary.get("npu_modules_loaded") is not True or summary.get("npu_device_nodes") != "PASS_ALL_THREE":
                errors.append("loaded first-boot summary must show all modules/nodes")
            if summary.get("official_demo") != "BLOCKED_NO_CAMERA":
                errors.append("demo-blocked summary status mismatch")
        else:
            if summary.get("driver_gate") != "PASS_INFERRED_ORDER":
                errors.append("successful first-boot driver gate mismatch")
            if summary.get("npu_modules_loaded") is not True or summary.get("npu_device_nodes") != "PASS_ALL_THREE":
                errors.append("successful first-boot summary must show all modules/nodes")
            if summary.get("official_demo") != "PASS_ALNPU":
                errors.append("successful demo summary status mismatch")
        first_boot_path = args.evidence_dir / "first_boot_validation.json"
        module_path = args.evidence_dir / "npu_module_preflight.json"
        for path in (first_boot_path, module_path):
            if not path.is_file():
                errors.append(f"missing first-boot evidence: {path.name}")
        if first_boot_path.is_file():
            try:
                first_boot = load(first_boot_path)
                if first_boot.get("candidate_sd_boot", {}).get("status") != "PASS_PRELIMINARY":
                    errors.append("first_boot_validation candidate SD status mismatch")
                if first_boot.get("board_write_or_system_change") is not False:
                    errors.append("first_boot_validation must record no board/system write")
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid first_boot_validation.json: {type(exc).__name__}")
        if module_path.is_file():
            try:
                module = load(module_path)
                if summary.get("status") == "FIRST_BOOT_PASS_DRIVER_BLOCKED":
                    if module.get("load_order_gate", {}).get("status") != "BLOCKED_UNCONFIRMED_VENDOR_ORDER":
                        errors.append("npu_module_preflight load gate mismatch")
                    if module.get("board_write_or_module_operation") is not False or module.get("npu_execution") is not False:
                        errors.append("npu_module_preflight must record no module/demo operation")
                else:
                    if module.get("load_order_gate", {}).get("status") != "PASS_INFERRED_ORDER":
                        errors.append("loaded npu_module_preflight load gate mismatch")
                    if module.get("board_write_or_module_operation") is not True:
                        errors.append("loaded npu_module_preflight operation flags mismatch")
                    if summary.get("status") == "FIRST_BOOT_PASS_NPU_DEMO_PASS":
                        if module.get("npu_execution") is not True:
                            errors.append("successful npu_module_preflight must record NPU execution")
                    elif module.get("npu_execution") is not False:
                        errors.append("demo-blocked npu_module_preflight must not record NPU execution")
                    load_path = args.evidence_dir / "npu_module_load_validation.json"
                    demo_path = args.evidence_dir / "official_demo_validation.json"
                    if not load_path.is_file():
                        errors.append("demo-blocked result requires npu_module_load_validation.json")
                    if not demo_path.is_file():
                        errors.append("demo-blocked result requires official_demo_validation.json")
                    if load_path.is_file():
                        try:
                            load_text = load_path.read_text(encoding="utf-8")
                            load_doc = json.loads(load_text)
                            sequence = load_doc.get("sequence", [])
                            if len(sequence) != 3 or any(item.get("return_code") != 0 for item in sequence):
                                errors.append("all three module load attempts must return zero")
                            if load_doc.get("final_state", {}).get("device_nodes") != ["/dev/cma_mem", "/dev/hard_npu", "/dev/soft_npu"]:
                                errors.append("module load final device nodes mismatch")
                        except (OSError, json.JSONDecodeError) as exc:
                            errors.append(f"invalid npu_module_load_validation.json: {type(exc).__name__}")
                    if demo_path.is_file():
                        try:
                            demo = load(demo_path)
                            if summary.get("status") == "FIRST_BOOT_PASS_DEMO_BLOCKED":
                                if demo.get("verdict") != "FIRST_BOOT_PASS_DEMO_BLOCKED" or demo.get("execution", {}).get("process_exit_code") != 255:
                                    errors.append("official demo blocked evidence mismatch")
                                if demo.get("backend_result", {}).get("alnpu_execution_confirmed") is not False:
                                    errors.append("blocked demo cannot claim Alnpu execution")
                            else:
                                if demo.get("verdict") != "FIRST_BOOT_PASS_NPU_DEMO_PASS" or demo.get("execution", {}).get("process_exit_code") != 0:
                                    errors.append("official demo success evidence mismatch")
                                if demo.get("backend_result", {}).get("alnpu_execution_confirmed") is not True:
                                    errors.append("successful demo must confirm Alnpu execution")
                                if demo.get("backend_result", {}).get("cpu_fallback_allowed") is not False:
                                    errors.append("successful demo must disallow CPU fallback")
                        except (OSError, json.JSONDecodeError) as exc:
                            errors.append(f"invalid official_demo_validation.json: {type(exc).__name__}")
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid npu_module_preflight.json: {type(exc).__name__}")

    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task": "026", "phase": summary.get("status"), "approval": summary.get("deployment_approval")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
