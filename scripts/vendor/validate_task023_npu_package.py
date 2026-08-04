#!/usr/bin/env python3
"""Offline consistency checks for Task 023 package-intake evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERDICTS = {
    "READY_FOR_CONTROLLED_BUILD",
    "READY_FOR_DEPLOYMENT_APPROVAL",
    "BLOCKED_BOARD_MISMATCH",
    "BLOCKED_KERNEL_MISMATCH",
    "BLOCKED_RUNTIME_INCOMPLETE",
    "BLOCKED_MODEL_ASSET_INCOMPLETE",
    "BLOCKED_BUILD_REPRODUCIBILITY",
    "BLOCKED_PROVENANCE_OR_LICENSE",
    "BLOCKED_TOOLCHAIN",
    "BLOCKED_BOARD_HARDWARE_MAPPING",
    "BLOCKED_NATIVE_RUNTIME_ASSETS",
    "BLOCKED_ARMNN_BACKEND_INCOMPLETE",
    "BLOCKED_PREBUILT_DEMO_DEPLOYMENT",
    "BLOCKED_MODULE_SYMBOL_CRC",
    "BLOCKED_PACKAGE_RELEASE_IDENTITY",
}
REQUIRED = (
    "npu_package_inventory.json",
    "npu_wiki_source_map.json",
    "npu_project_dependency_graph.json",
    "npu_driver_build_analysis.json",
    "npu_runtime_demo_analysis.json",
    "npu_static_compatibility.json",
    "npu_package_verdict.json",
)


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk_strings(key)
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)


def validate(evidence_dir: Path) -> List[str]:
    errors: List[str] = []
    docs: Dict[str, Any] = {}
    for name in REQUIRED:
        path = evidence_dir / name
        if not path.is_file():
            errors.append(f"missing required evidence: {name}")
            continue
        try:
            docs[name] = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {name}: {exc}")

    verdict = docs.get("npu_package_verdict.json", {})
    primary = verdict.get("primary_verdict")
    if primary not in VERDICTS:
        errors.append(f"invalid primary_verdict: {primary!r}")
    if verdict.get("task_status") not in {"In Progress", "Completed"}:
        errors.append("package intake task_status must be In Progress or Completed")
    if verdict.get("automated_intake") != "COMPLETE":
        errors.append("automated_intake must be COMPLETE")
    if verdict.get("task_status") == "Completed":
        if verdict.get("automated_audit") != "COMPLETE":
            errors.append("completed intake must record automated_audit COMPLETE")
        if verdict.get("audit_review") != "PASS" or verdict.get("audit_review_source") != "user":
            errors.append("completed intake must record user audit review PASS")
        if verdict.get("candidate_approved") is not True:
            errors.append("completed intake must record candidate_approved true")
    if not verdict.get("secondary_blockers"):
        errors.append("blocked intake must list secondary blockers")
    build = verdict.get("build", {})
    build_attempt = evidence_dir / "npu_build_attempt.json"
    if build_attempt.is_file():
        try:
            build_doc = load(build_attempt)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON npu_build_attempt.json: {exc}")
            build_doc = {}
        if build.get("attempted") is not True:
            errors.append("verdict build attempted flag must be true when build evidence exists")
        if build.get("status") not in {"PASS_WITH_LIMITATIONS", "PASS"}:
            errors.append("verdict build status must describe the recorded isolated build")
        if build.get("npu_build_attempt_evidence") != "results/evidence/023/npu_build_attempt.json":
            errors.append("verdict must reference npu_build_attempt.json")
        if not build_doc.get("attempts"):
            errors.append("npu_build_attempt.json must contain at least one attempt")
        policy = build_doc.get("policy", {})
        for field in ("vendor_programs_executed", "kernel_modules_loaded", "board_accessed", "bitstream_written", "sdk_sources_modified"):
            if policy.get(field) is not False:
                errors.append(f"build policy field {field} must be false")
    elif build.get("attempted") is not False or build.get("status") != "NOT_ATTEMPTED":
        errors.append("build evidence must explicitly state no build was attempted when no attempt file exists")
    one_shot = verdict.get("official_one_shot", {})
    if one_shot.get("executed") is not False or one_shot.get("status") != "NOT_EXECUTED":
        errors.append("official one-shot must remain not executed")
    safety = verdict.get("safety", {})
    for field in ("vendor_binaries_executed", "kernel_modules_loaded", "bitstreams_written", "board_modified", "project_model_converted"):
        if safety.get(field) is not False:
            errors.append(f"safety field {field} must be false")

    inventory = docs.get("npu_package_inventory.json", {})
    roots = inventory.get("roots", [])
    if not roots or inventory.get("root_summary", {}).get("suffix_counts_selected", {}).get("hpf") != 15:
        errors.append("inventory root/count facts are incomplete")
    selected = inventory.get("selected_files", [])
    if not selected:
        errors.append("inventory has no selected files")
    for item in selected:
        digest = item.get("sha256")
        if digest is not None and not SHA256_RE.fullmatch(digest):
            errors.append(f"invalid selected SHA256: {item.get('relative_path')}")
        if item.get("size_bytes") == 0:
            errors.append(f"zero selected size is not allowed: {item.get('relative_path')}")

    driver = docs.get("npu_driver_build_analysis.json", {})
    drivers = driver.get("drivers", [])
    if {item.get("name") for item in drivers} != {"hard_npu", "soft_npu", "cma_mem"}:
        errors.append("driver analysis must cover hard_npu, soft_npu and cma_mem")
    for item in drivers:
        if item.get("built_in_or_module") != "module":
            errors.append(f"driver is not recorded as obj-m module: {item.get('name')}")
        if "6.1.111-rt42" not in item.get("vermagic", ""):
            errors.append(f"module vermagic does not record board kernel: {item.get('name')}")

    runtime = docs.get("npu_runtime_demo_analysis.json", {})
    if runtime.get("runtime_status", {}).get("standalone_apug_npu_runtime") != "not located":
        errors.append("standalone APUG runtime status must remain not located")
    static = docs.get("npu_static_compatibility.json", {})
    if static.get("negative_findings", {}).get("vendor_elf_execution") is not False:
        errors.append("static compatibility must record vendor ELF execution as false")

    readiness = verdict.get("path_readiness", {})
    required_readiness = {
        "native_runtime_path_readiness",
        "armnn_demo_path_readiness",
        "driver_static_compatibility",
        "board_hardware_mapping",
        "source_build_reproducibility",
        "prebuilt_demo_deployment_readiness",
    }
    if set(readiness) != required_readiness:
        errors.append("path_readiness must contain the six required path status fields")
    if readiness.get("native_runtime_path_readiness") == "PASS":
        errors.append("native runtime cannot be marked PASS without the APUG runtime package")
    if readiness.get("prebuilt_demo_deployment_readiness") in {"PASS", "READY_FOR_DEPLOYMENT_APPROVAL"}:
        errors.append("prebuilt demo cannot be deployment-ready while board mapping is unresolved")
    if verdict.get("primary_verdict") == "BLOCKED_BOARD_HARDWARE_MAPPING" and readiness.get("board_hardware_mapping") != "BLOCKED_BOARD_HARDWARE_MAPPING":
        errors.append("board mapping readiness must agree with primary verdict")

    # The evidence is allowed to discuss the word token, but must not contain
    # obvious credentials or shell-private material.
    forbidden = ("BEGIN OPENSSH PRIVATE KEY", "Authorization:", "Cookie:", "password=")
    joined = "\n".join(walk_strings(docs))
    for marker in forbidden:
        if marker in joined:
            errors.append(f"sensitive marker found in evidence: {marker}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path("results/evidence/023"))
    args = parser.parse_args()
    errors = validate(args.evidence_dir)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "required_files": len(REQUIRED), "build_attempt": "RECORDED_ISOLATED_BUILD", "one_shot": "NOT_EXECUTED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
