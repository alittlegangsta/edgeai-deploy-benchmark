import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/vendor/validate_task025_npu_sd_preflight.py"


class Task025PreflightValidatorTest(unittest.TestCase):
    def test_checked_in_evidence_passes(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--evidence-dir", str(ROOT / "results/evidence/025")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_non_pending_deployment_approval(self):
        evidence = ROOT / "results/evidence/025"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for path in evidence.glob("*.json"):
                (target / path.name).write_bytes(path.read_bytes())
            verdict_path = target / "npu_sd_image_verdict.json"
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            verdict["deployment_approval"] = "APPROVED"
            verdict_path.write_text(json.dumps(verdict), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--evidence-dir", str(target)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_static_armnn_closure_and_candidate_block_are_explicit(self):
        evidence = ROOT / "results/evidence/025"
        closure = json.loads(
            (evidence / "npu_sd_armnn_rootfs_dependency.json").read_text(encoding="utf-8")
        )
        candidate = json.loads(
            (evidence / "npu_sd_candidate_identity.json").read_text(encoding="utf-8")
        )
        self.assertEqual(closure["status"], "PASS_STATIC_NON_SYSTEM_CLOSURE_NOT_DEPLOYMENT_READY")
        self.assertEqual(closure["closure"]["non_system_needed_missing_from_candidate_lib_dir"], [])
        self.assertFalse(closure["libprotoc_check"]["dt_needed_in_yolo_armnn_parser_protobuf_closure"])
        self.assertEqual(
            candidate["candidate_boot_chain_reproducibility"]["status"],
            "PASS_BOOT_AND_FORMAL_ROOTFS_FILE_SET_NOT_PARTITIONED",
        )
        self.assertEqual(
            candidate["candidate_kernel_module_compatibility"]["status"],
            "PASS_SAME_SOURCE_STATIC_COMPATIBILITY",
        )
        self.assertEqual(
            candidate["candidate_armnn_runtime_closure"]["status"],
            "PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY",
        )
        self.assertFalse(
            candidate["candidate_sd_identity"]["official_sdk_board_config_inventory"]["mlk_board_config_found"]
        )

    def test_formal_buildroot_rootfs_and_candidate_fileset_are_separate_from_history(self):
        evidence = ROOT / "results/evidence/025"
        config = json.loads((evidence / "npu_buildroot_config_identity.json").read_text(encoding="utf-8"))
        downloads = json.loads((evidence / "npu_buildroot_dl_manifest.json").read_text(encoding="utf-8"))
        rootfs = json.loads((evidence / "npu_formal_rootfs_build.json").read_text(encoding="utf-8"))
        closure = json.loads((evidence / "npu_formal_rootfs_runtime_closure.json").read_text(encoding="utf-8"))
        candidate = json.loads((evidence / "npu_final_candidate_artifact_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(config["config"]["target_architecture"], "aarch64")
        self.assertEqual(downloads["manifest"]["file_count"], 141)
        self.assertEqual(downloads["offline_recheck"]["new_download_requests"], 0)
        self.assertEqual(rootfs["status"], "PASS_FORMAL_BUILDROOT_ROOTFS")
        self.assertEqual(closure["rootfs"]["aarch64_elf_count"], 353)
        self.assertEqual(closure["rootfs"]["x86_64_elf_count"], 0)
        self.assertEqual(closure["rootfs"]["missing_dt_needed"], [])
        self.assertEqual(candidate["status"], "READY_FOR_SD_WRITE_APPROVAL")
        self.assertTrue(candidate["readiness"]["complete_file_set"])
        self.assertFalse(candidate["readiness"]["partitioned_sd_image"])
        self.assertEqual(candidate["readiness"]["sd_write"], "NOT_PERFORMED")

    def test_pdf_injection_is_partial_and_non_destructive(self):
        evidence = ROOT / "results/evidence/025"
        workflow = json.loads((evidence / "npu_pdf_workflow_extraction.json").read_text(encoding="utf-8"))
        inputs = json.loads((evidence / "npu_pdf_input_closure.json").read_text(encoding="utf-8"))
        safety = json.loads((evidence / "npu_uisrc_build_script_safety.json").read_text(encoding="utf-8"))
        reproduction = json.loads((evidence / "npu_pdf_isolated_reproduction.json").read_text(encoding="utf-8"))
        artifacts = json.loads((evidence / "npu_pdf_candidate_artifact_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(workflow["document"]["status"], "NOT_ACCESSIBLE_IN_SESSION")
        platform = next(item for item in inputs["inputs"] if item["role"] == "platform bitstream")
        self.assertEqual(platform["sha256"], "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5")
        script_map = {item["name"]: item for item in safety["scripts"]}
        self.assertEqual(script_map["scripts/rootfs/buildroot/make_parted.sh"]["classification"], "UNSAFE_DESTRUCTIVE")
        self.assertFalse(script_map["scripts/rootfs/buildroot/make_parted.sh"]["executed"])
        self.assertEqual(reproduction["kernel"]["repair_3"]["status"], "PASS")
        self.assertEqual(artifacts["readiness"]["rootfs"], "BLOCKED_NOT_BUILT_BY_BUILDROOT")
        self.assertFalse(artifacts["readiness"]["complete_sd_file_set"])

    def test_milianke_demo_keeps_partial_identity_and_native_path_split(self):
        evidence = ROOT / "results/evidence/025"
        screening = json.loads(
            (evidence / "npu_demo_directory_screening.json").read_text(encoding="utf-8")
        )
        demo = json.loads(
            (evidence / "milianke_npu_demo_audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(screening["method"]["deep_audit_target"], "05-5_NPU演示")
        self.assertIn("05-5_NPU演示", screening["selected_for_deep_audit"])
        self.assertEqual(demo["declared_identity"]["project_file"]["device"], "DR1M90GEG400")
        self.assertEqual(demo["status"]["mlk_board_project_identity"], "PARTIAL_DIRECT_LEAD_NOT_CLOSED")
        self.assertFalse(demo["software_path"]["native_runtime_assets_found_in_package"])
        self.assertFalse(demo["device_tree"]["kernel_fragment"]["included_base_present_in_package"])

    def test_demo_archive_and_boardconfig_followup_remain_bounded(self):
        evidence = ROOT / "results/evidence/025"
        archive = json.loads(
            (evidence / "npu_demo_archive_inventory.json").read_text(encoding="utf-8")
        )
        bsp = json.loads(
            (evidence / "npu_mlk_linux_bsp_audit.json").read_text(encoding="utf-8")
        )
        recovery = json.loads(
            (evidence / "npu_boardconfig_recovery_assessment.json").read_text(encoding="utf-8")
        )
        self.assertEqual(archive["snapshot"]["archive_count"], 151)
        selected = {item["relative_path"]: item for item in archive["selected_archives"]}
        self.assertEqual(selected["05-5_NPU演示/demo.zip"]["listing"]["entry_count"], 1777)
        self.assertEqual(
            selected["3-2_ex_fpsoc/3_2_01_sdk_base.rar"]["listing"]["status"],
            "NOT_AVAILABLE_NO_LOCAL_READER",
        )
        self.assertFalse(bsp["search_results"]["anlogic_dr1m90_dts_found_in_vendor_root"])
        self.assertEqual(
            recovery["decision"]["boardconfig_recovery_feasibility"],
            "ASSET_IDENTITY_CONFLICT",
        )

    def test_uisrc_package_identity_does_not_clear_mlk_block(self):
        evidence = ROOT / "results/evidence/025"
        package = json.loads(
            (evidence / "uisrc_package_inventory.json").read_text(encoding="utf-8")
        )
        arm = next(item for item in package["packages"] if item["id"] == "uisrc_lab_anlogicM_V4_0_1_arm")
        self.assertEqual(
            package["expected_downloads"]["uisrc_lab_anlogic_arm"]["status"],
            "FOUND_EXACT",
        )
        self.assertTrue(arm["expected_md5_match"])
        self.assertIn("Anlogic version: SDK_2025.1", arm["version_file"]["text"])
        self.assertFalse(arm["board_identity"]["board_config_is_mlk_specific"])
        self.assertFalse(arm["npu_and_runtime_assets"]["armnn_or_alnpu_library_found"])
        self.assertEqual(
            package["task025_impact"]["primary_verdict_unchanged"],
            "BLOCKED_MLK_BOARD_PROJECT_IDENTITY",
        )
        self.assertEqual(
            package["expected_downloads"]["anlogic_linuxsdk"]["status"],
            "NOT_FOUND_IN_BOUNDED_LOCAL_SCOPE",
        )

    def test_vm_history_does_not_clear_mlk_block(self):
        evidence = ROOT / "results/evidence/025"
        vm = json.loads(
            (evidence / "npu_vm_uisrc_environment_inventory.json").read_text(encoding="utf-8")
        )
        bsp = json.loads(
            (evidence / "npu_vm_historical_mlk_bsp_assessment.json").read_text(encoding="utf-8")
        )
        provenance = json.loads(
            (evidence / "npu_vm_05_5_provenance_comparison.json").read_text(encoding="utf-8")
        )
        self.assertEqual(vm["vm_identity"]["architecture"], "x86_64")
        self.assertEqual(vm["search_result"]["historical_uisrc_lab_2025_07_package"], "NOT_FOUND")
        self.assertEqual(vm["search_result"]["separate_05_5_original_workspace"], "NOT_FOUND")
        self.assertEqual(
            bsp["assessment"]["base_dts_availability"],
            "GENERIC_OFFICIAL_BASE_PRESENT_MLK_MAPPING_UNVERIFIED",
        )
        self.assertEqual(bsp["assessment"]["mlk_boardconfig_availability"], "NOT_FOUND")
        self.assertFalse(provenance["comparison"]["mlk_boardconfig_recovered"])
        self.assertEqual(provenance["comparison"]["candidate_sd_generation_readiness"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
