#!/usr/bin/env python3
"""Validate the documentation-only Task 029 vendor handoff package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FILES = ("README.md", "environment.md", "reproduction.md", "capability_boundary.md", "questions.md", "vendor_support_request.md", "manifest.json")
REQUIRED_METHODS = (
    "IsALHardNPUSupported", "IsConcatSupported", "IsConstantSupported", "IsInputSupported",
    "IsLayerSupported", "IsMemCopySupported", "IsOutputSupported", "IsPooling2dSupported",
    "IsPreluSupported", "IsResizeSupported", "IsConvolution2dSupported", "IsActivationSupported",
    "IsSplitterSupported", "IsAdditionSupported", "IsMultiplicationSupported", "IsElementwiseUnarySupported",
)
REQUIRED_QUESTIONS = ("DR1M90 GEG400", "AL_onnx_pass", "generic quantized YOLO", "ALHardNPU", "convert_tool", "al_ai_flow", "HPF", "SoftNPU", "SDK", "bitstream")
FORBIDDEN_SUFFIXES = {".onnx", ".bin", ".elf", ".so", ".ko", ".a", ".tar", ".gz", ".xz", ".zip", ".7z", ".img", ".dtb", ".hpf", ".tmfile"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc


def validate(package: Path) -> list[str]:
    errors: list[str] = []
    package = package.resolve()
    root = package.parents[2]
    for name in REQUIRED_FILES:
        if not (package / name).is_file():
            errors.append(f"missing handoff file: {name}")
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        return errors
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return [str(exc)]
    if manifest.get("schema_version") != 1 or manifest.get("task") != "029":
        errors.append("manifest schema/task identity is invalid")
    if manifest.get("status") not in {"In Progress", "Completed"}:
        errors.append("manifest status is not a repository task state")
    if manifest.get("readiness") != "READY_FOR_VENDOR_HANDOFF":
        errors.append("handoff readiness is not READY_FOR_VENDOR_HANDOFF")
    source = manifest.get("source_of_truth", {})
    if source.get("task") != "028" or source.get("new_experiments") is not False:
        errors.append("handoff must be based only on Task 028 without new experiments")
    if source.get("primary_verdict") != "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY":
        errors.append("Task 028 primary verdict is missing")
    if source.get("primary_blocker") != "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE":
        errors.append("scoped Task 028 blocker is missing")
    identity = manifest.get("reproduction_identity", {})
    required_identity = {
        "board": ("system_bit_sha256", "system_dtb_sha256"),
        "source": ("al_onnx_pass_sha256", "requirements_sha256", "pip_freeze_sha256"),
        "runtime": ("libarmnn_sha256", "libarmnn_onnx_parser_sha256", "libprotobuf_sha256"),
        "model": ("yolov5n_v7_opset12_sha256", "input_sha256"),
        "runner": ("diagnostic_aarch64_elf_sha256",),
    }
    for section, fields in required_identity.items():
        values = identity.get(section, {})
        for field in fields:
            value = values.get(field)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                errors.append(f"invalid or missing identity SHA256: {section}.{field}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(identity.get("source", {}).get("commit", ""))):
        errors.append("source commit must be a 40-hex Git identity")
    tracks = manifest.get("tracks", {})
    expected = {
        "track_a_raw_onnx": "BLOCKED_UNSUPPORTED_ALNPU_GRAPH",
        "track_b_apug1205_native": "BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE",
        "track_c1_al_onnx_pass": "PASS",
        "track_c2_quantized_host_accuracy": "NOT_ACCEPTED_PAUSED",
        "track_c4_benchmark": "NOT_RUN",
    }
    for key, value in expected.items():
        if tracks.get(key) != value:
            errors.append(f"track status mismatch: {key}")
    if tracks.get("track_c3") != {"parser": "PASS", "network": "PASS", "layer_support": "BLOCKED", "load_network": "NOT_REACHED", "npu_execution": "NOT_REACHED"}:
        errors.append("Track C3 stage status is incomplete")
    evidence = manifest.get("evidence", [])
    if not evidence:
        errors.append("manifest has no evidence references")
    for entry in evidence:
        rel, digest = entry.get("path"), entry.get("sha256")
        if not isinstance(rel, str) or not rel.startswith("results/evidence/028/"):
            errors.append(f"evidence reference is outside Task 028: {rel!r}")
            continue
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"invalid evidence SHA256: {rel}")
            continue
        path = root / rel
        if not path.is_file():
            errors.append(f"evidence file is missing: {rel}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"evidence SHA256 mismatch: {rel}")
    capability = (package / "capability_boundary.md").read_text(encoding="utf-8") if (package / "capability_boundary.md").is_file() else ""
    for method in REQUIRED_METHODS:
        if method not in capability:
            errors.append(f"capability matrix missing method: {method}")
    for phrase in ("LayerSupportBase", "ALHardNPU", "CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE"):
        if phrase not in capability:
            errors.append(f"capability scope/conclusion missing: {phrase}")
    if "not a claim about" not in capability.lower() or "dr1m90 hardware" not in capability.lower():
        errors.append("capability scope/conclusion missing: not a claim about DR1M90 hardware")
    questions = (package / "questions.md").read_text(encoding="utf-8") if (package / "questions.md").is_file() else ""
    for phrase in REQUIRED_QUESTIONS:
        if phrase.lower() not in questions.lower():
            errors.append(f"support question missing: {phrase}")
    for path in package.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"vendor/binary-like material is present: {path.relative_to(package)}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non-text material is present: {path.relative_to(package)}")
            continue
        personal_path_pattern = (
            r"/" + r"home/(?:administrator|uisrc|xiaoj)"
            + r"|/" + r"mnt/c/Users/"
            + r"|[A-Z]:\\Users\\"
        )
        if "-----BEGIN " in text or re.search(personal_path_pattern, text, re.I):
            errors.append(f"sensitive or absolute personal path in: {path.relative_to(package)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, default=Path("docs/vendor_handoff/dr1m90_npu"))
    args = parser.parse_args()
    errors = validate(args.package_dir)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"status": "PASS", "task": "029", "readiness": "READY_FOR_VENDOR_HANDOFF", "evidence": "Task 028 references verified", "vendor_material": "absent"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
