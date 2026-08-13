#!/usr/bin/env python3
"""Validate the Task 036 project-owned face Alnpu evidence offline.

The validator only consumes checked-in derived evidence.  It never accesses a
board, executes an ELF, or treats the list of registered CPU backends as proof
of fallback: the captured ArmNN assignment log is required as well.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "results" / "evidence" / "036"
IMAGES = ROOT / "results" / "images" / "036"

MODEL_SHA256 = "5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c"
ELF_SHA256 = "9306d119e556ca15f166d993356590e155ce537f8898aa6af85c51f6d95b184e"
INPUT_SHA256 = "ca7ef6edbf64379d523f7bb902977a21a942543085473700a0d1c2bd855c5c26"
ANNOTATED_SHA256 = "efa1a0463bfa67f1e4c86280b0a4f1f32f694fa52f2203809b5b51813558899a"
ARMNN_SHA256 = "5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce"
PARSER_SHA256 = "dcb43bc092ec283364806e563fa6aa8d2404eb7c005db44081821da405c5ce99"
PROTOBUF_SHA256 = "5d69d988c4b8309bb5dc9318c010bac6a16904549ffd38ce11f65a918376e265"


class ValidationError(RuntimeError):
    """Raised when a Task 036 evidence invariant is not satisfied."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValidationError(f"required non-empty file is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate() -> dict[str, Any]:
    config = load_json(ROOT / "configs/task036/face_runtime.json")
    result = load_json(EVIDENCE / "face_runner_result.json")
    benchmark = load_json(EVIDENCE / "face_runner_benchmark.json")
    manifest = load_json(EVIDENCE / "artifact_manifest.json")

    require(config.get("task") == "036", "runtime config task must be 036")
    require(config.get("backend_policy", {}).get("fallback_allowed") is False,
            "runtime config must reject fallback")
    require(config.get("backend_policy", {}).get("requested_backend") == "Alnpu",
            "runtime config must request Alnpu")

    for payload_name, payload in (("result", result), ("benchmark", benchmark)):
        require(payload.get("status") == "PASS_ALNPU_ONLY", f"{payload_name} did not pass Alnpu-only")
        require(payload.get("model_sha256") == MODEL_SHA256, f"{payload_name} model hash mismatch")
        runtime = payload.get("runtime", {})
        require(runtime.get("armnn_version") == "32.1.0", f"{payload_name} ArmNN version mismatch")
        require(runtime.get("requested_backend") == "Alnpu", f"{payload_name} backend request mismatch")
        require(runtime.get("fallback_allowed") == 0, f"{payload_name} permits fallback")
        require(runtime.get("requested_backend_registered") == 1, f"{payload_name} Alnpu is not registered")
        require(runtime.get("load_status") == "Success", f"{payload_name} LoadNetwork did not succeed")
        require(runtime.get("selected_backend") == "Alnpu", f"{payload_name} selected backend mismatch")
        require(runtime.get("cpu_fallback") == 0, f"{payload_name} reports CPU fallback")
        contract = payload.get("tensor_contract", {})
        input_info = contract.get("input", {})
        require(input_info.get("dtype") == "uint8", f"{payload_name} input dtype mismatch")
        require(input_info.get("shape") == [1, 3, 416, 416], f"{payload_name} input shape mismatch")
        outputs = contract.get("outputs", [])
        shapes = {tuple(item.get("shape", [])) for item in outputs}
        require(shapes == {(1, 18, 13, 13), (1, 18, 26, 26)},
                f"{payload_name} output heads mismatch: {shapes}")
        require(all(item.get("dtype") == "uint8" for item in outputs),
                f"{payload_name} output dtype mismatch")
        raw_outputs = payload.get("raw_outputs", [])
        require(len(raw_outputs) == 2 and all(item.get("finite") == 1 for item in raw_outputs),
                f"{payload_name} raw output finite check failed")
        detections = payload.get("detections", [])
        require(len(detections) == 2, f"{payload_name} expected two face detections")
        require(all(item.get("class_name") == "face" for item in detections),
                f"{payload_name} non-face class in result")
        require(all(item.get("confidence", 0.0) > 0.0 for item in detections),
                f"{payload_name} invalid confidence")
        timings = payload.get("timings", {})
        samples = timings.get("samples", [])
        repeats = timings.get("repeats")
        require(isinstance(repeats, int) and len(samples) == repeats and repeats > 0,
                f"{payload_name} timing sample count mismatch")
        for sample in samples:
            require(all(float(sample.get(key, 0.0)) > 0.0 for key in
                        ("preprocess_ms", "inference_ms", "postprocess_ms", "end_to_end_ms")),
                    f"{payload_name} non-positive timing sample")
        for stage in ("preprocess", "inference", "postprocess", "end_to_end"):
            summary = timings.get("summary_ms", {}).get(stage, {})
            require(float(summary.get("p95", -1.0)) >= float(summary.get("p50", 0.0)),
                    f"{payload_name} invalid p95/p50 for {stage}")

    stdout = (EVIDENCE / "board_stdout.log").read_text(encoding="utf-8")
    stderr = (EVIDENCE / "board_stderr.log").read_text(encoding="utf-8")
    require("ArmNN v32.1.0" in stdout, "captured stdout lacks ArmNN identity")
    assignments = re.findall(r"\|\s*Alnpu\s+\|\s*ALHardNPU", stdout)
    require(assignments, "captured stdout lacks Alnpu|ALHardNPU assignment")
    require("backend_request=Alnpu fallback_allowed=false" in stderr,
            "captured stderr lacks explicit no-fallback policy")
    require("status=PASS_ALNPU_ONLY" in stderr, "captured stderr lacks runner PASS status")
    require("CpuAcc fallback" not in stderr and "CpuRef fallback" not in stderr,
            "captured stderr reports a CPU fallback")

    board_state = load_json(EVIDENCE / "board_runtime_state.json")
    require(board_state.get("status") == "PASS_READ_ONLY", "board runtime state is not a read-only pass")
    require(board_state.get("kernel", {}).get("architecture") == "aarch64", "board architecture mismatch")
    require(board_state.get("cma", {}).get("total_kib") == 131072, "board CMA total mismatch")
    require(set(board_state.get("modules", {}).get("loaded", [])) == {"cma_mem", "hard_npu", "soft_npu"},
            "board module set mismatch")
    require(set(board_state.get("devices", {}).get("present", [])) ==
            {"/dev/cma_mem", "/dev/hard_npu", "/dev/soft_npu"}, "board device set mismatch")

    expected_files = {
        "face_runner_result.json": "face_runner_result_sha256",
        "face_runner_benchmark.json": "face_runner_benchmark_sha256",
        "board_stdout.log": "board_stdout_sha256",
        "board_stderr.log": "board_stderr_sha256",
        "../../images/036/face_annotated.png": "face_annotated_sha256",
        "../../images/036/face_annotated_benchmark.png": "face_annotated_benchmark_sha256",
    }
    manifest_files = manifest.get("derived_artifacts", {})
    for relative, manifest_key in expected_files.items():
        path = (EVIDENCE / relative).resolve()
        actual = sha256_file(path)
        require(actual == manifest_files.get(manifest_key), f"artifact hash mismatch: {relative}")

    require(manifest.get("project_runner", {}).get("sha256") == ELF_SHA256,
            "project runner hash mismatch")
    require(manifest.get("external_model", {}).get("sha256") == MODEL_SHA256,
            "external model hash mismatch")
    require(manifest.get("external_runtime", {}).get("libarmnn_sha256") == ARMNN_SHA256,
            "ArmNN runtime hash mismatch")
    require(manifest.get("external_runtime", {}).get("parser_sha256") == PARSER_SHA256,
            "OnnxParser runtime hash mismatch")
    require(manifest.get("external_runtime", {}).get("protobuf_sha256") == PROTOBUF_SHA256,
            "protobuf runtime hash mismatch")
    require(manifest.get("scope", {}).get("yolov5n_comparison") == "NOT_PERFORMED",
            "face control was incorrectly compared with YOLOv5n")

    return {
        "status": "PASS",
        "task": "036",
        "checks": {
            "runtime_config": True,
            "model_and_tensor_contract": True,
            "alnpu_only_runtime": True,
            "alhardnpu_assignment_log": True,
            "board_devices_and_cma": True,
            "artifact_hashes": True,
            "scope_boundary": True,
        },
        "assignment_count": len(assignments),
        "benchmark_repeats": benchmark["timings"]["repeats"],
        "note": "Functional vendor face control only; no YOLOv5n NPU performance claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write validation JSON to this path")
    args = parser.parse_args()
    try:
        report = validate()
    except ValidationError as error:
        print(f"Task 036 validation: FAIL: {error}")
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
