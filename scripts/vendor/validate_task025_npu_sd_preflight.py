#!/usr/bin/env python3
"""Offline consistency checks for the Task 025 SD-image preflight."""

import argparse
import json
import re
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = (
    "npu_sd_source_inventory.json",
    "npu_sd_build_chain.json",
    "npu_sd_build_attempt.json",
    "npu_sd_armnn_rootfs_dependency.json",
    "npu_sd_candidate_identity.json",
    "npu_sd_deployment_plan.json",
    "npu_sd_image_verdict.json",
    "npu_demo_directory_screening.json",
    "milianke_npu_demo_audit.json",
    "npu_demo_archive_inventory.json",
    "npu_mlk_linux_bsp_audit.json",
    "npu_hpf_bitstream_provenance.json",
    "npu_boardconfig_recovery_assessment.json",
    "uisrc_package_inventory.json",
    "npu_vm_uisrc_environment_inventory.json",
    "npu_vm_historical_mlk_bsp_assessment.json",
    "npu_vm_05_5_provenance_comparison.json",
    "npu_pdf_workflow_extraction.json",
    "npu_pdf_input_closure.json",
    "npu_uisrc_build_script_safety.json",
    "npu_pdf_isolated_reproduction.json",
    "npu_pdf_candidate_artifact_validation.json",
    "npu_buildroot_config_identity.json",
    "npu_buildroot_dl_manifest.json",
    "npu_formal_rootfs_build.json",
    "npu_formal_rootfs_runtime_closure.json",
    "npu_final_candidate_artifact_manifest.json",
)
ALLOWED_VERDICTS = {
    "READY_FOR_SD_WRITE_APPROVAL",
    "BLOCKED_MLK_BOARD_PROJECT_IDENTITY",
    "BLOCKED_CLEAN_SOURCE_RECONSTRUCTION",
    "BLOCKED_CLEAN_BUILD_REPRODUCIBILITY",
    "BLOCKED_BOOT_ASSET_GENERATION",
    "BLOCKED_KERNEL_DRIVER_COMPATIBILITY",
    "BLOCKED_ARMNN_RUNTIME_PACKAGE",
    "BLOCKED_LICENSE_OR_PROVENANCE",
    "BLOCKED_CANDIDATE_IMAGE_BUILD",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_hashes(value, location="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            if "sha256" in key.lower() and isinstance(child, str):
                yield location + "." + key, child
            yield from walk_hashes(child, location + "." + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_hashes(child, "%s[%d]" % (location, index))


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

    verdict = docs.get("npu_sd_image_verdict.json", {})
    primary = verdict.get("primary_verdict")
    if primary not in ALLOWED_VERDICTS:
        errors.append("invalid primary verdict")
    if verdict.get("task_status") != "Completed":
        errors.append("finalized task must be Completed")
    if verdict.get("candidate_approved") is not True:
        errors.append("candidate approval must be true after audit approval")
    if verdict.get("deployment_approval") != "PENDING":
        errors.append("deployment approval must remain pending")
    if verdict.get("candidate_sd_image") != "NOT_PARTITIONED_IMAGE":
        errors.append("candidate SD image must remain unpartitioned")
    if verdict.get("candidate_approval_semantics") != (
        "static-audit approval only; does not authorize formatting, partitioning or writing real media"
    ):
        errors.append("candidate approval semantics must remain explicit")
    if verdict.get("commit_created") is not True:
        errors.append("final local commit must be recorded")
    identity_split = verdict.get("identity_split", {})
    if identity_split.get("current_emmc_identity") != "KNOWN_FROM_TASK024_READ_ONLY_NOT_A_CANDIDATE_BLOCKER":
        errors.append("current eMMC identity must remain separate from candidate blocker")
    if identity_split.get("candidate_boot_chain_reproducibility") != "PASS_BOOT_AND_FORMAL_ROOTFS_FILE_SET_NOT_PARTITIONED":
        errors.append("candidate boot-chain identity split mismatch")
    if identity_split.get("candidate_armnn_runtime_closure") != "PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY":
        errors.append("candidate Arm NN closure split mismatch")
    if verdict.get("path_readiness", {}).get("candidate_sd_generation_readiness") != "READY_FOR_SD_WRITE_APPROVAL":
        errors.append("candidate SD generation readiness mismatch")
    safety = verdict.get("safety", {})
    for key in ("sd_written", "emmc_modified", "modules_loaded", "fpga_written", "vendor_npu_executed"):
        if safety.get(key) is not False:
            errors.append("safety.%s must be false" % key)

    attempt = docs.get("npu_sd_build_attempt.json", {})
    generated = attempt.get("generated_candidate", {})
    if generated.get("sd_image") is not False:
        errors.append("generated SD image must remain false")
    if generated.get("complete_file_set") is not True:
        errors.append("formal candidate file set must be recorded complete")
    if generated.get("partial_isolated_file_set") is not True:
        errors.append("partial isolated candidate file set must be recorded")
    if generated.get("boot_artifacts_generated") is not True:
        errors.append("isolated boot artifact generation must be recorded")
    if generated.get("rootfs_artifact_derived_not_buildroot_generated") is not False:
        errors.append("formal rootfs must not be classified as derived-only")
    if generated.get("formal_buildroot_rootfs_generated") is not True:
        errors.append("formal Buildroot rootfs generation must be recorded")
    app = next((item for item in attempt.get("attempts", []) if item.get("kind") == "official_app_npu_build"), {})
    if app.get("status") != "PASS_TARGETS_PARTIAL_PACKAGE":
        errors.append("Arm NN app build must retain partial-package status")
    if not app.get("packaging_errors"):
        errors.append("missing packaging errors were not retained")
    armnn = docs.get("npu_sd_armnn_rootfs_dependency.json", {})
    closure = armnn.get("closure", {})
    if armnn.get("status") != "PASS_STATIC_NON_SYSTEM_CLOSURE_NOT_DEPLOYMENT_READY":
        errors.append("Arm NN dependency closure status mismatch")
    if closure.get("non_system_needed_missing_from_candidate_lib_dir") != []:
        errors.append("Arm NN package has unresolved non-system DT_NEEDED entries")
    if armnn.get("libprotoc_check", {}).get("dt_needed_in_yolo_armnn_parser_protobuf_closure") is not False:
        errors.append("libprotoc classification must remain not DT_NEEDED")
    candidate = docs.get("npu_sd_candidate_identity.json", {})
    if candidate.get("candidate_sd_identity", {}).get("official_sdk_board_config_inventory", {}).get("mlk_board_config_found") is not False:
        errors.append("MLK BoardConfig absence is not recorded")
    if candidate.get("candidate_boot_chain_reproducibility", {}).get("status") != "PASS_BOOT_AND_FORMAL_ROOTFS_FILE_SET_NOT_PARTITIONED":
        errors.append("candidate boot-chain status mismatch")
    if candidate.get("candidate_kernel_module_compatibility", {}).get("status") != "PASS_SAME_SOURCE_STATIC_COMPATIBILITY":
        errors.append("candidate module status mismatch")
    if candidate.get("candidate_armnn_runtime_closure", {}).get("status") != "PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY":
        errors.append("candidate formal Arm NN closure status mismatch")
    pdf_workflow = docs.get("npu_pdf_workflow_extraction.json", {})
    pdf_document = pdf_workflow.get("document", {})
    if pdf_document.get("status") != "NOT_ACCESSIBLE_IN_SESSION":
        errors.append("PDF accessibility status must remain explicit")
    if pdf_document.get("source_type") != "user_provided_workflow_summary":
        errors.append("PDF source type must distinguish user summary from extraction")
    workflow_safety = pdf_workflow.get("source_checks", {})
    for key in ("all_mutations_confined_to_isolated_vm_workspace", "board_accessed", "media_written", "npu_executed"):
        expected = False if key != "all_mutations_confined_to_isolated_vm_workspace" else True
        if workflow_safety.get(key) is not expected:
            errors.append("PDF workflow source_checks.%s mismatch" % key)
    input_closure = docs.get("npu_pdf_input_closure.json", {})
    inputs = {item.get("role"): item for item in input_closure.get("inputs", [])}
    for role in ("FSBL", "platform bitstream"):
        if inputs.get(role, {}).get("available") is not True:
            errors.append("PDF input closure missing available %s" % role)
    if inputs.get("platform bitstream", {}).get("sha256") != "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5":
        errors.append("PDF tutorial platform bitstream identity mismatch")
    if inputs.get("platform bitstream", {}).get("matches_known_best_result_bit") is not False:
        errors.append("PDF platform/best-result bit distinction missing")
    script_safety = docs.get("npu_uisrc_build_script_safety.json", {})
    scripts = {item.get("name"): item for item in script_safety.get("scripts", [])}
    for name in ("scripts/rootfs/buildroot/make_parted.sh", "scripts/rootfs/buildroot/deploy_image.sh"):
        if scripts.get(name, {}).get("classification") != "UNSAFE_DESTRUCTIVE":
            errors.append("destructive script safety classification missing: " + name)
        if scripts.get(name, {}).get("executed") is not False:
            errors.append("destructive script must not be executed: " + name)
    if scripts.get("scripts/rootfs/buildroot/create_dr1m_image.sh", {}).get("exit_code") != 0:
        errors.append("isolated boot image script did not pass")
    reproduction = docs.get("npu_pdf_isolated_reproduction.json", {})
    if reproduction.get("injection", {}).get("move_files_exit_code") != 0:
        errors.append("PDF injection move_files did not pass")
    if reproduction.get("kernel", {}).get("repair_3", {}).get("status") != "PASS":
        errors.append("same-source kernel repair-3 result missing")
    if reproduction.get("uboot", {}).get("build_status") != "PASS":
        errors.append("same-source U-Boot build result missing")
    if reproduction.get("image", {}).get("create_dr1m_image_exit_code") != 0:
        errors.append("isolated create_dr1m_image result missing")
    if reproduction.get("rootfs", {}).get("make_rootfs_script") != "NOT_RUN":
        errors.append("Buildroot rootfs script execution must remain explicit")
    if reproduction.get("rootfs", {}).get("derived_candidate_status") != "DERIVED_FROM_EXISTING_GENERIC_ROOTFS_WITH_ISOLATED_OVERLAY":
        errors.append("derived rootfs classification mismatch")
    reproduction_safety = reproduction.get("safety", {})
    for key in ("board_accessed", "media_written", "modules_loaded", "fpga_written", "vendor_npu_executed", "project_yolov5n_converted"):
        if reproduction_safety.get(key) is not False:
            errors.append("PDF reproduction safety.%s must be false" % key)
    artifact = docs.get("npu_pdf_candidate_artifact_validation.json", {})
    if artifact.get("status") != "PASS_PARTIAL_CANDIDATE_NOT_SD_READY":
        errors.append("PDF candidate artifact status mismatch")
    artifacts = artifact.get("artifacts", {})
    if artifacts.get("BOOT.bin", {}).get("sha256") != "e25f98e00a68ea76f9e96736ba88fb7c169e2f8b769d60af55e3e69639880016":
        errors.append("PDF candidate BOOT.bin identity mismatch")
    if artifacts.get("system.dtb", {}).get("semantic_checks", {}).get("hard_npu", {}).get("compatible") != "anlogic,hard_npu":
        errors.append("candidate DTB HardNPU semantic check missing")
    if artifacts.get("system.dtb", {}).get("semantic_checks", {}).get("soft_npu", {}).get("compatible") != "anlogic,soft_npu":
        errors.append("candidate DTB SoftNPU semantic check missing")
    if artifacts.get("system.dtb", {}).get("semantic_checks", {}).get("cma", {}).get("linux_cma_default") is not True:
        errors.append("candidate DTB CMA semantic check missing")
    for name in ("hard_npu.ko", "soft_npu.ko", "cma_mem.ko"):
        if artifacts.get(name, {}).get("same_source_module_symvers_missing_symbols") != 0:
            errors.append("same-source module symbol check failed: " + name)
    if artifacts.get("rootfs-candidate.tar.gz", {}).get("buildroot_generated") is not False:
        errors.append("candidate rootfs must not be presented as Buildroot output")
    if artifact.get("runtime_closure", {}).get("non_system_dt_needed_missing_in_full_candidate_rootfs") != []:
        errors.append("candidate rootfs static runtime closure is incomplete")
    if artifact.get("readiness", {}).get("complete_sd_file_set") is not False:
        errors.append("candidate artifact set must remain incomplete")
    if artifact.get("readiness", {}).get("rootfs") != "BLOCKED_NOT_BUILT_BY_BUILDROOT":
        errors.append("candidate rootfs Buildroot blocker mismatch")
    if verdict.get("pdf_workflow_increment", {}).get("status") != "FORMAL_BUILDROOT_ROOTFS_PASS_COMPLETE_FILE_SET_READY":
        errors.append("verdict PDF workflow increment status mismatch")

    buildroot_config = docs.get("npu_buildroot_config_identity.json", {})
    if buildroot_config.get("status") not in (None, "PASS_FROZEN_BUILDROOT_CONFIG"):
        errors.append("Buildroot config identity status mismatch")
    config = buildroot_config.get("config", {})
    if config.get("sha256") != "1c09289906374a04eeff6fe44c20751f637f174fb916021c991b99016287c84c":
        errors.append("Buildroot .config identity mismatch")
    if config.get("defconfig_sha256") != "bbc691bdca2852786e73d6011c3b7cfbaa191e46aa09b21f9f23ef7daeb30526":
        errors.append("Buildroot defconfig identity mismatch")
    if config.get("target_architecture") != "aarch64" or config.get("toolchain", {}).get("target_glibc") != "2.25":
        errors.append("Buildroot target/toolchain identity mismatch")
    dl = docs.get("npu_buildroot_dl_manifest.json", {})
    manifest = dl.get("manifest", {})
    if manifest.get("file_count") != 141 or manifest.get("archive_count") != 70 or manifest.get("total_bytes") != 268798198:
        errors.append("Buildroot download manifest count/size mismatch")
    if dl.get("offline_recheck", {}).get("exit_code") != 0 or dl.get("offline_recheck", {}).get("new_download_requests") != 0:
        errors.append("Buildroot offline cache recheck failed")
    formal = docs.get("npu_formal_rootfs_build.json", {})
    if formal.get("status") != "PASS_FORMAL_BUILDROOT_ROOTFS" or formal.get("build", {}).get("exit_code") != 0:
        errors.append("formal Buildroot rootfs build status mismatch")
    if formal.get("build", {}).get("rootfs_archive", {}).get("sha256") != "ae64bbd125a47f54df445a084485466336f1df60f5137ad61b44b8eb22c64f39":
        errors.append("formal rootfs archive identity mismatch")
    closure_formal = docs.get("npu_formal_rootfs_runtime_closure.json", {})
    if closure_formal.get("status") != "PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY":
        errors.append("formal rootfs closure status mismatch")
    rootfs = closure_formal.get("rootfs", {})
    if rootfs.get("elf_count") != 353 or rootfs.get("aarch64_elf_count") != 353 or rootfs.get("x86_64_elf_count") != 0:
        errors.append("formal rootfs architecture counts mismatch")
    if rootfs.get("missing_dt_needed") != [] or rootfs.get("target_execution") is not False:
        errors.append("formal rootfs dynamic closure or execution guard mismatch")
    final_candidate = docs.get("npu_final_candidate_artifact_manifest.json", {})
    if final_candidate.get("status") != "READY_FOR_SD_WRITE_APPROVAL":
        errors.append("final candidate status mismatch")
    if final_candidate.get("candidate_approved") is not True:
        errors.append("final candidate approval must be true")
    if final_candidate.get("candidate_sd_image") != "NOT_PARTITIONED_IMAGE":
        errors.append("final candidate must identify a non-partitioned image")
    final_readiness = final_candidate.get("readiness", {})
    if final_readiness.get("complete_file_set") is not True or final_readiness.get("partitioned_sd_image") is not False or final_readiness.get("sd_write") != "NOT_PERFORMED":
        errors.append("final candidate readiness/safety mismatch")
    if final_candidate.get("checksum_manifest", {}).get("entries") != 13:
        errors.append("final candidate checksum entry count mismatch")
    repos = docs.get("npu_sd_source_inventory.json", {}).get("official_repositories", [])
    names = {item.get("name") for item in repos}
    if names != {"sdk", "dr1m90_npu", "toolchains", "boardimages"}:
        errors.append("official repository set is incomplete")
    sdk = next((item for item in repos if item.get("name") == "sdk"), {})
    if sdk.get("selected_release", {}).get("tag") != "SDK_2025.07-linux6.1":
        errors.append("SDK release line mismatch")
    archive_note = sdk.get("selected_release", {}).get("archive_note", "")
    if "submodule" not in archive_note or "contents" not in archive_note:
        errors.append("clean archive submodule limitation missing")
    plan = docs.get("npu_sd_deployment_plan.json", {})
    if plan.get("pre_write_approval") != "NOT_GRANTED" or plan.get("execution", {}).get("sd_written") is not False:
        errors.append("deployment plan claims approval or execution")
    screening = docs.get("npu_demo_directory_screening.json", {})
    if screening.get("source_root") != "<vendor-root>/03_demo":
        errors.append("03_demo screening source root is not normalized")
    if screening.get("method", {}).get("deep_audit_target") != "05-5_NPU演示":
        errors.append("05-5 deep-audit target is missing")
    if "05-5_NPU演示" not in screening.get("selected_for_deep_audit", []):
        errors.append("05-5 is not listed as a selected deep-audit target")
    demo = docs.get("milianke_npu_demo_audit.json", {})
    declared = demo.get("declared_identity", {}).get("project_file", {})
    if declared.get("device") != "DR1M90GEG400":
        errors.append("Milianke project device identity mismatch")
    demo_status = demo.get("status", {})
    if demo_status.get("mlk_board_project_identity") != "PARTIAL_DIRECT_LEAD_NOT_CLOSED":
        errors.append("Milianke board identity must remain partial")
    if demo_status.get("candidate_sd_generation_readiness") != "NOT_READY":
        errors.append("Milianke candidate SD readiness must remain not ready")
    software_path = demo.get("software_path", {})
    if software_path.get("native_runtime_assets_found_in_package") is not False:
        errors.append("native runtime absence is not retained for 05-5")
    bitstreams = demo.get("hardware_chain", {}).get("bitstreams", [])
    platform = next((item for item in bitstreams if item.get("status") == "platform_copy_candidate"), {})
    best = next((item for item in bitstreams if item.get("status") == "generated_output_candidate"), {})
    if platform.get("sha256") == best.get("sha256"):
        errors.append("05-5 bitstream copy mismatch was not retained")
    if platform.get("same_as_best_result") is not False:
        errors.append("05-5 platform/best bitstream mismatch flag is not retained")
    if demo.get("device_tree", {}).get("kernel_fragment", {}).get("included_base_present_in_package") is not False:
        errors.append("05-5 missing base DTS fact is not retained")
    board_macro = demo.get("declared_identity", {}).get("board_config", {}).get("macro", "")
    if "AD101" not in board_macro:
        errors.append("05-5 AD101 software identity conflict is not retained")
    archive = docs.get("npu_demo_archive_inventory.json", {})
    snapshot = archive.get("snapshot", {})
    if snapshot.get("archive_count") != 151 or snapshot.get("total_bytes") != 4263567836:
        errors.append("03_demo archive snapshot count/size mismatch")
    if archive.get("source_root") != "<vendor-root>/03_demo":
        errors.append("archive inventory source root is not normalized")
    selected_archives = {item.get("relative_path"): item for item in archive.get("selected_archives", [])}
    demo_archive = selected_archives.get("05-5_NPU演示/demo.zip", {})
    if demo_archive.get("listing", {}).get("entry_count") != 1777:
        errors.append("05-5 demo archive listing is incomplete")
    for relative in ("3-2_ex_fpsoc/3_2_01_sdk_base.rar", "3-2_ex_fpsoc/3_2_02_sdk_adv.rar"):
        if selected_archives.get(relative, {}).get("listing", {}).get("status") != "NOT_AVAILABLE_NO_LOCAL_READER":
            errors.append("large FPSoc RAR listing limitation missing: " + relative)
    bsp = docs.get("npu_mlk_linux_bsp_audit.json", {})
    search = bsp.get("search_results", {})
    if search.get("anlogic_dr1m90_dts_found_in_vendor_root") is not False:
        errors.append("missing base anlogic-dr1m90.dts fact is not recorded")
    if search.get("boardconfig_or_equivalent_mlk_found") is not False:
        errors.append("MLK BoardConfig search result is not false")
    if bsp.get("recovery_assessment", {}).get("base_linux_bsp_availability") != "GENERIC_GEG400_REFERENCE_ONLY":
        errors.append("generic Linux BSP classification mismatch")
    hpf = docs.get("npu_hpf_bitstream_provenance.json", {})
    if hpf.get("hpf_bitstream_relationship") != "PARTIAL_NOT_CLOSED":
        errors.append("HPF/bitstream relationship must remain partial")
    hpf_assets = {item.get("name"): item for item in hpf.get("assets", [])}
    if hpf_assets.get("05-5 generated best-result bitstream", {}).get("same_as_hpf_embedded_platform_bit") is not False:
        errors.append("05-5 best/platform bitstream mismatch is not retained")
    if hpf_assets.get("05-5 BOOT.bin", {}).get("payload_mapping") != "UNRESOLVED":
        errors.append("05-5 BOOT payload mapping must remain unresolved")
    recovery = docs.get("npu_boardconfig_recovery_assessment.json", {})
    decision = recovery.get("decision", {})
    if decision.get("boardconfig_recovery_feasibility") != "ASSET_IDENTITY_CONFLICT":
        errors.append("BoardConfig recovery classification mismatch")
    if decision.get("primary_verdict") != "BLOCKED_MLK_BOARD_PROJECT_IDENTITY":
        errors.append("deep audit primary verdict mismatch")
    packages = docs.get("uisrc_package_inventory.json", {})
    expected = packages.get("expected_downloads", {})
    if expected.get("uisrc_lab_anlogic_arm", {}).get("status") != "FOUND_EXACT":
        errors.append("uisrc ARM package exact expected-MD5 result missing")
    if expected.get("anlogic_linuxsdk", {}).get("status") != "NOT_FOUND_IN_BOUNDED_LOCAL_SCOPE":
        errors.append("anlogic-linuxsdk absence must remain explicit")
    if expected.get("uisrc_ubuntu18x64", {}).get("status") != "FOUND_EXACT":
        errors.append("uisrc VM installer exact expected-MD5 result missing")
    arm_package = next(
        (item for item in packages.get("packages", []) if item.get("id") == "uisrc_lab_anlogicM_V4_0_1_arm"),
        {},
    )
    if arm_package.get("expected_md5_match") is not True:
        errors.append("uisrc ARM package digest match is not retained")
    version_lines = arm_package.get("version_file", {}).get("text", [])
    if "Anlogic version: SDK_2025.1" not in version_lines:
        errors.append("uisrc ARM embedded SDK_2025.1 identity missing")
    if arm_package.get("board_identity", {}).get("board_config_is_mlk_specific") is not False:
        errors.append("uisrc ARM package must not be promoted to MLK BoardConfig")
    if arm_package.get("npu_and_runtime_assets", {}).get("armnn_or_alnpu_library_found") is not False:
        errors.append("uisrc ARM package userspace runtime absence is not retained")
    if arm_package.get("assessment", {}).get("candidate_sd_generation_ready") is not False:
        errors.append("uisrc ARM package must remain not ready for candidate SD generation")
    sdk_package = next(
        (item for item in packages.get("packages", []) if item.get("id") == "sdk_2025_7_known_vendor_release"),
        {},
    )
    if sdk_package.get("md5") != "a85e6f1f52782a0a9b7e7444d7f8e968":
        errors.append("known sdk.2025.7 MD5 identity mismatch")
    if sdk_package.get("sha256") != "c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0":
        errors.append("known sdk.2025.7 SHA256 identity mismatch")
    impact = packages.get("task025_impact", {})
    if impact.get("primary_verdict_unchanged") != "BLOCKED_MLK_BOARD_PROJECT_IDENTITY":
        errors.append("uisrc package audit must not clear the primary board identity blocker")
    safety = packages.get("safety", {})
    for key in ("vendor_archives_executed", "vendor_scripts_executed", "vendor_binaries_executed", "board_accessed", "vm_accessed"):
        if safety.get(key) is not False:
            errors.append("uisrc package safety.%s must be false" % key)
    vm = docs.get("npu_vm_uisrc_environment_inventory.json", {})
    vm_identity = vm.get("vm_identity", {})
    if vm_identity.get("architecture") != "x86_64":
        errors.append("VM architecture identity mismatch")
    if vm_identity.get("vm_access") != "PASS_READ_ONLY":
        errors.append("VM read-only access status missing")
    sdk_tree = vm.get("trees", {}).get("official_sdk_2025_07_tree", {})
    if "SDK_2025.07" not in sdk_tree.get("version_fact", ""):
        errors.append("VM official SDK_2025.07 marker missing")
    if sdk_tree.get("mlk_board_config") is not False:
        errors.append("VM official SDK MLK BoardConfig absence missing")
    search_result = vm.get("search_result", {})
    if search_result.get("historical_uisrc_lab_2025_07_package") != "NOT_FOUND":
        errors.append("historical VM uisrc package search result mismatch")
    if search_result.get("separate_05_5_original_workspace") != "NOT_FOUND":
        errors.append("original 05-5 workspace search result mismatch")
    vm_safety = vm.get("safety", {})
    for key in ("vm_files_modified", "vendor_scripts_executed", "vendor_installers_executed", "vendor_demo_executed", "board_accessed", "board_modified", "media_written", "credentials_collected"):
        if vm_safety.get(key) is not False:
            errors.append("VM audit safety.%s must be false" % key)
    bsp_vm = docs.get("npu_vm_historical_mlk_bsp_assessment.json", {})
    bsp_assessment = bsp_vm.get("assessment", {})
    if bsp_assessment.get("base_dts_availability") != "GENERIC_OFFICIAL_BASE_PRESENT_MLK_MAPPING_UNVERIFIED":
        errors.append("VM generic base DTS classification mismatch")
    if bsp_assessment.get("mlk_boardconfig_availability") != "NOT_FOUND":
        errors.append("VM MLK BoardConfig absence mismatch")
    if bsp_assessment.get("candidate_sd_generation_readiness") != "NOT_READY":
        errors.append("VM candidate SD readiness must remain not ready")
    provenance = docs.get("npu_vm_05_5_provenance_comparison.json", {})
    comparison = provenance.get("comparison", {})
    if comparison.get("local_and_vm_archive_match") is not True:
        errors.append("VM 05-5 archive copy identity mismatch")
    if comparison.get("exact_2025_07_uisrc_lab_provenance") is not False:
        errors.append("exact historical 2025.07 uisrc provenance must remain unproven")
    if comparison.get("mlk_boardconfig_recovered") is not False:
        errors.append("VM 05-5 MLK BoardConfig recovery mismatch")
    if comparison.get("candidate_sd_generation_readiness") != "NOT_READY":
        errors.append("VM provenance candidate SD readiness must remain not ready")
    provenance_safety = provenance.get("safety", {})
    for key in ("archive_executed", "vendor_program_executed", "installer_executed", "build_script_executed", "vm_modified", "board_accessed", "media_written"):
        if provenance_safety.get(key) is not False:
            errors.append("VM provenance safety.%s must be false" % key)
    for name, document in docs.items():
        for location, digest in walk_hashes(document, name):
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append("invalid SHA256 at %s" % location)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task": "025", "evidence_files": len(docs), "primary_verdict": primary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
