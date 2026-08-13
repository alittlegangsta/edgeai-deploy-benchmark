#!/usr/bin/env python3
"""Validate the host-side official AL_onnx_pass Track C evidence.

The validator checks recorded artifacts and correctness gates only.  It never
imports or executes vendor code, accesses the board, accepts CPU fallback, or
turns a quantization smoke result into an NPU result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "results" / "evidence" / "028"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load(name: str) -> dict:
    with (EVIDENCE / name).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit a JSON result")
    args = parser.parse_args()

    audit = load("al_onnx_pass_audit.json")
    environment = load("trackc_environment.json")
    smoke = load("trackc_official_smoke.json")
    validation = load("trackc_validation.json")
    int8_smoke = load("trackc3_board_int8_smoke.json")
    probe_matrix = load("trackc3_quant_operator_probe_matrix.json")
    version_audit = load("trackc3_runtime_version_audit.json")
    controls = load("trackc3_model_control_comparison.json")
    compatibility = load("trackc3_runtime_compatibility_matrix.json")
    hpf_comparison = load("trackc3_hpf_d20_comparison.json")
    support = load("trackc3_support_boundary_audit.json")
    capability = load("trackc3_capability_face_path_audit.json")

    checks: dict[str, bool] = {}
    checks["source_identity"] = (
        audit.get("task") == "028"
        and audit.get("track") == "C"
        and audit.get("source_identity", {}).get("head")
        == "199ef4d71f453bb9a000102ff39def09c4cf73f9"
    )
    checks["environment"] = (
        environment.get("track") == "C"
        and environment.get("environment", {}).get("pip_check") == "PASS"
        and environment.get("environment", {}).get("vendor_requirements_imports") == "PASS"
        and environment.get("installation", {}).get("repair_exit_code") == 0
        and len(environment.get("environment", {}).get("pip_freeze", [])) >= 40
        and environment.get("environment", {}).get("pip_freeze_sha256")
        == "7b077b4fcef14e44f97b9d4c64d3ef7d6768e18d8ce2252dcbe90b09e4da057b"
    )
    frozen = smoke.get("frozen_inputs", {})
    checks["frozen_contract"] = (
        frozen.get("model_sha256")
        == "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
        and frozen.get("input_sha256")
        == "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
    )
    entry = smoke.get("official_entry", {})
    artifacts = entry.get("artifacts", {})
    checks["official_conversion"] = (
        smoke.get("status") == "BLOCKED_TRACK_C_QUANTIZED_CORRECTNESS"
        and entry.get("exit_code") == 0
        and artifacts.get("sim", {}).get("sha256")
        == "421e1c670fbb219cb444b0244c9e0162a5c14ebc1e9b63c6a4c936d38a93422f"
        and artifacts.get("quant_uint8", {}).get("sha256")
        == "b8d4736f056a56576e905558c415012d0c90855aee429fe870c754e0335cc7af"
        and artifacts.get("split", "").startswith("NOT_CREATED")
    )
    graph = smoke.get("graph_contract", {})
    crop = graph.get("sim_detect_crop", {})
    quant = graph.get("quant_uint8", {})
    checks["detect_crop_contract"] = (
        crop.get("outputs")
        == [
            [[1, 255, 80, 80], "FLOAT"],
            [[1, 255, 40, 40], "FLOAT"],
            [[1, 255, 20, 20], "FLOAT"],
        ]
        and crop.get("operators", {}).get("Floor") == 0
        and crop.get("operators", {}).get("Shape") == 0
        and crop.get("operator_counts", {}).get("Conv") == 60
        and crop.get("operator_counts", {}).get("Resize") == 2
    )
    checks["quant_qdq_contract"] = (
        quant.get("operators", {}).get("Q") == 200
        and quant.get("operators", {}).get("DQ") == 320
        and quant.get("operators", {}).get("Floor") == 0
        and quant.get("operators", {}).get("Shape") == 0
        and quant.get("operator_counts", {}).get("QuantizeLinear") == 200
        and quant.get("operator_counts", {}).get("DequantizeLinear") == 320
    )
    fp32 = smoke.get("host_correctness", {}).get("sim_fp32", {})
    checks["fp32_host_smoke"] = (
        fp32.get("exit_code") == 0
        and fp32.get("detection_count") == 5
        and fp32.get("class_ids") == [66, 62, 41, 64, 64]
        and fp32.get("npu_claim") is False
    )
    uint8 = smoke.get("host_correctness", {}).get("quant_uint8_one_image", {})
    expanded = smoke.get("host_correctness", {}).get("quant_uint8_expanded_smoke", {})
    checks["quant_gate_is_explicitly_blocked"] = (
        uint8.get("strict_correctness") == "FAIL"
        and uint8.get("detection_count") == 5
        and uint8.get("min_box_iou", 1.0) < 0.99
        and uint8.get("max_confidence_delta", 0.0) > 0.01
        and expanded.get("strict_correctness") == "FAIL"
        and expanded.get("calibration_count") == 27
    )
    calibration_500 = frozen.get("calibration_500", {})
    quant_500 = smoke.get("host_correctness", {}).get("quant_uint8_calibration_500", {})
    checks["calibration_500_reproducible_smoke"] = (
        calibration_500.get("generated_count") == 500
        and calibration_500.get("source_count") == 27
        and calibration_500.get("generated_manifest_sha256")
        == "6f71361703b2f1979cb07bf3564ad75e23301cedf88df1ef6371168b69727922"
        and quant_500.get("calibration_count") == 500
        and quant_500.get("strict_correctness") == "FAIL"
        and quant_500.get("min_box_iou", 1.0) < 0.99
        and quant_500.get("max_confidence_delta", 0.0) > 0.01
    )
    int8 = smoke.get("int8_probe", {})
    checks["int8_invalid_graph_recorded"] = (
        int8.get("conversion_exit_code") == 0
        and int8.get("onnx_checker", "").startswith("FAIL:")
        and int8.get("host_ort_exit_code") == 1
        and int8.get("status") == "INVALID_GRAPH"
    )
    qdq = smoke.get("qdq_diagnostic", {})
    largest_errors = qdq.get("largest_qdq_relative_errors", [])
    checks["qdq_diagnostic"] = (
        qdq.get("status") == "DIAGNOSTIC_ONLY"
        and qdq.get("calibration_count") == 1
        and qdq.get("vendor_documentation_ref") == "DR1_NPU_SCRIPTS/README.md, YOLO quantization FAQ"
        and len(largest_errors) >= 6
        and largest_errors[0].get("tensor") == "/model.9/Concat_output_0"
        and float(largest_errors[0].get("qdq_error", 0.0)) > 300.0
    )
    runtime = smoke.get("runtime_and_safety", {})
    checks["no_board_or_benchmark"] = (
        runtime.get("alnpu_run") == "NOT_EXECUTED"
        and runtime.get("benchmark") == "NOT_RUN"
        and runtime.get("board_accessed") is False
        and runtime.get("vendor_binary_executed") is False
        and runtime.get("cpu_fallback_accepted") is False
    )
    checks["formal_calibration_not_fabricated"] = (
        runtime.get("formal_calibration_500_images", "").startswith("ESTABLISHED_FOR_HOST_SMOKE_ONLY")
    )
    checks["recorded_validation"] = (
        validation.get("status") == "PASS_HOST_PIPELINE_QUANT_GATE_BLOCKED"
        and validation.get("primary_status") == "BLOCKED_TRACK_C_QUANTIZED_CORRECTNESS"
    )

    # C3 evidence is deliberately validated as a compatibility result, not as
    # a correctness or benchmark result.  The full INT8 graph reached parsing
    # but failed during Optimize; no CPU fallback or inference is accepted.
    candidate = int8_smoke.get("candidate", {})
    stages = int8_smoke.get("stages", {})
    unsupported = stages.get("unsupported_layers", [])
    unsupported_pairs = {(item.get("layer"), item.get("dtype")) for item in unsupported}
    checks["int8_board_smoke"] = (
        int8_smoke.get("task") == "028"
        and int8_smoke.get("track") == "C3"
        and int8_smoke.get("status") == "BOARD_ALNPU_INT8_OPTIMIZATION_BLOCKED"
        and SHA256_RE.fullmatch(str(candidate.get("model_sha256", ""))) is not None
        and candidate.get("model_sha256") == "8ff448f1fd250a198b0a4a44a1eca9d09c50a68a4da459788960282ba98c3ad9"
        and candidate.get("opset") == 14
        and candidate.get("input", {}).get("dtype") == "FLOAT"
        and candidate.get("input", {}).get("shape") == [1, 3, 640, 640]
        and stages.get("parser_created") is True
        and stages.get("network_parsed") is True
        and stages.get("optimize_begin") is True
        and stages.get("optimize") == "FAIL"
        and stages.get("load_network") == "NOT_REACHED"
        and unsupported_pairs == {
            ("Convolution2d", "QSymmS8"),
            ("Activation", "QSymmS8"),
            ("ElementwiseBinary", "QSymmS8"),
        }
        and stages.get("fallback") == "DISABLED"
        and int8_smoke.get("command", {}).get("exit_code") == 1
        and int8_smoke.get("dmesg", {}).get("severe_error_observed") is False
        and int8_smoke.get("outputs", {}).get("detections") == "NOT_CREATED"
    )

    # The synthetic matrix is retained as a bounded diagnostic.  Its parser
    # SIGSEGV means it cannot be interpreted as per-operator support evidence.
    matrix = probe_matrix.get("matrix", [])
    expected_ops = {"Conv2d", "Activation", "Add", "Mul", "Concat", "Resize"}
    checks["quant_operator_probe_matrix"] = (
        probe_matrix.get("task") == "028"
        and probe_matrix.get("track") == "C3"
        and probe_matrix.get("status") == "PARSER_DIALECT_INCONCLUSIVE"
        and len(matrix) == 12
        and {entry.get("operator") for entry in matrix} == expected_ops
        and {entry.get("quantization") for entry in matrix} == {"UINT8", "INT8"}
        and all(
            SHA256_RE.fullmatch(str(entry.get("model_sha256", ""))) is not None
            and entry.get("exit_code") == 139
            and entry.get("stage") == "parser_created"
            and entry.get("result") == "PARSER_SIGSEGV"
            for entry in matrix
        )
        and probe_matrix.get("board_protocol", {}).get("cpu_fallback_allowed") is False
        and probe_matrix.get("board_protocol", {}).get("dmesg_severe_error") is False
        and "do not establish per-operator support" in probe_matrix.get("interpretation", "")
    )

    # Version evidence must remain explicit about what is known and what is
    # not: source/runtime skew is a hypothesis, not a measured conclusion.
    source = version_audit.get("source", {})
    board_runtime = version_audit.get("board_runtime", {})
    comparison = version_audit.get("comparison", {})
    checks["runtime_version_audit"] = (
        version_audit.get("task") == "028"
        and version_audit.get("track") == "C3"
        and version_audit.get("status") == "VERSION_IDENTITIES_RECORDED_SKEW_NOT_PROVEN"
        and source.get("commit") == "199ef4d71f453bb9a000102ff39def09c4cf73f9"
        and SHA256_RE.fullmatch(str(source.get("AL_onnx_pass_sha256", ""))) is not None
        and SHA256_RE.fullmatch(str(source.get("requirements_sha256", ""))) is not None
        and board_runtime.get("armnn_stdout_version") == "ArmNN v32.1.0"
        and board_runtime.get("version_file_value") == "ed5ae24"
        and SHA256_RE.fullmatch(str(board_runtime.get("version_file_sha256", ""))) is not None
        and board_runtime.get("libarmnn_so", {}).get("soname_filename") == "libarmnn.so.32.1"
        and board_runtime.get("libarmnn_onnx_parser_so", {}).get("soname_filename") == "libarmnnOnnxParser.so.24.6"
        and comparison.get("AL_onnx_pass_to_board_build_match") == "NOT_PROVEN"
        and comparison.get("runtime_toolchain_version_skew") == "NOT_PROVEN"
        and comparison.get("no_runtime_files_modified") is True
    )

    # Control models distinguish graph/operator coverage from a runtime
    # version claim.  The prior face model is the only measured positive;
    # YOLOv8n and YOLOv5n both stop at Optimize with fallback disabled.
    models = controls.get("models", {})
    face = models.get("vendor_face_positive", {})
    yolov8 = models.get("vendor_yolov8n_control", {})
    yolov5_uint8 = models.get("project_yolov5n_uint8", {})
    yolov5_int8 = models.get("project_yolov5n_int8", {})
    checks["control_model_comparison"] = (
        controls.get("task") == "028"
        and controls.get("track") == "C3"
        and controls.get("status") == "STATIC_CONTROL_COMPARISON_COMPLETE"
        and set(models) == {
            "vendor_face_positive",
            "vendor_yolov8n_control",
            "project_yolov5n_uint8",
            "project_yolov5n_int8",
        }
        and "Alnpu/ALHardNPU" in face.get("backend_observation", "")
        and yolov8.get("board_parse_optimize_load", {}).get("optimize") == "FAIL"
        and yolov8.get("board_parse_optimize_load", {}).get("unsupported") == "QAsymmU8 Splitter"
        and yolov8.get("board_parse_optimize_load", {}).get("load_network") == "NOT_REACHED"
        and yolov5_uint8.get("board_parse_optimize_load", {}).get("unsupported") == [
            "QAsymmU8 Conv2d",
            "QAsymmU8 Activation",
            "QAsymmU8 ElementwiseBinary",
        ]
        and yolov5_int8.get("board_parse_optimize_load", {}).get("unsupported") == [
            "QSymmS8 Conv2d",
            "QSymmS8 Activation",
            "QSymmS8 ElementwiseBinary",
        ]
        and controls.get("comparison", {}).get("runtime_skew_conclusion", "").endswith(
            "unproven possibility."
        )
    )

    # The compatibility matrix must distinguish a genuinely different runtime
    # from a byte-identical copy.  The available release package is the same
    # runtime already loaded on the board, so the NEW/OLD rows cannot isolate a
    # library-version variable.  The official YOLOv8n control still has to be
    # interpreted from the explicit Alnpu-only exception, not its vendor demo's
    # catch-and-return-zero process exit code.
    compat_source = compatibility.get("source_identity", {})
    compat_board = compatibility.get("board_runtime", {})
    compat_hardware = compatibility.get("board_hardware_context", {})
    compat_backend = compatibility.get("backend_static_identity", {})
    compat_libs = compat_board.get("libraries", {})
    compat_probe = compatibility.get("temporary_board_probe", {})
    compat_rows = compatibility.get("matrix", [])
    row_keys = {(row.get("runtime"), row.get("model")): row for row in compat_rows}
    checks["runtime_compatibility_matrix"] = (
        compatibility.get("task") == "028"
        and compatibility.get("track") == "C3"
        and compatibility.get("status") == "RUNTIME_IDENTITY_MATCHED_YOLOV8N_GATE_FAILED"
        and compat_source.get("commit") == "199ef4d71f453bb9a000102ff39def09c4cf73f9"
        and compat_source.get("git_history", {}).get("nearest_ancestor_tag")
        == "SDK_2026.01"
        and compat_source.get("git_history", {}).get("nearest_ancestor_tag_commit")
        == "a06f09a23582900e2b8843d564ea28db679649a5"
        and compat_source.get("git_history", {}).get("commits_after_nearest_ancestor_tag")
        == 3
        and compat_source.get("git_history", {}).get("head_tag_mapping")
        == "HEAD is not tagged; SDK_2026.01 is an ancestor, not an exact release identity"
        and compat_source.get("runtime_archive", {}).get("sha256")
        == "867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526"
        and compat_board.get("version_file_value") == "ed5ae24"
        and compat_board.get("all_compared_libraries_exact_match") is True
        and compat_board.get("runtime_variable_isolated") is False
        and compat_hardware.get("candidate_sd_boot_assets", {}).get("system.bit_sha256")
        == "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5"
        and compat_hardware.get("candidate_sd_boot_assets", {}).get("system.dtb_sha256")
        == "e1ddd7405245d7b9f644c64066bda64369edbac0d8e8676564261d9cfc22b979"
        and compat_hardware.get("softnpu_static_configuration") == {
            "NPU_SOFT": 1,
            "SOFT_NN": 1,
            "SOFT_YOLO": 1,
            "source": "results/evidence/028/softnpu_ip_audit.json",
        }
        and compat_backend.get("separate_alnpu_shared_object_observed") is False
        and compat_backend.get("alhardnpu_symbols_observed_in") == "libarmnn.so.32.1"
        and compat_backend.get("onnx_parser_needed") == [
            "libarmnn.so.32",
            "libprotobuf.so.23",
        ]
        and compatibility.get("vm_sdk_provenance", {}).get("app_npu_build_script_sha256")
        == "252854d2b571c91cfa57ae578fb762b92721e5b267aae659ff6bcda211efde45"
        and compatibility.get("vm_sdk_provenance", {}).get("run_yolo_pic_script_sha256")
        == "97b8311a67dbf8ecc20f70684ed4e5cb9acf97ad1071a23b84dad9ce172a39de"
        and compatibility.get("vm_sdk_provenance", {}).get("yolov8n_model_sha256")
        == "5fa7e8ee047a118c500736cf6b1f24bf1d4ec5120661b10ba661e662f9371d96"
        and set(compat_libs) == {
            "libarmnn.so.32.1",
            "libarmnnOnnxParser.so.24.6",
            "libprotobuf.so.23.0.0",
            "libarmnnBasePipeServer.so.32.1",
            "libtimelineDecoder.so.32.1",
            "libtimelineDecoderJson.so.32.1",
        }
        and all(
            value.get("exact_match") is True
            and SHA256_RE.fullmatch(str(value.get("board_sha256", ""))) is not None
            and value.get("board_sha256") == value.get("candidate_sha256")
            for value in compat_libs.values()
        )
        and compat_probe.get("persistent_system_paths_modified") is False
        and compat_probe.get("sd_or_emmc_modified") is False
        and compat_probe.get("benchmark") == "NOT_RUN"
        and compat_probe.get("cpu_fallback_allowed") is False
        and compat_probe.get("loader_proof", {}).get("ldd_status") == "PASS_NO_NOT_FOUND"
        and compat_probe.get("loader_proof", {}).get("observed_candidate_paths") == [
            "/tmp/task028-runtime/libarmnn.so.32",
            "/tmp/task028-runtime/libarmnnOnnxParser.so.24",
            "/tmp/task028-runtime/libprotobuf.so.23",
        ]
        and row_keys.get(("OLD_BOARD_RUNTIME", "yolo_face_uint8_15.onnx"), {}).get("result")
        == "PASS_EXISTING_TASK026"
        and row_keys.get(("OLD_BOARD_RUNTIME", "vendor_yolov8n.quant.onnx"), {}).get("result")
        == "FAIL_ALNPU_OPTIMIZE"
        and row_keys.get(("NEW_MATCHED_RUNTIME_COPY", "yolo_face_uint8_15.onnx"), {}).get("result")
        == "PASS_PARSER_OPTIMIZE_LOAD_TEMPORARY"
        and row_keys.get(("NEW_MATCHED_RUNTIME_COPY", "vendor_yolov8n.quant.onnx"), {}).get("result")
        == "FAIL_ALNPU_OPTIMIZE"
        and row_keys.get(("NEW_MATCHED_RUNTIME_COPY", "vendor_yolov8n.quant.onnx"), {}).get("unsupported")
        == "QAsymmU8 Splitter"
        and compatibility.get("conclusion", {}).get("critical_new_runtime_yolov8_gate") == "FAIL"
        and compatibility.get("conclusion", {}).get("runtime_toolchain_version_skew") == "NOT_PROVEN"
        and compatibility.get("conclusion", {}).get("hardware_dialect_audit")
        == "D20.1_AD101V20_GEG484_DIFFERS_FROM_05_5_GEG400"
        and compatibility.get("conclusion", {}).get("hardware_dialect_evidence")
        == "results/evidence/028/trackc3_hpf_d20_comparison.json"
    )

    # D20.1 is a useful static control, but it targets the GEG484 package and
    # has a different SoftNPU address/IRQ and SOFT_RESIZE setting.  It must not
    # be substituted for the GEG400 05-5 platform bitstream.
    current = hpf_comparison.get("current_05_5_package", {})
    d20 = hpf_comparison.get("d20_1_official_example", {})
    hpf_cmp = hpf_comparison.get("comparison", {})
    checks["hpf_d20_version_comparison"] = (
        hpf_comparison.get("task") == "028"
        and hpf_comparison.get("track") == "C3"
        and hpf_comparison.get("status") == "HPF_SOFTNPU_VERSION_COMPARISON_COMPLETE"
        and hpf_comparison.get("safety", {}).get("read_only_source_audit") is True
        and hpf_comparison.get("safety", {}).get("bitstream_written") is False
        and current.get("board_identity", {}).get("device") == "DR1M90GEG400"
        and current.get("tutorial_selected_hpf", {}).get("embedded_bitstream", {}).get("sha256")
        == "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5"
        and current.get("soft_npu_configuration") == {
            "source": "05-5_NPU演示/demo/soc_prj/al_ip/NPU_SOFT_0/.params_NPU_SOFT_0.txt",
            "sha256": "23f10bd7c7a0c9d8c017246b793eb9e75ac5dfd128f2c2691237c39c10ee7dfc",
            "NPU_SOFT": 1,
            "SOFT_NN": 1,
            "SOFT_YOLO": 1,
            "SOFT_RESIZE": 1,
            "ALL_OPERATOR": 1,
            "PRE_PROCESS": 1,
            "POST_PROCESS": 0,
        }
        and d20.get("target_identity", {}).get("device") == "DR1M90GEG484"
        and d20.get("hpf", {}).get("embedded_bitstream", {}).get("package") == "DR1M90GEG484"
        and d20.get("soft_npu_configuration", {}).get("SOFT_RESIZE") == 0
        and hpf_cmp.get("device_package_match") is False
        and hpf_cmp.get("bitstream_identity_match") is False
        and hpf_cmp.get("soft_resize_setting_match") is False
        and hpf_cmp.get("soft_npu_address_match") is False
        and hpf_cmp.get("soft_npu_interrupt_match") is False
        and hpf_cmp.get("vdma_topology_match") is False
        and hpf_cmp.get("d20_1_direct_substitution") == "REJECTED_BOARD_PACKAGE_MISMATCH"
        and hpf_cmp.get("hardware_dialect_difference_observed") is True
        and hpf_cmp.get("runtime_version_skew") == "NOT_PROVEN"
    )

    # The support-boundary audit is intentionally a static binary result plus
    # retained real-graph board evidence.  It must not turn the unavailable
    # board transport into a fabricated fresh run, and it must distinguish the
    # Alnpu whitelist from generic LayerSupportBase rejection slots.
    support_lib = support.get("armnn_binary_identity", {}).get("libarmnn", {})
    support_dispatch = support.get("support_dispatch_static_audit", {})
    vtable = support_dispatch.get("vtable_slots", [])
    vtable_map = {entry.get("method"): entry for entry in vtable}
    vendor_path = support.get("official_vendor_path", {})
    vendor_result = vendor_path.get("vendor_app_model_result", {})
    real_graphs = support.get("real_graph_evidence", {})
    hardware = support.get("hardware_context", {})
    support_conclusion = support.get("conclusion", {})
    checks["support_boundary_static_audit"] = (
        support.get("task") == "028"
        and support.get("track") == "C3"
        and support.get("status") == "ALNPU_SUPPORT_BOUNDARY_STATICALLY_IDENTIFIED"
        and support.get("safety", {}).get("board_probe_this_turn")
        == "NOT_RUN_TRANSPORT_UNAVAILABLE"
        and support.get("safety", {}).get("transport_error")
        == "UtilBindVsockAnyPort:307: socket failed 1"
        and support_lib.get("sha256")
        == "5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce"
        and support_lib.get("soname") == "libarmnn.so.32"
        and support_lib.get("build_id") == "9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895"
        and support.get("armnn_binary_identity", {}).get("packaging", {}).get(
            "separate_libAlnpu_observed"
        ) is False
        and "armnn::AlnpuLayerSupport::IsLayerSupported"
        in support.get("armnn_binary_identity", {}).get("packaging", {}).get(
            "representative_symbols", []
        )
        and vtable_map.get("LayerSupportBase::IsConvolution2dSupported", {}).get(
            "implementation"
        ) == "0x00340c50"
        and vtable_map.get("LayerSupportBase::IsActivationSupported", {}).get(
            "implementation"
        ) == "0x00340f00"
        and vtable_map.get("LayerSupportBase::IsSplitterSupported", {}).get(
            "implementation"
        ) == "0x003401e0"
        and vtable_map.get("LayerSupportBase::IsAdditionSupported", {}).get(
            "implementation"
        ) == "0x00340ec8"
        and vtable_map.get("LayerSupportBase::IsMultiplicationSupported", {}).get(
            "implementation"
        ) == "0x00340688"
        and vtable_map.get("AlnpuLayerSupport::IsConcatSupported", {}).get(
            "implementation"
        ) == "0x003b5f90"
        and vtable_map.get("AlnpuLayerSupport::IsALHardNPUSupported", {}).get(
            "implementation"
        ) == "0x003b9200"
        and vtable_map.get("AlnpuLayerSupport::IsResizeSupported", {}).get(
            "implementation"
        ) == "0x003b8168"
        and "only support add now"
        in support_dispatch.get("embedded_validation_predicates", [])
        and "weights is not a supported type"
        in support_dispatch.get("embedded_validation_predicates", [])
        and vendor_result.get("application") == "yolo_demo_pic"
        and vendor_result.get("model") == "yolov8n.quant.onnx"
        and vendor_result.get("backend") == "Alnpu only"
        and vendor_result.get("optimize") == "FAIL"
        and vendor_result.get("first_reported_unsupported") == "QAsymmU8 Splitter"
        and vendor_result.get("fallback") == "DISABLED"
        and real_graphs.get("positive_face", {}).get("observed", "").startswith(
            "Task 026 Alnpu/ALHardNPU positive"
        )
        and real_graphs.get("vendor_yolov8n", {}).get("first_real_graph_failure")
        == "QAsymmU8 Splitter at Alnpu Optimize"
        and real_graphs.get("project_yolov5n_uint8", {}).get(
            "first_real_graph_failure"
        )
        == "QAsymmU8 Conv2d, Activation and ElementwiseBinary at Alnpu Optimize"
        and real_graphs.get("project_yolov5n_int8", {}).get(
            "first_real_graph_failure"
        )
        == "QSymmS8 Conv2d, Activation and ElementwiseBinary at Alnpu Optimize"
        and hardware.get("system_bit_sha256")
        == "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5"
        and hardware.get("hpf_sha256")
        == "ec0ef8aa53f3de8a13cbb953808c68b8b947f6c84da0107248af8542f78da7a7"
        and hardware.get("softnpu_flags") == {
            "NPU_SOFT": 1,
            "SOFT_NN": 1,
            "SOFT_YOLO": 1,
            "SOFT_RESIZE": 1,
            "ALL_OPERATOR": 1,
        }
        and support_conclusion.get("vendor_app_vendor_yolov8n")
        == "FAIL_ALNPU_OPTIMIZE"
        and support_conclusion.get("runtime_skew") == "NOT_PROVEN; the available release ArmNN objects are byte-identical to the board runtime."
        and support_conclusion.get("current_primary")
        == "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY"
        and support_conclusion.get("primary_blocker")
        == "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE"
        and support_conclusion.get("track_c3")
        == "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE"
        and support_conclusion.get("track_a")
        == "BLOCKED_UNSUPPORTED_ALNPU_GRAPH"
        and support_conclusion.get("benchmark") == "NOT_RUN"
    )

    # C3c closes the static capability audit. It is scoped to the exact
    # matched AArch64 backend identity and retained real graph observations;
    # it is not a claim about an unavailable future vendor build.
    cap_matrix = capability.get("capability_matrix", {})
    cap_dispatch = cap_matrix.get("relevant_dispatch", [])
    cap_dispatch_map = {entry.get("method"): entry for entry in cap_dispatch}
    face_path = capability.get("face_positive_path", {})
    face_contract = face_path.get("network_contract", {})
    face_run = face_path.get("strict_board_observation", {})
    cap_conclusion = capability.get("conclusion", {})
    wrapper = capability.get("board_wrapper_audit", {})
    checks["capability_face_path_audit"] = (
        capability.get("task") == "028"
        and capability.get("track") == "C3c"
        and capability.get("status") == "COMPLETE"
        and capability.get("task_status") == "Completed"
        and capability.get("final_primary_verdict") == "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY"
        and capability.get("binary_identity", {}).get("libarmnn", {}).get("sha256")
        == "5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce"
        and capability.get("binary_identity", {}).get("archive_sha256")
        == "867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526"
        and cap_matrix.get("alnpu_overrides") == [
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
        ]
        and cap_matrix.get("override_symbol_addresses", {}).get("IsALHardNPUSupported", {}).get("address") == "0x003b9200"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsConcatSupported", {}).get("address") == "0x003b5f90"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsConstantSupported", {}).get("address") == "0x003b5df8"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsInputSupported", {}).get("address") == "0x003b5bd8"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsLayerSupported", {}).get("address") == "0x003bb1c8"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsMemCopySupported", {}).get("address") == "0x003b5c08"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsOutputSupported", {}).get("address") == "0x003b5bd8"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsPooling2dSupported", {}).get("address") == "0x003b6db0"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsPreluSupported", {}).get("address") == "0x003ba500"
        and cap_matrix.get("override_symbol_addresses", {}).get("IsResizeSupported", {}).get("address") == "0x003b8168"
        and all(
            cap_dispatch_map[name].get("implementation_class") == "LayerSupportBase"
            and cap_dispatch_map[name].get("classification") == "GENERIC_DEFAULT_REJECTION_PATH"
            for name in [
                "IsConvolution2dSupported",
                "IsActivationSupported",
                "IsSplitterSupported",
                "IsAdditionSupported",
                "IsMultiplicationSupported",
                "IsElementwiseUnarySupported",
            ]
        )
        and face_path.get("model_sha256")
        == "5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668"
        and face_contract.get("input") == {"shape": [1, 3, 416, 416], "dtype": "FLOAT"}
        and face_contract.get("outputs") == [
            {"shape": [1, 18, 26, 26], "dtype": "FLOAT"},
            {"shape": [1, 18, 13, 13], "dtype": "FLOAT"},
        ]
        and face_contract.get("split_nodes") == 0
        and face_run.get("requested_backend") == "Alnpu"
        and face_run.get("cpu_fallback") is False
        and face_run.get("optimize") == "PASS"
        and face_run.get("load_network") == "PASS"
        and face_run.get("runtime_assignments") == [
            "135|Alnpu |ALHardNPU",
            "134|Alnpu |ALHardNPU",
            "126|Alnpu |ALHardNPU",
        ]
        and capability.get("runtime_identity_inventory", {}).get("unique_libarmnn_sha256")
        == ["5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce"]
        and capability.get("runtime_identity_inventory", {}).get("alternate_backend_build_with_generic_yolo_overrides")
        == "NOT_FOUND_IN_AUDITED_SCOPES"
        and capability.get("runtime_identity_inventory", {}).get("runtime_skew")
        == "NOT_PROVEN"
        and capability.get("official_path_audit", {}).get("extra_conversion_between_al_onnx_pass_and_armnn")
        == "NOT_FOUND"
        and wrapper.get("status") == "UNAVAILABLE_ENVIRONMENT"
        and wrapper.get("failure_before_ssh") == "UtilBindVsockAnyPort:307: socket failed 1"
        and wrapper.get("classification") == "ENVIRONMENT_ONLY_NOT_NPU_BLOCKER"
        and cap_conclusion.get("primary")
        == "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY"
        and cap_conclusion.get("primary_blocker")
        == "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE"
        and cap_conclusion.get("track_a") == "BLOCKED_UNSUPPORTED_ALNPU_GRAPH"
        and cap_conclusion.get("native_compiler_reassessment")
        == "REQUIRED_FOR_GENERAL_YOLO_DEPLOYMENT"
        and capability.get("safety", {}).get("benchmark") == "NOT_RUN"
    )

    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema_version": 1,
        "task": "028",
        "track": "C",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "interpretation": (
            "Vendor host dependencies and the unmodified official conversion are closed. "
            "The full YOLOv5n QAsymmU8 and QSymmS8 graphs fail current Alnpu Optimize, "
            "while the release YOLOv8n control fails QAsymmU8 Splitter. The synthetic "
            "operator matrix is parser-dialect inconclusive. The release runtime "
            "copy is byte-identical to the board runtime; the matched-runtime "
            "YOLOv8n Alnpu-only gate still fails QAsymmU8 Splitter, so runtime/toolchain "
            "skew is not proven. No YOLOv5n inference or benchmark was accepted. "
            "The C3c audit scopes the result to the matched compiled backend: "
            "generic YOLO layer slots use LayerSupportBase rejection paths, while "
            "the face positive control uses the evidenced ALHardNPU fused/custom "
            "assignment path."
        ),
    }
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
