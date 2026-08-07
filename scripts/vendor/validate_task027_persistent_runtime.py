#!/usr/bin/env python3
"""Validate Task 027's persistent-runtime contract and real build evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_OVERLAY = {
    "etc/network/interfaces", "etc/dhcpcd.conf", "etc/edgeai/runtime.conf",
    "etc/edgeai/authorized_keys", "etc/init.d/S41edgeai-network",
    "etc/init.d/S49edgeai-ssh-keys", "etc/init.d/S98edgeai-npu",
    "usr/bin/edgeai-npu-healthcheck", "usr/bin/edgeai-camera-demo-manual",
}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=Path("results/evidence/027"))
    parser.add_argument("--overlay", type=Path, default=Path("configs/task027/rootfs_overlay"))
    args = parser.parse_args()
    errors: list[str] = []
    evidence = args.evidence_dir
    contract = load(evidence / "persistent_runtime_contract.json")
    overlay = load(evidence / "overlay_static_validation.json")
    build = load(evidence / "formal_rootfs_build.json")
    artifacts = load(evidence / "candidate_runtime_artifacts.json")
    validation = load(evidence / "validation.json")
    key_repair = load(evidence / "ssh_host_key_repair.json")
    keyfix_build = load(evidence / "keyfix_rootfs_build.json")
    keyfix3_build = load(evidence / "keyfix3_rootfs_build.json")
    sd_update = load(evidence / "sd_update_execution.json")

    task_state = contract.get("task_state")
    deployment_readiness = contract.get("deployment_readiness")
    if task_state not in {"In Progress", "Completed"}:
        errors.append("Task 027 state is invalid")
    if task_state == "Completed":
        if deployment_readiness != "COMPLETED_VALIDATED":
            errors.append("completed Task 027 must be COMPLETED_VALIDATED")
    elif deployment_readiness != "READY_FOR_SD_UPDATE_APPROVAL":
        errors.append("deployment readiness is not READY_FOR_SD_UPDATE_APPROVAL")
    if contract.get("sd_update") not in {
        "KEYFIX_PENDING", "KEYFIX_UPDATED_BOARD_BOOT_PENDING",
        "KEYFIX_UPDATED_BOARD_VALIDATED", "KEYFIX2_BOOT_FAILED_KEYFIX3_PENDING_APPROVAL",
        "KEYFIX3_UPDATED_BOARD_BOOT_PENDING", "KEYFIX3_UPDATED_BOARD_VALIDATED",
        "NOT_PERFORMED",
    }:
        errors.append("key-fix SD update state is invalid")
    # The first candidate was explicitly written and booted before the
    # host-key repair was requested. Keep that observation separate from the
    # key-fix2 failure and the later key-fix3 validated replacement.
    if contract.get("board_rebooted") is not True:
        errors.append("initial candidate board reboot must be recorded")
    if contract.get("initial_candidate_sd_update") != "COMPLETED":
        errors.append("initial candidate SD update is not recorded as completed")
    if contract.get("keyfix_candidate_booted") is not True:
        errors.append("deployed key-fix candidate boot must be recorded")
    if contract.get("keyfix_candidate_health") != "FAIL_HEALTHCHECK_FAT_MASK":
        errors.append("deployed key-fix health failure must be retained")
    if task_state == "Completed":
        if contract.get("keyfix3_candidate_booted") is not True:
            errors.append("completed Task 027 must record keyfix3 boot")
        if contract.get("keyfix3_candidate_health") != "PASS":
            errors.append("completed Task 027 must record keyfix3 health PASS")
    elif contract.get("keyfix3_candidate_booted") is not False:
        errors.append("keyfix3 candidate must remain unbooted before validation")
    if contract.get("camera_autostart") is not False:
        errors.append("camera autostart must be false")
    if contract.get("npu_module_order") != ["cma_mem", "hard_npu", "soft_npu"]:
        errors.append("NPU module order mismatch")
    if contract.get("eth0", {}).get("cidr") != "192.168.50.2/24":
        errors.append("eth0 static address mismatch")

    missing = sorted(REQUIRED_OVERLAY - set(overlay.get("files", [])))
    if missing:
        errors.append("overlay evidence missing: " + ", ".join(missing))
    if overlay.get("private_key_files"):
        errors.append("private key files are present in overlay evidence")
    if overlay.get("authorized_key_type") not in {"ssh-ed25519", "ssh-rsa", "ecdsa-sha2"}:
        errors.append("authorized key type is not an approved public key")
    if not re.fullmatch(r"[0-9a-f]{64}", overlay.get("authorized_key_sha256", "")):
        errors.append("authorized key hash is malformed")

    if build.get("status") != "PASS_OFFLINE_BUILDROOT":
        errors.append("formal Buildroot status mismatch")
    if build.get("network_policy", {}).get("network_requests_during_build") != 0:
        errors.append("formal build made network requests")
    if build.get("rootfs_format") != "cpio.lz4+uInitrd.lz4":
        errors.append("rootfs format mismatch")
    for name in ("rootfs_tar_gz", "rootfs_cpio_lz4", "uinitrd_lz4"):
        item = build.get("artifacts", {}).get(name, {})
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            errors.append(f"missing or malformed hash for {name}")
        if item.get("size_bytes", 0) <= 0:
            errors.append(f"non-positive size for {name}")

    if artifacts.get("status") != "STATIC_VALIDATION_PASS":
        errors.append("candidate artifact status mismatch")
    runtime = artifacts.get("runtime", {})
    if runtime.get("aarch64_elf_count", 0) <= 0 or runtime.get("x86_64_elf_count") != 0:
        errors.append("candidate ELF architecture counts mismatch")
    if runtime.get("missing_dt_needed") != []:
        errors.append("candidate runtime closure has missing DT_NEEDED entries")
    if artifacts.get("modules", {}).get("same_source") is not True:
        errors.append("module same-source evidence missing")
    if artifacts.get("overlay", {}).get("camera_autostart") is not False:
        errors.append("candidate artifact enables camera autostart")
    if artifacts.get("keyfix_sd_update") not in {
        "NOT_PERFORMED", "COMPLETED_BOARD_BOOT_PENDING",
        "COMPLETED_BOARD_BOOT_FAILED_HEALTHCHECK", "COMPLETED_BOARD_VALIDATED",
    }:
        errors.append("key-fix candidate artifact SD state is invalid")
    if artifacts.get("keyfix_sd_update") != "NOT_PERFORMED":
        keyfix_update = sd_update.get("keyfix_update", {})
        if keyfix_update.get("status") not in {
            "KEYFIX_SD_UPDATE_COMPLETED_BOARD_BOOT_PENDING",
            "KEYFIX_SD_UPDATE_COMPLETED_BOARD_BOOT_FAILED_HEALTHCHECK",
            "KEYFIX_SD_UPDATE_COMPLETED_BOARD_VALIDATED",
        }:
            errors.append("key-fix SD update evidence status mismatch")
        if keyfix_update.get("destination", {}).get("new_sha256") != artifacts.get("keyfix_sd_update_uinitrd_sha256"):
            errors.append("key-fix SD update hash does not match candidate artifact")

    if artifacts.get("keyfix3_sd_update") not in {
        "COMPLETED_BOARD_BOOT_PENDING", "COMPLETED_BOARD_VALIDATED",
    }:
        errors.append("keyfix3 SD update state is invalid")
    keyfix3_update = sd_update.get("keyfix3_update", {})
    if keyfix3_update.get("status") not in {
        "KEYFIX3_SD_UPDATE_COMPLETED_BOARD_BOOT_PENDING",
        "KEYFIX3_SD_UPDATE_COMPLETED_BOARD_BOOT_VALIDATED",
        "KEYFIX3_SD_UPDATE_COMPLETED_BOARD_VALIDATED",
    }:
        errors.append("keyfix3 SD update evidence status mismatch")
    if keyfix3_update.get("destination", {}).get("new_sha256") != artifacts.get("keyfix3_candidate", {}).get("uinitrd_lz4_sha256"):
        errors.append("keyfix3 SD update hash does not match candidate artifact")

    if validation.get("status") != "PASS":
        errors.append("validation evidence status is not PASS")
    if validation.get("checks", {}).get("task026_immutable") is not True:
        errors.append("Task 026 immutability gate is not recorded")

    if key_repair.get("status") != "REPAIR_STATIC_VALIDATION_PASS":
        errors.append("SSH host-key repair evidence status mismatch")
    if key_repair.get("fingerprint", {}).get("expected") != "SHA256:4Dz+I9j354/XGF2bCFAUTz1qrSGqGQhHJoVCEos3hi8":
        errors.append("expected host-key fingerprint mismatch")
    if key_repair.get("fingerprint", {}).get("current_matches_expected") is not True:
        errors.append("current host-key fingerprint did not match expected")
    if key_repair.get("fingerprint", {}).get("persistent_matches_current") is not True:
        errors.append("persistent/current host-key fingerprints did not match")
    if key_repair.get("private_key_sha256", {}).get("current_matches_persistent") is not True:
        errors.append("current/persistent private-key hashes did not match")
    if key_repair.get("running_image", {}).get("public_sidecar_present") is not False:
        errors.append("running-image sidecar observation is not retained")
    if key_repair.get("security", {}).get("candidate_mount_options") != "fmask=0177,dmask=0077":
        errors.append("secure candidate FAT mount options are missing")

    if keyfix_build.get("status") != "PASS_OFFLINE_KEYFIX_BUILDROOT":
        errors.append("key-fix Buildroot status mismatch")
    if keyfix_build.get("sd_update") != "NOT_PERFORMED":
        errors.append("key-fix SD update must not be performed")
    for name in ("rootfs_tar_gz", "rootfs_cpio_lz4", "uinitrd_lz4"):
        item = keyfix_build.get("artifacts", {}).get(name, {})
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            errors.append(f"missing or malformed key-fix hash for {name}")
        if item.get("size_bytes", 0) <= 0:
            errors.append(f"non-positive key-fix size for {name}")
    if keyfix_build.get("runtime", {}).get("aarch64_elf_count", 0) <= 0:
        errors.append("key-fix candidate has no AArch64 ELF evidence")
    if keyfix_build.get("runtime", {}).get("x86_64_elf_count") != 0:
        errors.append("key-fix candidate contains x86_64 ELF evidence")
    if keyfix_build.get("runtime", {}).get("missing_dt_needed") != []:
        errors.append("key-fix candidate has unresolved DT_NEEDED evidence")

    if keyfix3_build.get("status") != "PASS_OFFLINE_KEYFIX3_BUILDROOT":
        errors.append("keyfix3 Buildroot status mismatch")
    if keyfix3_build.get("sd_update") != "NOT_PERFORMED":
        errors.append("keyfix3 SD update must not be performed")
    for name in ("rootfs_tar_gz", "rootfs_cpio_lz4", "uinitrd_lz4"):
        item = keyfix3_build.get("artifacts", {}).get(name, {})
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            errors.append(f"missing or malformed keyfix3 hash for {name}")
        if item.get("size_bytes", 0) <= 0:
            errors.append(f"non-positive keyfix3 size for {name}")
    if keyfix3_build.get("runtime", {}).get("aarch64_elf_count", 0) <= 0:
        errors.append("keyfix3 candidate has no AArch64 ELF evidence")
    if keyfix3_build.get("runtime", {}).get("x86_64_elf_count") != 0:
        errors.append("keyfix3 candidate contains x86_64 ELF evidence")
    if keyfix3_build.get("runtime", {}).get("dt_needed_closure") != "INHERITED_FROM_IDENTICAL_KEYFIX2_TARGET_ASSETS":
        errors.append("keyfix3 DT_NEEDED closure provenance mismatch")
    if artifacts.get("keyfix3_candidate", {}).get("uinitrd_lz4_sha256") != keyfix3_build.get("artifacts", {}).get("uinitrd_lz4", {}).get("sha256"):
        errors.append("keyfix3 candidate hash does not match build evidence")

    if args.overlay.is_dir():
        actual = {p.relative_to(args.overlay).as_posix() for p in args.overlay.rglob("*") if p.is_file()}
        missing_local = sorted(REQUIRED_OVERLAY - actual)
        if missing_local:
            errors.append("local overlay missing: " + ", ".join(missing_local))
        key = args.overlay / "etc/edgeai/authorized_keys"
        if key.exists() and "PRIVATE KEY" in key.read_text(encoding="utf-8", errors="replace"):
            errors.append("local overlay contains private-key marker")

    if errors:
        print(json.dumps({"status": "FAIL", "task": "027", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task": "027", "task_state": task_state,
                      "deployment_readiness": deployment_readiness}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
