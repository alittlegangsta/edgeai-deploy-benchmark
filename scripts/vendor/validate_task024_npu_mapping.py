#!/usr/bin/env python3
"""Offline consistency checks for the read-only Task 024 board mapping."""
import argparse
import hashlib
import json
import re
from pathlib import Path

SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRIMARY = {"BLOCKED_ACTIVE_BITSTREAM_IDENTITY", "READY_FOR_CONTROLLED_DEPLOYMENT_APPROVAL"}
REQUIRED = (
    "board_boot_chain.json",
    "board_device_tree.json",
    "board_kernel_provenance.json",
    "board_mapping_matrix.json",
    "controlled_deployment_plan.json",
    "official_repository_inventory.json",
    "official_repository_dependency_matrix.json",
    "active_boot_static_parse.json",
    "active_device_tree_current.json",
    "kernel_modversions_symbol_audit.json",
    "validation.json",
)


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def walk_sha256(value, location="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            if "sha256" in key.lower() and child is not None:
                yield location + "." + key, child
            yield from walk_sha256(child, location + "." + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_sha256(child, "%s[%d]" % (location, index))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    errors = []
    docs = {}
    for name in REQUIRED:
        path = args.evidence_dir / name
        if not path.is_file():
            errors.append("missing evidence: " + name)
            continue
        try:
            docs[name] = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append("invalid JSON %s: %s" % (name, type(exc).__name__))

    boot = docs.get("board_boot_chain.json", {})
    verdict = boot.get("verdict", {})
    if verdict.get("primary") not in PRIMARY:
        errors.append("invalid primary verdict")
    access = boot.get("access", {}).get("current_board", {})
    if access.get("reachable") is not True or access.get("current_observation_valid") is not True:
        errors.append("current board read-only observation is not confirmed")
    if boot.get("safety", {}).get("writes_performed") is not False:
        errors.append("mapping evidence claims a write")
    if boot.get("active_boot_chain", {}).get("status") != "CURRENT_READ_CONFIRMED":
        errors.append("active boot chain is not marked current-read-confirmed")
    if boot.get("active_boot_chain", {}).get("active_bitstream_identity", "").startswith("VERIFIED"):
        errors.append("opaque active bitstream was promoted without payload evidence")

    dt = docs.get("board_device_tree.json", {})
    if dt.get("candidate_status") != "CANDIDATE_NOT_ACTIVE":
        errors.append("candidate DT assets must not be marked active")
    current = dt.get("current_observation", {})
    if current.get("classification") != "real_device_observation":
        errors.append("current DT observation classification missing")
    if current.get("hard_npu", {}).get("driver_bound") is not False:
        errors.append("current hard_npu binding must remain unbound")
    if current.get("cma", {}).get("size_bytes") != 134217728:
        errors.append("current CMA size is not recorded as 128 MiB")
    if dt.get("comparison", {}).get("active_current_read_available") is not True:
        errors.append("current DT read is not confirmed")

    kernel = docs.get("board_kernel_provenance.json", {})
    if kernel.get("board_observed_abi", {}).get("kernel") != "6.1.111-rt42":
        errors.append("board kernel ABI mismatch")
    if kernel.get("vm_provenance", {}).get("defconfig_symbols", {}).get("CONFIG_MODVERSIONS") != "not set in candidate defconfig; active board value unknown":
        errors.append("CONFIG_MODVERSIONS boundary is missing")
    modules = kernel.get("driver_static_compatibility", {}).get("modules", [])
    if len(modules) != 3 or any(module.get("loadability") != "NOT_PROVEN" for module in modules):
        errors.append("driver static evidence incorrectly promotes loadability")

    matrix = docs.get("board_mapping_matrix.json", {})
    rows = matrix.get("rows", [])
    if len(rows) < 12:
        errors.append("mapping matrix is incomplete")
    if any(row.get("controlled_deployment") is True for row in rows):
        errors.append("unapproved mapping marked deployment-ready")
    if matrix.get("overall", {}).get("primary_verdict") != verdict.get("primary"):
        errors.append("matrix and boot verdict disagree")

    plan = docs.get("controlled_deployment_plan.json", {})
    if plan.get("executed") is not False or plan.get("approval") != "NOT_GRANTED":
        errors.append("deployment plan claims execution or approval")
    if plan.get("recommended_media") != "isolated SD card first; untouched eMMC fallback":
        errors.append("rollback media policy changed")
    if plan.get("safety", {}).get("vendor_demo_run") is not False:
        errors.append("vendor demo execution is not explicitly false")

    inventory = docs.get("official_repository_inventory.json", {})
    names = {repo.get("name") for repo in inventory.get("repositories", [])}
    if names != {"dr1m90_npu", "toolchains", "boardimages", "sdk"}:
        errors.append("official repository inventory is incomplete")
    if any(repo.get("dirty_file_count", 0) for repo in inventory.get("repositories", [])) is not True:
        errors.append("repository dirty-state audit missing")

    boot_static = docs.get("active_boot_static_parse.json", {})
    if boot_static.get("conclusion", {}).get("active_bitstream_identity") != "BLOCKED_ACTIVE_BITSTREAM_IDENTITY":
        errors.append("active boot static parse does not preserve bitstream blocker")
    if boot_static.get("conclusion", {}).get("writes_performed") is not False:
        errors.append("active boot static parse claims a write")

    mod_audit = docs.get("kernel_modversions_symbol_audit.json", {})
    if mod_audit.get("board_kernel", {}).get("config_modversions") != "UNKNOWN_FOR_ACTIVE_KERNEL":
        errors.append("active CONFIG_MODVERSIONS must remain unknown")
    if mod_audit.get("symbol_comparison", {}).get("symbol_crc_compatibility") != "UNPROVEN":
        errors.append("symbol CRC status incorrectly promoted")

    validation = docs.get("validation.json", {})
    if validation.get("primary_verdict") != verdict.get("primary"):
        errors.append("validation and boot verdict disagree")
    if validation.get("safety", {}).get("board_modified") is not False:
        errors.append("validation claims board modification")

    for name, doc in docs.items():
        for location, digest in walk_sha256(doc, name):
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append("invalid SHA256 at %s" % location)

    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task": "024", "evidence_files": len(docs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
