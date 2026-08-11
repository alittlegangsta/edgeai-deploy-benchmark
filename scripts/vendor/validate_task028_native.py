#!/usr/bin/env python3
"""Validate the Task 028 APUG1205 native-path audit without trusting prose."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TUTORIAL_BIT_SHA256 = "e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: pathlib.Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def check_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        fail(f"{label} is not a lowercase SHA256")


def check_git_commit(value: object, label: str) -> None:
    if not isinstance(value, str) or not GIT_COMMIT_RE.fullmatch(value):
        fail(f"{label} is not a 40-character Git commit")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=pathlib.Path,
        default=pathlib.Path("results/evidence/028/native_toolchain_audit.json"),
    )
    parser.add_argument(
        "--positive",
        type=pathlib.Path,
        default=pathlib.Path("results/evidence/028/native_yolov5s_positive_path.json"),
    )
    parser.add_argument(
        "--softnpu",
        type=pathlib.Path,
        default=pathlib.Path("results/evidence/028/softnpu_ip_audit.json"),
    )
    args = parser.parse_args()

    audit = read_json(args.audit)
    positive = read_json(args.positive)
    softnpu = read_json(args.softnpu)

    if audit.get("status") != "BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE":
        fail("native audit status is not the approved unavailable-toolchain result")
    if audit.get("track") != "B":
        fail("native audit is not marked as Track B")
    compiler = audit.get("asset_availability", {})
    for name in (
        "native_compiler_container",
        "convert_tool",
        "al_ai_flow",
        "nn_compiler",
        "positive_yolov5s_320_sigmoid_onnx",
        "net_config_yolov5s_json",
        "tmfile",
        "rt_bin",
        "weight_bin",
        "libnpu_runtime",
        "npu_c_api_h",
        "native_one_shot_source_or_elf",
    ):
        if compiler.get(name) is not False:
            fail(f"native asset {name} must be explicitly unavailable")
    if compiler.get("armnn_assets_are_native_substitute") is not False:
        fail("ArmNN assets must not be treated as a native-runtime substitute")
    cache = audit.get("asset_search", {}).get("docker_or_container_cache", {})
    for name in ("docker_command", "podman_command", "nerdctl_command"):
        if cache.get(name) != "not found":
            fail(f"container availability field {name} is not a negative audit result")
    check_sha256(audit.get("apug1205_document", {}).get("sha256"), "APUG document SHA256")
    check_git_commit(
        audit.get("repository_identities", {}).get("dr1m90_npu", {}).get("head"),
        "dr1m90_npu HEAD",
    )
    check_git_commit(
        audit.get("repository_identities", {}).get("sdk", {}).get("head"),
        "sdk HEAD",
    )

    if positive.get("status") != "NOT_EXECUTED":
        fail("native YOLOv5s positive path must remain NOT_EXECUTED")
    if positive.get("outputs", {}).get("native_board_result") != "not_run":
        fail("native board result must remain not_run")
    if positive.get("benchmark") != "NOT_RUN":
        fail("native path must not report a benchmark")
    for name, present in positive.get("required_inputs", {}).items():
        if present is not False:
            fail(f"positive-path asset {name} is not explicitly unavailable")

    if softnpu.get("status") != "PASS_STATIC_NPU_SOFT_CONFIGURATION":
        fail("SoftNPU audit status is not the static configuration result")
    design = softnpu.get("source", {}).get("design_xml", {}).get("video_npu_configuration", {})
    for name in ("NPU_SOFT", "SOFT_NN", "SOFT_YOLO", "SOFT_RESIZE"):
        if design.get(name) != 1:
            fail(f"SoftNPU configuration {name} is not statically enabled")
    if softnpu.get("source", {}).get("tutorial_platform_bitstream", {}).get("sha256") != TUTORIAL_BIT_SHA256:
        fail("tutorial platform bitstream identity differs from the frozen APUG/05-5 input")
    if softnpu.get("interpretation", {}).get("native_compiler_proof") is not False:
        fail("SoftNPU metadata must not be interpreted as compiler proof")
    if softnpu.get("interpretation", {}).get("native_runtime_proof") is not False:
        fail("SoftNPU metadata must not be interpreted as runtime proof")

    # Keep this check useful if evidence is copied or regenerated: all recorded
    # hashes must be syntactically valid, without hashing private vendor files.
    for path, value in (
        (args.audit, audit),
        (args.positive, positive),
        (args.softnpu, softnpu),
    ):
        encoded = json.dumps(value, sort_keys=True).encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() == "0" * 64:
            fail(f"impossible evidence digest for {path}")

    print(
        json.dumps(
            {
                "status": "PASS",
                "track_a": "BLOCKED_UNSUPPORTED_ALNPU_GRAPH",
                "track_a_scoped_backend": "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE",
                "track_b": "BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE",
                "native_positive_path": "NOT_EXECUTED",
                "softnpu_static_configuration": "PASS",
                "cpu_fallback": "not accepted",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
