#!/usr/bin/env python3
"""Offline validator for Task 035 INT8 evidence.

This validator checks identities and gates only; it never downloads data or
turns a skipped ARM build into a passing result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "evidence" / "035"


def read_json(name: str) -> dict:
    path = EVIDENCE / name
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise AssertionError(f"{name} root is not an object")
    return value


def check_hash(value: str, label: str) -> None:
    if not SHA256.fullmatch(value):
        raise AssertionError(f"{label} is not a lowercase SHA256")


def self_test() -> None:
    check_hash("0" * 64, "self-test")
    try:
        check_hash("not-a-hash", "negative self-test")
    except AssertionError:
        return
    raise AssertionError("negative hash test did not fail")


def validate() -> dict:
    source = read_json("int8_source_build_audit.json")
    tools = read_json("int8_tool_audit.json")
    calibration = read_json("calibration_manifest.json")
    evaluation = read_json("evaluation_manifest.json")
    quant = read_json("int8_quantization_run.json")
    correctness = read_json("int8_correctness.json")
    build = read_json("int8_build_matrix.json")
    profile = read_json("int8_layer_profile.json")
    bounded = read_json("int8_bounded_validation.json")
    coco = read_json("coco_accuracy_readiness.json")
    coco_audit = read_json("coco_evaluator_audit.json")
    full_eval = read_json("coco_full_evaluation.json")
    arm_benchmark = read_json("arm_int8_benchmark.json")

    checks: dict[str, bool] = {}
    checks["source_commit"] = source["source"]["commit"] == "56775de50990ab7f16627efdcf5529b49541206f"
    checks["host_int8_enabled"] = source["host_build"]["NCNN_INT8"] == "ON"
    checks["official_tools"] = set(tools["official_flow"]) == {"optimize", "calibration", "quantize", "source"}
    checks["calibration_count"] = calibration["count"] == 500 and calibration["target_count"] == 500
    checks["calibration_manifest"] = calibration["manifest_sha256"] == "de490f890d82b40e0f66f17ed4289d2efd276e933b6e9f0935e4572c365c28f7"
    checks["evaluation_count"] = evaluation["count"] == 500
    checks["evaluation_manifest"] = evaluation["manifest_sha256"] == "b98b81be7822bce89b10535e6806833b30ac56d706723ce1d88b80c0f2cc3f2d"
    checks["selection_and_annotations"] = (
        calibration["selection"]["seed"] == 35035
        and evaluation["selection"]["seed"] == 35035
        and calibration["selection"]["annotation_sha256"] == "e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f"
        and evaluation["annotation"]["sha256"] == "e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f"
    )
    checks["manifests_disjoint"] = calibration["evaluation_overlap"] == 0 and evaluation["selection"]["overlap_count"] == 0
    metric_scope = evaluation["metric_scope"].lower()
    checks["metrics_scope_explicit"] = (
        "corrected coco bbox subset" in metric_scope
        and "confidence=0.001" in metric_scope
        and "deployment threshold remains" in metric_scope
    )
    checks["valid_candidate_failed_gate"] = (
        correctness["status"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and correctness["previous_bounded_status"] == "INT8_ACCURACY_REJECTED"
        and correctness["previous_task_status"] == "INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA"
        and correctness["valid_calibration_candidate"]["calibration_count"] == 22
        and correctness["valid_calibration_candidate"]["detection_count"] == 3
        and correctness["valid_calibration_candidate"]["gate_result"] == "FAIL_DETECTION_COUNT"
    )
    checks["performance_evidence"] = (
        arm_benchmark["status"] == "INT8_ACCEPTED"
        and arm_benchmark["protocol"]["sample_count_per_variant"] == 50
        and arm_benchmark["protocol"]["independent_processes_per_variant"] == 5
        and arm_benchmark["protocol"]["warmup"] == 3
        and arm_benchmark["protocol"]["repeat_per_process"] == 10
    )
    checks["final_int8_decision"] = (
        arm_benchmark["status"] == "INT8_ACCEPTED"
        and arm_benchmark["accuracy_gate"]["status"] == "PASS"
        and arm_benchmark["accuracy_gate"]["decision"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and arm_benchmark["comparison"]["meaningful_inference_benefit"] is True
        and arm_benchmark["comparison"]["inference_speedup_fp32_over_eq"] > 1.0
        and arm_benchmark["comparison"]["pipeline_speedup_fp32_over_eq"] > 1.0
    )
    checks["arm_build_not_fabricated"] = (
        build["arm_aarch64"]["status"] == "BUILT_AND_EXECUTED"
        and build["arm_aarch64"]["ldd_status"] == "PASS_PRIVATE_LIBS_RESOLVED"
    )
    checks["layer_profile_completed"] = (
        profile["status"] == "PASS_DIAGNOSTIC"
        and profile["int8_eq"]["run_count"] == 6
        and profile["int8_eq"]["layer_count"] == 206
        and profile["comparison"]["convolution_layer_count_equal"] is True
    )
    checks["no_npu_quantizer"] = quant["al_onnx_pass_used"] is False
    checks["eq_not_accepted"] = (
        correctness["eq_control"]["status"] == "NOT_ACCEPTED"
        and correctness["eq_control"]["table_generated"] is False
        and correctness["eq_control"]["exit_code"] == 130
    )
    checks["aciq_metrics_fail_gate"] = (
        correctness["valid_calibration_candidate"]["minimum_class_matched_iou"] < 0.99
        and correctness["valid_calibration_candidate"]["maximum_confidence_delta"] > 0.01
    )
    candidates = {item["method"].lower(): item for item in bounded["candidates"]}
    checks["bounded_matrix_identity"] = (
        bounded["status"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and bounded["previous_status"] == "INT8_ACCURACY_REJECTED"
        and bounded["final_task_verdict"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and
        bounded["calibration"]["count"] == 22
        and bounded["calibration"]["unique_sha256_count"] == 22
        and bounded["calibration"]["manifest_sha256"] == calibration["previous_bounded_manifest"]["manifest_sha256"]
        and bounded["evaluation"]["actual_count"] == 1
        and bounded["evaluation"]["metric"] == "FP32-reference regression"
    )
    checks["bounded_aciq_matrix"] = (
        candidates["aciq"]["detection_count"] == 3
        and candidates["aciq"]["reference_detection_count"] == 5
        and candidates["aciq"]["class_agreement"] is False
        and candidates["aciq"]["minimum_matched_iou"] < 0.99
        and candidates["aciq"]["maximum_confidence_delta"] > 0.01
        and candidates["aciq"]["gate"] == "FAIL"
    )
    checks["bounded_kl_matrix"] = (
        candidates["kl"]["detection_count"] == 0
        and candidates["kl"]["catastrophic_zero_detection"] is True
        and candidates["kl"]["gate"] == "FAIL"
    )
    checks["bounded_eq_matrix"] = (
        candidates["eq"]["status"] == "NOT_ACCEPTED"
        and candidates["eq"]["table_sha256"] is None
        and candidates["eq"]["exit_code"] == 130
        and candidates["eq"]["gate"] == "NOT_EVALUATED"
    )
    checks["bounded_arm_gate"] = (
        bounded["arm_benchmark"]["status"] == "SKIPPED_CORRECTNESS_GATE"
        and bounded["arm_benchmark"]["accepted_candidate"] is None
    )
    checks["coco80_contract_and_data"] = (
        coco["status"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and coco["model_contract"]["class_count"] == 80
        and coco["model_contract"]["output_shape"] == [1, 25200, 85]
        and coco["selection"]["calibration_count"] == 500
        and coco["selection"]["evaluation_count"] == 500
        and coco["selection"]["overlap_count"] == 0
        and coco["download"]["attempted"] is False
    )
    expanded = bounded["expanded_coco_validation"]["models"]
    checks["expanded_metrics_superseded"] = (
        bounded["expanded_coco_validation"]["status"] == "SUPERSEDED_INVALID_SCOPE_AND_THRESHOLD"
        and
        expanded["fp32"]["detections"] == 2557
        and expanded["aciq"]["detections"] == 2384
        and expanded["kl"]["detections"] == 1145
        and expanded["eq"]["detections"] == 2350
        and bounded["expanded_coco_validation"]["calibration_count"] == 500
    )
    eq = bounded["expanded_coco_validation"]["eq"]
    checks["expanded_eq_complete"] = (
        eq["status"] == "COMPLETED_AND_REJECTED"
        and eq["gate"] == "FAIL_ON_HELDOUT_AND_FROZEN_REFERENCE"
        and eq["table_sha256"] == "2d138307017cf68769ec01b5c06502f4d903fe3720399235be215102d1462471"
        and eq["param_sha256"] == "b05bd424462f40d92792287cafdf463ec513ea1eb5d7a024cefd3f93b769a2c4"
        and eq["bin_sha256"] == "9ae93520aa8fa9c235176e57c3146ac6a66115cddd0186c20f2637f7516c09f7"
        and eq["runner_json_sha256"] == "2753c5c9117c9f65353784833f27b81a5ec2ee33e9faf21d6c4673775deac844"
    )
    checks["expanded_task_verdict"] = (
        correctness["expanded_coco_evaluation"]["gate_policy"]["task_level_verdict"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and correctness["expanded_golden_regression"]["candidates"]["eq"]["detection_count"] == 5
        and correctness["expanded_golden_regression"]["candidates"]["eq"]["minimum_class_matched_iou"] < 0.99
        and correctness["expanded_golden_regression"]["candidates"]["eq"]["maximum_confidence_delta"] > 0.01
    )
    corrected = coco_audit["corrected_metrics"]
    checks["coco_audit_scope"] = (
        coco_audit["status"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and coco_audit["held_out_subset"]["count"] == 500
        and coco_audit["corrected_evaluator"]["coco_eval_params"]["imgIds_count"] == 500
        and coco_audit["corrected_evaluator"]["coco_eval_params"]["imgIds_equal_held_out"] is True
        and coco_audit["corrected_evaluator"]["image_id_checks"]["prediction_ids_equal_held_out_each_model"] is True
        and coco_audit["corrected_evaluator"]["image_id_checks"]["duplicate_or_missing_subset_ids"] is False
    )
    checks["coco_audit_format"] = (
        coco_audit["corrected_evaluator"]["category_mapping"]["all_model_class_names_match_contract"] is True
        and coco_audit["corrected_evaluator"]["bbox_mapping"]["all_models_finite_and_nonnegative"] is True
        and coco_audit["corrected_evaluator"]["bbox_mapping"]["all_models_within_original_image_bounds"] is True
        and coco_audit["corrected_evaluator"]["confidence_scope"]["deployment_threshold_changed"] is False
    )
    checks["coco_audit_metrics"] = (
        abs(corrected["fp32"]["mAP50"] - 0.4973494284597922) < 1e-12
        and abs(corrected["fp32"]["mAP50_95"] - 0.30971763324139717) < 1e-12
        and abs(corrected["aciq"]["mAP50"] - 0.4759858766452364) < 1e-12
        and abs(corrected["kl"]["mAP50"] - 0.4070404716208542) < 1e-12
        and abs(corrected["eq"]["mAP50"] - 0.4840712671411614) < 1e-12
    )
    checks["fp32_sanity_gate"] = (
        coco_audit["fp32_sanity_gate"]["status"] == "PASS"
        and coco_audit["fp32_sanity_gate"]["observed_mAP50"] >= coco_audit["fp32_sanity_gate"]["minimum_mAP50"]
        and coco_audit["fp32_sanity_gate"]["observed_mAP50_95"] >= coco_audit["fp32_sanity_gate"]["minimum_mAP50_95"]
    )
    checks["full_independent_eq_gate"] = (
        full_eval["status"] == "EQ_INT8_ARM_BENCHMARK_CANDIDATE"
        and full_eval["selection"]["evaluation_count"] == 4500
        and full_eval["selection"]["calibration_count"] == 500
        and full_eval["selection"]["overlap_count"] == 0
        and full_eval["evaluator"]["confidence_threshold"] == 0.001
        and full_eval["evaluator"]["nms_iou_threshold"] == 0.6
        and full_eval["evaluator"]["max_detections_per_image"] == 100
        and full_eval["evaluator"]["evaluated_imgIds_equal_manifest"] is True
        and full_eval["evaluator"]["prediction_ids_equal_manifest"] is True
        and full_eval["evaluator"]["duplicate_or_missing_subset_ids"] is False
        and full_eval["models"]["fp32"]["images"] == 4500
        and full_eval["models"]["eq"]["images"] == 4500
        and full_eval["models"]["fp32"]["zero_detection_images"] == 0
        and full_eval["models"]["eq"]["zero_detection_images"] == 0
        and abs(full_eval["comparison"]["delta_eq_minus_fp32_mAP50"]) <= 0.02
        and abs(full_eval["comparison"]["delta_eq_minus_fp32_mAP50_95"]) <= 0.02
        and full_eval["comparison"]["gate_mAP50_pass"] is True
        and full_eval["comparison"]["gate_mAP50_95_pass"] is True
        and full_eval["comparison"]["gate_no_catastrophic_zero_detection"] is True
        and full_eval["comparison"]["accuracy_gate"] == "PASS"
    )

    for label, value in {
        "source archive": source["source"]["source_archive_sha256"],
        "param": source["model_contract"]["param_sha256"],
        "bin": source["model_contract"]["bin_sha256"],
        "calibration manifest": calibration["manifest_sha256"],
        "evaluation manifest": evaluation["manifest_sha256"],
        "calibration ids": calibration["ids_sha256"],
        "evaluation ids": evaluation["ids_sha256"],
        "calibration per-image manifest": calibration["per_image_sha256_manifest_sha256"],
        "evaluation per-image manifest": evaluation["per_image_sha256_manifest_sha256"],
        "annotation": evaluation["annotation"]["sha256"],
        "command log": quant["commands_log"]["sha256"],
        "candidate param": correctness["valid_calibration_candidate"]["param_sha256"],
        "candidate bin": correctness["valid_calibration_candidate"]["bin_sha256"],
        "candidate run": correctness["valid_calibration_candidate"]["runner_json_sha256"],
        "bounded commands": "08faee9799131fe939b95c96e27de86a2c338f50a053ad46dd04bf010c37333a",
        "bounded ACIQ bin": quant["calibration_candidates"][1]["bin_sha256"],
        "bounded KL bin": quant["calibration_candidates"][0]["bin_sha256"],
        "bounded EQ stderr": bounded["candidates"][2]["stderr_sha256"],
        "expanded EQ table": eq["table_sha256"],
        "expanded EQ param": eq["param_sha256"],
        "expanded EQ bin": eq["bin_sha256"],
        "expanded EQ runner": eq["runner_json_sha256"],
        "expanded metrics": correctness["expanded_coco_evaluation"]["metrics_sha256"],
        "expanded EQ golden": correctness["expanded_golden_regression"]["candidates"]["eq"]["prediction_json_sha256"],
        "COCO audit evaluator": "50287b0271daf95097da819a249a0dbe5cb9309a3d4eb953b7d32550d87ebb4b",
        "COCO audit metrics": "8a0404e2e815bb19e2c499d1752402cb83a3d461fd175736d350f9d9fbdf4e7b",
        "COCO mapping": "e4fc99a46d6a909f04789512401fc85bfa86fb35e0ad4f8f3ac3a446479fa571",
        "COCO FP32 result": "a6117faa3e27187afce1d6caff77a3a1d1cf702a8178e751f22ebabefe5fe097",
        "COCO ACIQ result": "bfba0b04ea464d1003172c5c39fa748409fedc0b24b91bcda614485ca699e577",
        "COCO KL result": "a9860cfdf434bcfb6a6586c4e308cad0e147e5e291d6ab0d202f47546e5e5690",
        "COCO EQ result": "11f37cda957d40f9d13b30b8df82608eea38700091ec0609f7bcd5f04a022622",
        "full evaluation manifest": full_eval["selection"]["manifest_sha256"],
        "full evaluation ids": full_eval["selection"]["ids_sha256"],
        "full evaluation per-image manifest": full_eval["selection"]["per_image_sha256_manifest_sha256"],
        "full evaluation annotation": full_eval["selection"]["annotation_sha256"],
        "full evaluator": full_eval["evaluator"]["evaluator_sha256"],
        "full metrics": full_eval["external_artifacts"]["metrics_sha256"],
        "full FP32 predictions": full_eval["models"]["fp32"]["prediction_json_sha256"],
        "full EQ predictions": full_eval["models"]["eq"]["prediction_json_sha256"],
        "full FP32 COCO result": full_eval["models"]["fp32"]["coco_result_sha256"],
        "full EQ COCO result": full_eval["models"]["eq"]["coco_result_sha256"],
        "formal profiler": arm_benchmark["build"]["profiler_elf_sha256"],
        "formal ncnn library": arm_benchmark["build"]["libncnn_sha256"],
        "formal EQ param": arm_benchmark["workload"]["eq_param_sha256"],
        "formal EQ bin": arm_benchmark["workload"]["eq_bin_sha256"],
        "layer profile profiler": profile["int8_eq"]["build"]["profiler_sha256"],
        "layer profile ncnn library": profile["int8_eq"]["build"]["libncnn_sha256"],
        "layer profile stderr": profile["int8_eq"]["raw_log"]["stderr_sha256"],
        "layer profile stdout": profile["int8_eq"]["raw_log"]["stdout_sha256"],
        "layer profile run JSON": profile["int8_eq"]["raw_log"]["run_json_sha256"],
        "board environment": arm_benchmark["board"]["environment_sha256"],
    }.items():
        check_hash(value, label)

    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise AssertionError("failed checks: " + ", ".join(failed))
    return {"schema_version": 1, "task": "035", "status": "PASS", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            print("task035 validator self-test: PASS")
            return 0
        result = validate()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("task035 INT8 evidence validation: PASS")
        return 0
    except (AssertionError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"task035 INT8 evidence validation: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
