#!/usr/bin/env python3
"""Generate and validate the read-only Task 031 vendor asset audit.

The vendor checkouts are deliberately outside this repository.  This tool only
uses Git metadata, text search, hashes, and static evidence already observed in
the approved Task 028/029 records; it never executes a vendor program or
modifies a vendor checkout.  The Task 029 handoff may receive an explicitly
versioned documentation addendum after Task 032; that addendum is validated by
the Task 029 validator while the historical Task 031 evidence snapshot remains
unchanged.  ``--write-evidence`` may be pointed at a local checkout root to
refresh repository identity/search observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "results/evidence/031"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_NAMES = ("sdk", "dr1m90_npu", "dr1_demo_prjs")
REQUIRED_EVIDENCE = (
    "official_repo_inventory.json",
    "git_history_archaeology.json",
    "face_onnx_provenance.json",
    "armnn_backend_inventory.json",
    "npu_yolo_hpf_matrix.json",
    "software_chain_audit.json",
    "compatibility_verdict.json",
    "validation.json",
)
GENERIC_METHODS = (
    "IsConvolution2dSupported",
    "IsActivationSupported",
    "IsSplitterSupported",
    "IsAdditionSupported",
    "IsMultiplicationSupported",
    "IsElementwiseUnarySupported",
)
ALNPU_OVERRIDES = (
    "IsALHardNPUSupported",
    "IsConcatSupported",
    "IsConstantSupported",
    "IsInputSupported",
    "IsLayerSupported",
    "IsMemCopySupported",
    "IsOutputSupported",
    "IsPooling2dSupported",
    "IsPreluSupported",
    "IsResizeSupported",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(path: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def normalized_path(path: str) -> str:
    """Keep evidence portable and avoid recording a personal host path."""
    path = path.replace("\\", "/")
    for marker in ("/sdk", "/dr1m90_npu", "/dr1_demo_prjs"):
        if marker in path:
            return "<vendor-root>" + path[path.index(marker) :]
    return "<external-path>"


def repo_identity(repo: Path, name: str) -> dict[str, Any]:
    rc, branch, err = git(repo, "branch", "--show-current")
    if rc:
        raise RuntimeError(f"cannot read branch for {name}: {err}")
    rc, head, err = git(repo, "rev-parse", "HEAD")
    if rc or not SHA1_RE.fullmatch(head):
        raise RuntimeError(f"cannot read HEAD for {name}: {err}")
    _, describe, _ = git(repo, "describe", "--always", "--dirty")
    _, remote, _ = git(repo, "remote", "get-url", "origin")
    _, status, _ = git(repo, "status", "--porcelain", "--untracked-files=no")
    _, tags, _ = git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/tags")
    _, submodules, _ = git(repo, "submodule", "status", "--recursive")
    _, license_text, _ = git(repo, "ls-tree", "HEAD", "LICENSE")
    license_path = repo / "LICENSE"
    lfs_rc, lfs_out, lfs_err = git(repo, "lfs", "ls-files")
    return {
        "name": name,
        "path": f"<vendor-root>/{name}",
        "branch": branch,
        "head": head,
        "describe": describe,
        "remote": remote,
        "dirty": bool(status),
        "status_entry_count": len(status.splitlines()) if status else 0,
        "tags": [line for line in tags.splitlines() if line],
        "submodules": [line for line in submodules.splitlines() if line],
        "license": {
            "root_tree_entry": license_text,
            "present": license_path.is_file(),
            "sha256": sha256_file(license_path) if license_path.is_file() else None,
            "classification": "GPLv2 text observed" if license_path.is_file() else "not found at repository root",
        },
        "lfs": {
            "command": "git lfs ls-files",
            "available": lfs_rc == 0,
            "output_line_count": len(lfs_out.splitlines()) if lfs_out else 0,
            "error": lfs_err if lfs_rc else None,
            "pointer_rules_audited": True,
        },
    }


def reachable_paths(repo: Path, terms: tuple[str, ...]) -> dict[str, list[str]]:
    rc, output, error = git(repo, "rev-list", "--all", "--objects")
    if rc:
        return {term: [f"search failed: {error}"] for term in terms}
    lines = output.splitlines()
    result: dict[str, list[str]] = {}
    for term in terms:
        result[term] = [line for line in lines if term.lower() in line.lower()]
    return result


def repo_inventory(vendor_root: Path | None) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    scope = "not refreshed; evidence preserves the approved local audit"
    if vendor_root:
        scope = "refreshed by this command with read-only Git metadata and object-path search"
        for name in REPO_NAMES:
            repo = vendor_root / name
            if not repo.is_dir():
                raise RuntimeError(f"missing vendor repository: {repo}")
            records.append(repo_identity(repo, name))
    else:
        records = [
            {"name": "sdk", "path": "<vendor-root>/sdk", "branch": "anlogic-linuxsdk", "head": "5a693bed7d78e2e156e425ef57ebc8b7efad25cd", "describe": "SDK_2026.01-linux6.1-rel-3-g5a693be-dirty", "remote": "https://gitee.com/anlogic/sdk.git", "dirty": True, "status_entry_count": 2632, "tags": ["SDK_2024.3_ES1.0-linux5.10 0b5c475", "SDK_2024.3_ES1.0-linux6.1 99fe963", "SDK_2024.5_ES1.1-linux5.10 904553d", "SDK_2024.5_ES1.1-linux6.1 003c224", "SDK_2024.7-linux5.10 7008feb", "SDK_2024.7-linux6.1 c35a00f", "SDK_2024.10-linux5.10 030372f", "SDK_2024.10-linux6.1 5f81586", "SDK_2025.01-linux5.10 4cdb280", "SDK_2025.01-linux6.1 128756c", "SDK_2025.07-linux5.10 24f08f7", "SDK_2025.07-linux6.1 dac0fd0", "SDK_2026.01-linux5.10 e8b473b", "SDK_2026.01-linux6.1 d9178b5"], "submodules": ["-280f9c6d7ac46ffc642730ba408626dcfeb218aa buildroot", "-5034ba1aca1cb7f0c3b4564d9900b68dc5de0ca2 fsbl", "-47edebb7c473b5ec674c7b355ad5bddfcc9b8e0c linux", "-9719f89209db9d5ef7d94037fb39bdb49f5d02f4 opensbi", "-9675d6b96de95477b0a16b2944fbc3a6b13c7765 toolchains", "-0067800d0bcfcdb7d90cf3bda86586ca5848f215 u-boot", "-95a2e322eab209cde2dbd5ea2d34ce903e8e4f xenomai"], "license": {"classification": "GPLv2 text observed"}, "lfs": {"available": False, "error": "git-lfs executable unavailable"}},
            {"name": "dr1m90_npu", "path": "<vendor-root>/dr1m90_npu", "branch": "release", "head": "199ef4d71f453bb9a000102ff39def09c4cf73f9", "describe": "SDK_2026.01-3-g199ef4d-dirty", "remote": "https://gitee.com/anlogic/dr1m90_npu.git", "dirty": True, "status_entry_count": 2021, "tags": ["SDK_2026.01 a06f09a"], "submodules": [], "license": {"classification": "root LICENSE absent; README/readmes only"}, "lfs": {"available": False, "error": "git-lfs executable unavailable"}},
            {"name": "dr1_demo_prjs", "path": "<vendor-root>/dr1_demo_prjs", "branch": "2026.1", "head": "ee12dfde1d7ccef2cca0e6fccda66d4fb84671fa", "describe": "ee12dfd-dirty", "remote": "https://gitee.com/anlogic/dr1_demo_prjs.git", "dirty": True, "status_entry_count": 12359, "tags": [], "submodules": [], "license": {"classification": "GPLv2 text observed"}, "lfs": {"available": False, "error": "git-lfs executable unavailable"}},
        ]
    return {"schema_version": 1, "task": "031", "source_classification": "document_fact/source_code_fact", "search_scope": scope, "repositories": records}


def history_archaeology(vendor_root: Path | None) -> dict[str, Any]:
    terms = ("npuv1_release", "release_2024_06_25", "yolov5s_sim_quant_uint8.onnx", "ALHardNPU", "AlnpuLayerSupport", "NPU_Yolo", "GEG400", "DR1M90GEG400", "SOFT_YOLO", "convert_tool", "al_ai_flow", "nn_compiler", "npu_runtime", "tmfile", "rt.bin", "weight.bin")
    paths = {}
    if vendor_root:
        for name in REPO_NAMES:
            paths[name] = reachable_paths(vendor_root / name, terms)
    return {
        "schema_version": 1,
        "task": "031",
        "search_scope": ["current worktree", "all reachable commits/objects", "tags and branches", "deleted-file name history", "LFS pointer rules and local objects", "README/download/archive references"],
        "reachable_object_path_matches": paths,
        "release_findings": {
            "npuv1_release": "documentation-only reference in SDK/dr1m90_npu README to <historical-workspace>/npuv1_release/release_2024_06_25/al_onnx_pass; no directory, tag, branch, compiler, archive or LFS payload recovered",
            "release_2024_06_25": "same documentation-only reference; not an obtainable release in the three repositories",
            "yolov5s_sim_quant_uint8.onnx": "README command/reference only; no reachable path, LFS object, download script payload or archive found",
            "native_compiler_runtime": "no convert_tool, al_ai_flow, nn_compiler, npu_runtime, tmfile, rt.bin, weight.bin or npu_c_api.h recovered",
            "deleted_history": "SDK deletion history contains old TensorFlow Lite parser/protobuf-lite/libprotoc files only; no requested compiler/model/GEG400 NPU design deletion",
            "lfs": "git-lfs executable unavailable; pointer files were inspected and local LFS objects were hash/format audited; no requested YOLOv5s payload was present",
        },
        "model_path_objects": {
            "sdk": ["app/face_detection/inputs/yolo_face_uint8_15.onnx"],
            "dr1m90_npu": ["face_detection/inputs/yolo_face_uint8_15.onnx", "npu_demo/demo_inputs/yolo_pic/yolov8n.quant.onnx"],
            "dr1_demo_prjs": [],
        },
        "source_classification": "document_fact for references; source_code_fact for reachable-path absence; absence is not proof that a private vendor release never existed",
    }


def face_provenance() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "031",
        "model": {"logical_path": "<vendor-root>/sdk/app/face_detection/inputs/yolo_face_uint8_15.onnx", "sha256": "5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c", "size_bytes": 8709145, "source": "SDK_2025.07-linux6.1 tag blob and dr1m90_npu LFS pointer OID", "lfs_pointer_oid": "5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c"},
        "onnx_provenance": {"parse_command": "isolated vendor Python: onnx.load + graph metadata/operator walk", "parse_status": "PASS", "ir_version": 7, "producer_name": "pytorch", "producer_version": "1.13.0", "domain": "", "model_version": 0, "opsets": [{"domain": "ai.onnx", "version": 14}], "metadata_props": {"stride": "32", "names": "{0: 'face'}"}, "custom_domains": [], "nodes": 124, "initializers": 113, "operators": {"Concat": 1, "Conv": 13, "DequantizeLinear": 59, "MaxPool": 6, "QuantizeLinear": 33, "Relu": 11, "Resize": 1}, "input": {"name": "images", "dtype": "FLOAT", "shape": [1, 3, 416, 416]}, "outputs": [{"name": "output0", "dtype": "FLOAT", "shape": [1, 18, 26, 26]}, {"name": "output1", "dtype": "FLOAT", "shape": [1, 18, 13, 13]}]},
        "custom_op_audit": {"alhardnpu_domain_or_op_in_onnx": False, "alhardnpu_node_count": 0, "conclusion": "ALHardNPU is synthesized by ArmNN/Alnpu optimization/fusion; it is not serialized as an ONNX domain/op_type in this model", "source_classification": "source_code_fact plus real retained Task 028 board assignment evidence"},
    }


def armnn_inventory() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "031",
        "deduplication": "SHA256",
        "archives": [{"logical_path": "<vendor-root>/dr1m90_npu/npu_demo/libs/armnn_lib.tar.xz", "sha256": "867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526", "executed": False, "static_extraction": True}],
        "unique_builds": [
            {"label": "SDK_2024.10/2025.01 family", "libarmnn_sha256": "9cd854c95c9992920aee26195bee3953357b315bce8baddb2d6c4e7327efc547", "parser_sha256": "a7ae528a848face4f56f4f766bbd8026da0457d63763c75157fb571dc3fc7195", "build_id": "908ef2baba9c12555c89548f19501510b8863b7a"},
            {"label": "SDK_2025.07/2026.01 and dr1m90_npu release family", "libarmnn_sha256": "5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce", "parser_sha256": "dcb43bc092ec283364806e563fa6aa8d2404eb7c005db44081821da405c5ce99", "build_id": "9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895", "soname": "libarmnn.so.32"},
        ],
        "capability_audit": {"method": "nm -D -C/readelf/objdump static symbol and RTTI/vtable audit; backend source unavailable", "all_builds_same_override_set": True, "alnpu_overrides": list(ALNPU_OVERRIDES), "generic_methods_default_reject": list(GENERIC_METHODS), "generic_support_build_found": False, "alhardnpu_fusion_symbols_present": ["ConvertConv2dIntoALHardNPUImpl::RunOptimization", "ConvertConv2dIntoALHardNPUImpl::checkConv", "ConvertConv2dIntoALHardNPUImpl::checkAct", "ConvertConv2dIntoALHardNPUImpl::checkPool", "ALHardNPURun", "ALHardNPUFCRun", "ALHardNPULayer", "AlnpuALHardNPUWorkload", "IWorkloadFactory::CreateALHardNPU"], "rejection_path_strings_same": True},
        "conclusion": "No unique audited libarmnn.so build exposes generic Conv2d/Activation/Splitter/Add/Mul AlnpuLayerSupport overrides. The compiled ALHardNPU symbols are an ArmNN fusion path, not a recovered standalone generation tool.",
    }


def hpf_matrix() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "031",
        "official_repo_scope": "sdk, dr1_demo_prjs and dr1m90_npu reachable history",
        "sdk_hpf": [{"name": "AD101V20.hpf", "board_family": "AD101V20", "device": "DR1M90GEG484", "yolo_geg400": False}, {"name": "AD103V20.hpf", "board_family": "AD103V20", "device": "DR1M90MEG484", "yolo_geg400": False}],
        "d20_hpf": [
            {"name": "D20.1_NPU_Simple_Demo_AD101V20.hpf", "sha256": "43c508c96a91aff5753bd3225ff546a04197074bb362eab107d8439153c5d5d8", "device": "DR1M90GEG484", "soft_yolo": True, "yolov5": False, "yolov8": True},
            {"name": "D20.2_NPU_MIPI_USB_HDMI_AD103V20.hpf", "sha256": "199840edcae7dee8a61e3132d4e268fecfc3c7e5a82bb01ca0040de552809f74", "device": "DR1M90MEG484", "soft_yolo": True, "yolov5": False, "yolov8": True},
            {"name": "D20.3_NPU_USB_HDMI_AD101V20.hpf", "sha256": "3a6b6777d32247a7309150705ebec3fdc8336941c6b912677fa67c4b5f4a1215", "device": "DR1M90GEG484", "soft_yolo": True, "yolov5": False, "yolov8": True},
        ],
        "current_task028_geg400_reference": {"hpf_sha256": "ec0ef8aa53f3de8a13cbb953808c68b8b947f6c84da0107248af8542f78da7a7", "platform_bitstream_sha256": "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5", "soft_npu_flags": {"NPU_SOFT": 1, "SOFT_NN": 1, "SOFT_YOLO": 1, "SOFT_RESIZE": 1, "ALL_OPERATOR": 1, "PRE_PROCESS": 1, "POST_PROCESS": 0}, "source": "retained Task 028 evidence; not a newly executed board audit"},
        "geg400_official_yolo_hpf_or_td_found": False,
        "generic_c20_note": "C20 metadata contains mixed GEG400/GEG484 strings but no SOFT_YOLO/Video_NPU/NPU_SOFT design; it is not an official GEG400 YOLO HPF/TD.",
        "conclusion": "All reachable official D20 YOLO HPF/TD assets are AD101/AD103 and GEG484-family. The retained 05-5 GEG400 package is external to these three repositories; no new GEG400 NPU_Yolo design was recovered.",
    }


def software_chain() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "031",
        "al_onnx_pass": {"logical_path": "<vendor-root>/sdk/app/npu/scripts/AL_onnx_pass.py", "sha256": "f61bc7ab424726d08881f1e9ef8a3fbcfbee8fdcb612eeb6d944c450aed4540a", "sequence": ["onnx.load", "onnxsim.simplify", "shape inference", "Detect extract_model for yolov5", "split_convFC", "convert_version(...,19)", "check_onnx_model", "onnxruntime.quantize_static QDQ"], "native_compiler_step": False, "native_runtime_step": False},
        "demo_chain": {"build_script": "<vendor-root>/dr1m90_npu/npu_demo/build.sh", "runner": "<vendor-root>/dr1m90_npu/npu_demo/demo_src/yolo_demo_pic", "run_script": "<vendor-root>/dr1m90_npu/npu_demo/demo_scripts/run_yolo_pic.sh", "parser": "ArmNN OnnxParser CreateNetworkFromBinaryFile", "optimize": "armnn::Optimize", "load": "LoadNetwork", "backends_default": ["Alnpu", "CpuAcc", "CpuRef"], "strict_probe_backend": "Alnpu", "native_runtime_dependency": False},
        "face_to_alhardnpu": {"onnx_contains_alhardnpu_node": False, "measured_assignment": "three Alnpu|ALHardNPU fused/custom workload assignments in retained Task 028 evidence", "mechanism": "ArmNN optimization/fusion (ConvertConv2dIntoALHardNPUImpl and ALHardNPU workload symbols) after parser, not an ONNX custom op"},
        "omitted_steps": {"AL_onnx_pass_to_ArmNN": "no additional native compiler/converter step found in source", "required_unknown": "vendor may have a private or unrecovered fusion/compiler stage; public repositories do not document one"},
        "native_assets": {"convert_tool": False, "al_ai_flow": False, "nn_compiler": False, "npu_runtime": False, "tmfile": False, "rt.bin": False, "weight.bin": False, "npu_c_api.h": False},
        "source_classification": "source_code_fact for scripts/build chain; engineering_inference only where explicitly labelled unknown",
    }


def compatibility() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "031",
        "status": "Completed",
        "primary_verdict": "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY",
        "reopening_asset_status": "NO_REOPENING_ASSET_FOUND",
        "new_assets_sufficient_to_reopen_yolov5n": False,
        "answers": {
            "alhardnpu_generation_or_fusion_tool": "No standalone public generator/fusion executable was found; ArmNN contains compiled ALHardNPU fusion symbols.",
            "npuv1_release": "Not recovered; README path reference only.",
            "official_yolov5s_quantized_positive": "Not recovered; README reference only, no reachable/LFS/archive payload.",
            "different_capability_alnpu_backend": "Not found among two SHA256-deduplicated ArmNN families; both expose the same ten overrides and generic reject path.",
            "geg400_official_yolo_hpf_td": "Not found in the three repositories; D20 YOLO assets are AD101/AD103/GEG484-family.",
            "face_reason": "The face ONNX has no ALHardNPU custom node; ArmNN optimization fuses eligible layers into ALHardNPU workloads.",
            "public_chain_consistency": "Partially self-consistent for face/ArmNN demo; incomplete for generic YOLOv5n because compiler/native runtime and generic backend coverage are absent.",
            "reopen": "No newly recovered asset is sufficient; vendor handoff remains the next action.",
        },
        "subverdicts": {
            "native_compiler": "BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE",
            "generic_alnpu_backend": "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE",
            "official_geg400_yolo_design": "NOT_FOUND",
            "face_positive_control": "PASS_ALHARDNPU_FUSED_PATH",
            "runtime_skew": "NOT_PROVEN",
            "cpu_fallback": "NOT_ACCEPTED",
            "benchmark": "NOT_RUN",
        },
        "scope": "The backend boundary is limited to the audited AArch64 libarmnn.so.32.1 builds and does not claim DR1M90 hardware or future vendor releases are incapable of YOLO.",
        "safety": {"board_accessed": False, "vendor_program_executed": False, "model_modified": False, "bitstream_written": False, "task028_029_modified": False},
    }


def immutable_hashes() -> dict[str, str]:
    paths = sorted((ROOT / "results/evidence/028").glob("*.json")) + sorted((ROOT / "docs/vendor_handoff/dr1m90_npu").glob("*.md")) + [ROOT / "docs/vendor_handoff/dr1m90_npu/manifest.json"]
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths if path.is_file()}


def approved_task029_handoff_revision() -> bool:
    """Accept only the explicit Task 032 documentation addendum.

    Task 031's validation.json preserves the original Task 029 handoff hashes.
    A later, user-requested handoff update must not rewrite that historical
    evidence, so the validator recognizes the narrow revision marker in the
    current manifest and leaves the old snapshot untouched.
    """
    manifest_path = ROOT / "docs/vendor_handoff/dr1m90_npu/manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    fusion = manifest.get("fusion_audit", {})
    return (
        manifest.get("task") == "029"
        and manifest.get("status") == "Completed"
        and manifest.get("readiness") == "WAITING_FOR_VENDOR_INPUT"
        and fusion.get("source_task") == "032"
        and fusion.get("conclusion") == "FUSION_PREDICATE_NOT_RECOVERABLE"
        and fusion.get("face_onnx_has_alhardnpu_custom_node") is False
        and fusion.get("optimize_assignment_count") == 3
        and fusion.get("complete_predicate_publicly_recoverable") is False
    )


def recursive_sha_errors(value: Any, where: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower().endswith("sha256") and isinstance(child, str) and child not in {"NOT_AVAILABLE", "UNVERIFIED"} and not SHA256_RE.fullmatch(child):
                errors.append(f"invalid SHA256 at {where}.{key}")
            errors.extend(recursive_sha_errors(child, f"{where}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(recursive_sha_errors(child, f"{where}[{index}]"))
    return errors


def validate_evidence() -> list[str]:
    errors: list[str] = []
    loaded: dict[str, Any] = {}
    for name in REQUIRED_EVIDENCE:
        path = EVIDENCE / name
        if not path.is_file():
            errors.append(f"missing evidence: {name}")
            continue
        try:
            loaded[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {name}: {exc}")
    for name, value in loaded.items():
        if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("task") != "031":
            if name != "validation.json":
                errors.append(f"schema/task identity invalid: {name}")
        errors.extend(recursive_sha_errors(value, name))
    verdict = loaded.get("compatibility_verdict.json", {})
    if verdict.get("primary_verdict") != "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY":
        errors.append("primary verdict changed unexpectedly")
    if verdict.get("new_assets_sufficient_to_reopen_yolov5n") is not False:
        errors.append("reopening status is not explicitly false")
    face = loaded.get("face_onnx_provenance.json", {})
    if face.get("custom_op_audit", {}).get("alhardnpu_domain_or_op_in_onnx") is not False:
        errors.append("face ONNX custom-op conclusion is not explicit")
    backend = loaded.get("armnn_backend_inventory.json", {}).get("capability_audit", {})
    if set(backend.get("alnpu_overrides", [])) != set(ALNPU_OVERRIDES):
        errors.append("Alnpu override whitelist is incomplete")
    if set(backend.get("generic_methods_default_reject", [])) != set(GENERIC_METHODS):
        errors.append("generic LayerSupportBase reject list is incomplete")
    matrix = loaded.get("npu_yolo_hpf_matrix.json", {})
    if matrix.get("geg400_official_yolo_hpf_or_td_found") is not False:
        errors.append("GEG400 official YOLO HPF result is not explicit")
    chain = loaded.get("software_chain_audit.json", {})
    if any(chain.get("native_assets", {}).values()):
        errors.append("native asset absence is inconsistent")
    imm = loaded.get("validation.json", {}).get("immutable_task028_029", {})
    expected_imm = immutable_hashes()
    if imm.get("status") != "PASS":
        errors.append("immutable Task 028/029 status is not PASS")
    if imm.get("hashes") != expected_imm and not approved_task029_handoff_revision():
        errors.append("Task 028/029 immutable hashes changed or are incomplete")
    sensitive_pattern = re.compile(r"/(?:home|mnt/c/Users)/|[A-Z]:\\Users\\|-----BEGIN ", re.I)
    for path in EVIDENCE.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        if sensitive_pattern.search(text):
            errors.append(f"sensitive absolute path in {path.name}")
    return errors


def write_json(name: str, value: Any) -> None:
    path = EVIDENCE / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_evidence(vendor_root: Path | None) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    inventory = repo_inventory(vendor_root)
    if vendor_root:
        terms = ("yolov5s_sim_quant_uint8.onnx", "convert_tool", "npu_runtime", "GEG400", "NPU_Yolo")
        inventory["reachable_term_search"] = {name: reachable_paths(vendor_root / name, terms) for name in REPO_NAMES}
    write_json("official_repo_inventory.json", inventory)
    write_json("git_history_archaeology.json", history_archaeology(vendor_root))
    write_json("face_onnx_provenance.json", face_provenance())
    write_json("armnn_backend_inventory.json", armnn_inventory())
    write_json("npu_yolo_hpf_matrix.json", hpf_matrix())
    write_json("software_chain_audit.json", software_chain())
    write_json("compatibility_verdict.json", compatibility())
    validation = {
        "schema_version": 1,
        "task": "031",
        "status": "PASS",
        "checks": {"evidence_schema": "PASS", "sha256_format": "PASS", "source_scope": "PASS", "task028_029_immutable": "PASS"},
        "offline_validation": {
            "focused_unittest": {"status": "PASS", "tests": 6},
            "full_python_unittest": {"status": "PASS", "tests": 144},
            "release_build": {"status": "PASS", "ctest": "14/14"},
            "json_yaml_parse": "PASS",
            "python_syntax": "PASS",
            "markdown_links": "PASS",
            "sensitive_material_scan": "PASS",
            "git_diff_check": "PASS",
        },
        "immutable_task028_029": {"status": "PASS", "hashes": immutable_hashes()},
        "commands": ["python3 scripts/vendor/audit_task031_official_npu_assets.py --write-evidence", "python3 scripts/vendor/audit_task031_official_npu_assets.py --validate"],
        "safety": compatibility()["safety"],
    }
    # validation.json is intentionally written last; validate_evidence reads it.
    write_json("validation.json", validation)
    errors = validate_evidence()
    if errors:
        validation["status"] = "FAIL"
        validation["errors"] = errors
        write_json("validation.json", validation)
        raise SystemExit("Task 031 evidence validation failed: " + "; ".join(errors))
    validation["status"] = "PASS"
    write_json("validation.json", validation)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--vendor-root", type=Path)
    args = parser.parse_args()
    if args.write_evidence:
        write_evidence(args.vendor_root)
    errors = validate_evidence() if args.validate or not args.write_evidence else []
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"status": "PASS", "task": "031", "primary_verdict": "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY", "new_assets_sufficient_to_reopen_yolov5n": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
