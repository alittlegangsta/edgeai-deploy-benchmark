#!/usr/bin/env python3
"""Build and validate the Task042 final demo recording package.

The package is deliberately evidence-only.  ``--write`` derives the manifest
from the immutable Task040 authoritative results and hashes existing small
repository assets; it does not run an inference binary, access a board, or
create a recording.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "results/final/authoritative_results.json"
MANIFEST = ROOT / "release/demo/manifest.json"
GUIDE = ROOT / "docs/FINAL_DEMO_GUIDE.md"

ASSET_SPECS = (
    ("README.md", "final project presentation", "markdown"),
    ("docs/PROJECT_PRESENTATION.md", "architecture and shot-list source", "markdown"),
    ("docs/FINAL_BENCHMARK_RESULTS.md", "formal benchmark provenance", "markdown"),
    ("results/final/README_READY_TABLES.md", "README-ready formal tables", "markdown"),
    ("results/final/authoritative_results.json", "formal source authority", "json"),
    ("results/evidence/039/pc_tensorrt_fp16_video.json", "PC video integration evidence", "json"),
    ("results/evidence/039/dr_camera_ncnn_int8.json", "DR1 camera integration evidence", "json"),
    ("results/evidence/039/validation.json", "video/camera validation", "json"),
    ("results/evidence/036/vendor_face_flow_audit.json", "vendor face flow audit", "json"),
    ("results/evidence/036/face_runner_benchmark.json", "vendor face functional run", "json"),
    ("results/evidence/036/artifact_manifest.json", "vendor face identity manifest", "json"),
    ("results/evidence/036/board_stdout.log", "Alnpu assignment log", "text"),
    ("results/evidence/036/board_stderr.log", "no-fallback status log", "text"),
    ("results/images/021/first_annotated.png", "DR1 camera representative frame", "image"),
    ("results/images/021/middle_annotated.png", "DR1 camera representative frame", "image"),
    ("results/images/021/last_annotated.png", "DR1 camera representative frame", "image"),
    ("results/images/036/face_annotated.png", "vendor face NPU visual", "image"),
    ("results/videos/anlogic_arm_ncnn_reference.avi", "reviewed ARM video", "video"),
)

TASK040_ALLOWED = {
    "README.md",
    "TASKS.md",
    "docs/FINAL_BENCHMARK_RESULTS.md",
    "results/final/README_READY_TABLES.md",
    "results/final/authoritative_results.json",
    "results/final/validation.json",
    "scripts/validate_task040_final_results.py",
    "tasks/040_final_cross_platform_benchmark_results.md",
    "tests/python/test_task040_final_results.py",
}
TASK041_ALLOWED = TASK040_ALLOWED | {
    "docs/PROJECT_PRESENTATION.md",
    "scripts/validate_task041_presentation.py",
    "tasks/041_final_readme_project_presentation.md",
    "tests/python/test_task041_presentation.py",
}
TASK042_ALLOWED = TASK041_ALLOWED | {
    "docs/FINAL_DEMO_GUIDE.md",
    "release/demo/manifest.json",
    "scripts/validate_task042_demo_release.py",
    "tasks/042_final_demo_capture_release_validation.md",
    "tests/python/test_task042_demo_release.py",
    "scripts/validate_task041_presentation.py",
    "docs/career/RESUME_PROJECT.md",
    "docs/career/PROJECT_PITCH.md",
    "docs/career/INTERVIEW_QA.md",
    "docs/career/PROJECT_STORIES.md",
    "docs/career/FINAL_PROJECT_FACTS.md",
    "scripts/validate_task043_career_package.py",
    "tasks/043_resume_interview_package.md",
    "tests/python/test_task043_career_package.py",
}

SEGMENT_IDS = {
    "readme_architecture",
    "pc_tensorrt_fp16_video",
    "dr1_camera_ncnn_int8",
    "dr1_face_alnpu_control",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{rel}: expected JSON object")
    return value


def formal_summary(authoritative: dict[str, Any]) -> dict[str, Any]:
    rows = authoritative["authoritative_results"]["cross_platform_yolov5n_performance"]
    selected = []
    for row in rows:
        metrics = row["metrics"]
        selected.append(
            {
                "id": row["id"],
                "platform": row["platform"],
                "backend": row["backend"],
                "precision": row["precision"],
                "backend_inference_mean_ms": metrics["backend_inference_ms"]["mean"],
                "pipeline_mean_ms": metrics["pipeline_ms"]["mean"],
                "fps": metrics["fps"],
                "peak_rss_kib": metrics["peak_rss_kib"].get("mean"),
                "source_evidence": row["source_evidence"],
            }
        )
    tradeoffs = authoritative["authoritative_results"]["accuracy_performance_tradeoff"]
    compact_tradeoffs = []
    for item in tradeoffs:
        compact_tradeoffs.append(
            {
                "id": item["id"],
                "decision": item["decision"],
                "accuracy": item["accuracy"],
                "performance": item["performance"],
                "source_evidence": item["source_evidence"],
            }
        )
    matrix = authoritative["authoritative_results"]["deployment_capability_matrix"]
    return {
        "formal_rows": selected,
        "accuracy_performance_tradeoffs": compact_tradeoffs,
        "deployment_capability_matrix": matrix,
        "source_policy": "Only these formal rows and tradeoffs are used for release claims; Task038/039 integration evidence is not substituted.",
    }


def build_segments() -> list[dict[str, Any]]:
    return [
        {
            "id": "readme_architecture",
            "duration_seconds": {"start": 0, "end": 20},
            "command_status": "PREPARED_NOT_RUN",
            "command": "sed -n '1,150p' README.md && sed -n '1,150p' docs/PROJECT_PRESENTATION.md",
            "overlay": "YOLOv5n v7.0 | [1,3,640,640] -> [1,25200,85] | C++17",
            "narration": "Shared OpenCV preprocessing, explicit C++ backend adapters, shared decode/NMS and evidence.",
            "scope": "presentation_only",
            "evidence": ["README.md", "docs/PROJECT_PRESENTATION.md"],
            "asset_requirements": ["repository checkout"],
        },
        {
            "id": "pc_tensorrt_fp16_video",
            "duration_seconds": {"start": 20, "end": 48},
            "command_status": "PREPARED_NOT_RUN",
            "command": "PC_BUILD=<release-build-root>; TRT_ENGINE=<task037-yolov5n-fp16-engine>; VIDEO=data/samples/videos/anlogic_arm_reference.avi; \"$PC_BUILD/edgeai_demo\" --backend tensorrt --precision fp16 --model \"$TRT_ENGINE\" --source \"$VIDEO\" --output-video \"$PC_BUILD/demo/trt_fp16.avi\" --output-json \"$PC_BUILD/demo/trt_fp16.json\" --output-codec MJPG --warmup 2",
            "overlay": "backend=tensorrt precision=fp16 inference_ms pipeline_fps detections",
            "narration": "RTX 4060 Ti TensorRT FP16 video integration; formal values remain Task040.",
            "scope": "integration_evidence_only",
            "evidence": ["results/evidence/039/pc_tensorrt_fp16_video.json", "results/final/authoritative_results.json"],
            "asset_requirements": ["Release edgeai_demo", "locally built Task037 FP16 engine", "frozen sample video"],
        },
        {
            "id": "dr1_camera_ncnn_int8",
            "duration_seconds": {"start": 48, "end": 78},
            "command_status": "PREPARED_NOT_RUN",
            "command": "DR1_ROOT=/root/edgeai/<approved-runtime-root>; LD_LIBRARY_PATH=\"$DR1_ROOT/lib\" \"$DR1_ROOT/edgeai_demo\" --backend ncnn --precision int8 --model \"$DR1_ROOT/model/eq_int8_manifest.json\" --camera 0 --max-frames 3 --output-video \"$DR1_ROOT/demo/dr_camera_int8.avi\" --output-json \"$DR1_ROOT/demo/dr_camera_int8.json\" --output-codec MJPG --threads 2 --packing 1",
            "overlay": "backend=ncnn precision=int8 inference_ms pipeline_fps detections",
            "narration": "Real DR1 UVC camera with accepted ncnn EQ INT8; bounded integration, not realtime benchmark.",
            "scope": "camera_integration_evidence_only",
            "evidence": ["results/evidence/039/dr_camera_ncnn_int8.json", "results/evidence/039/validation.json"],
            "asset_requirements": ["DR1 edgeai_demo and approved EQ INT8 manifest", "USB camera /dev/video0"],
        },
        {
            "id": "dr1_face_alnpu_control",
            "duration_seconds": {"start": 78, "end": 108},
            "command_status": "PREPARED_NOT_RUN",
            "command": "FACE_ROOT=/root/edgeai/<face-runtime-root>; LD_LIBRARY_PATH=\"$FACE_ROOT/armnn_lib/lib:$FACE_ROOT/ffmpeg_opencv4.7.0_aarch64/lib:$FACE_ROOT/lib\" \"$FACE_ROOT/edgeai_armnn_face_image\" --model \"$FACE_ROOT/inputs/yolo_face_uint8_15.onnx\" --image \"$FACE_ROOT/inputs/first_raw.png\" --output-json \"$FACE_ROOT/demo/face.json\" --output-image \"$FACE_ROOT/demo/face.png\" --warmup 2 --repeats 10",
            "overlay": "Alnpu | ALHardNPU | fallback_allowed=false | PASS_ALNPU_ONLY",
            "narration": "Vendor face functional NPU control; not a YOLOv5n performance result.",
            "scope": "functional_control_only",
            "evidence": ["results/evidence/036/vendor_face_flow_audit.json", "results/evidence/036/face_runner_benchmark.json", "results/evidence/036/board_stdout.log", "results/evidence/036/board_stderr.log"],
            "asset_requirements": ["AArch64 face runner", "yolo_face_uint8_15.onnx", "Arm NN 32.1 runtime", "DR1 runtime-root"],
            "backend_gate": {"required_assignment": "Alnpu | ALHardNPU", "fallback_allowed": False, "accept_status": "PASS_ALNPU_ONLY"},
        },
    ]


def build_manifest() -> dict[str, Any]:
    authoritative = read_json("results/final/authoritative_results.json")
    assets = []
    for rel, role, kind in ASSET_SPECS:
        path = ROOT / rel
        if not path.is_file():
            raise AssertionError(f"missing release asset: {rel}")
        assets.append({"path": rel, "role": role, "kind": kind, "sha256": sha256_file(path)})
    return {
        "schema_version": 1,
        "task": "042",
        "status": "FINAL_DEMO_PACKAGE_READY",
        "recorded_at_wsl": datetime.now().astimezone().isoformat(),
        "recorded_time_semantics": "WSL package-generation time; not capture time, board runtime time or benchmark time",
        "source_authority": {
            "path": "results/final/authoritative_results.json",
            "sha256": sha256_file(AUTH),
            "status": authoritative.get("status"),
            "formal_only": True,
        },
        "recording_policy": {
            "screen_recording": "MANUAL_NOT_PERFORMED",
            "benchmark_rerun": False,
            "board_access": False,
            "npu_execution": False,
            "formal_source": "results/final/authoritative_results.json",
            "task038_039_timings": "integration_evidence_only",
        },
        "segments": build_segments(),
        "authoritative_summary": formal_summary(authoritative),
        "assets": assets,
        "release_checks": {
            "four_segments_only": True,
            "prepared_commands_not_executed": True,
            "formal_values_come_from_task040": True,
            "task039_camera_not_formal_benchmark": True,
            "face_npu_not_yolov5n_speed_result": True,
            "custom_yolov5n_npu_status": "WAITING_FOR_VENDOR_INPUT",
            "new_binary_assets_added": False,
        },
    }


def local_links(path: Path, text: str) -> list[str]:
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    for link in links:
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        if not target.exists():
            raise AssertionError(f"broken local Markdown link: {path.relative_to(ROOT)} -> {link}")
    return links


def validate() -> dict[str, Any]:
    if not MANIFEST.is_file() or not GUIDE.is_file():
        raise AssertionError("Task042 manifest or guide is missing; run --write first")
    manifest = read_json("release/demo/manifest.json")
    authoritative = read_json("results/final/authoritative_results.json")
    if manifest.get("task") != "042" or manifest.get("status") != "FINAL_DEMO_PACKAGE_READY":
        raise AssertionError("Task042 manifest status is not FINAL_DEMO_PACKAGE_READY")
    source = manifest.get("source_authority", {})
    if source.get("path") != "results/final/authoritative_results.json":
        raise AssertionError("source authority path changed")
    if source.get("sha256") != sha256_file(AUTH):
        raise AssertionError("authoritative source SHA256 mismatch")
    if source.get("status") != authoritative.get("status"):
        raise AssertionError("authoritative source status mismatch")
    segments = manifest.get("segments")
    if not isinstance(segments, list) or {item.get("id") for item in segments} != SEGMENT_IDS or len(segments) != 4:
        raise AssertionError("manifest must contain exactly the four required segments")
    for segment in segments:
        if segment.get("command_status") != "PREPARED_NOT_RUN":
            raise AssertionError(f"segment was incorrectly marked executed: {segment.get('id')}")
        if not segment.get("command") or not segment.get("evidence"):
            raise AssertionError(f"segment is incomplete: {segment.get('id')}")
    face = next(item for item in segments if item["id"] == "dr1_face_alnpu_control")
    if face.get("scope") != "functional_control_only":
        raise AssertionError("face control scope changed")
    gate = face.get("backend_gate", {})
    if gate.get("required_assignment") != "Alnpu | ALHardNPU" or gate.get("fallback_allowed") is not False:
        raise AssertionError("face control no-fallback gate is incomplete")
    camera = next(item for item in segments if item["id"] == "dr1_camera_ncnn_int8")
    if camera.get("scope") != "camera_integration_evidence_only":
        raise AssertionError("camera integration was promoted to benchmark")
    summary = manifest.get("authoritative_summary", {})
    expected_summary = formal_summary(authoritative)
    if summary != expected_summary:
        raise AssertionError("authoritative summary is not derived from current Task040 manifest")
    if any("results/evidence/039" in json.dumps(item) for item in summary.get("formal_rows", [])):
        raise AssertionError("Task039 integration evidence entered formal summary")
    if summary.get("deployment_capability_matrix") is None:
        raise AssertionError("deployment capability matrix is missing")
    for asset in manifest.get("assets", []):
        rel = asset.get("path")
        if not isinstance(rel, str) or Path(rel).is_absolute():
            raise AssertionError(f"asset path must be repository-relative: {rel}")
        path = ROOT / rel
        if not path.is_file():
            raise AssertionError(f"missing asset: {rel}")
        if asset.get("sha256") != sha256_file(path):
            raise AssertionError(f"asset SHA256 mismatch: {rel}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256"))):
            raise AssertionError(f"invalid asset SHA256: {rel}")
    guide_text = GUIDE.read_text(encoding="utf-8")
    required_phrases = (
        "FINAL_DEMO_PACKAGE_READY", "PREPARED_NOT_RUN", "Alnpu | ALHardNPU",
        "WAITING_FOR_VENDOR_INPUT", "integration evidence", "not a realtime",
        "Task040", "Task038/039", "queue capacity=0", "no CPU fallback",
    )
    missing = [phrase for phrase in required_phrases if phrase.lower() not in guide_text.lower()]
    if missing:
        raise AssertionError(f"guide missing required scope phrases: {missing}")
    if len(re.findall(r"^## Segment [1-4]", guide_text, flags=re.MULTILINE)) != 4:
        raise AssertionError("guide must contain exactly four numbered demo segments")
    links = local_links(GUIDE, guide_text)
    sensitive = re.compile(r"/mnt/c/Users/|/home/[^/< >]+/|[A-Z]:[\\/]Users[\\/]|-----BEGIN .*PRIVATE KEY-----", re.I)
    if sensitive.search(guide_text) or sensitive.search(MANIFEST.read_text(encoding="utf-8")):
        raise AssertionError("guide or manifest contains sensitive absolute path/private-key material")
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=ROOT, text=True)
    changed = []
    for line in status.splitlines():
        path = line[3:]
        changed.append(path)
        if path not in TASK042_ALLOWED:
            raise AssertionError(f"changed path outside Task040/041/042 allowed set: {path}")
    # The package may already be committed when a later documentation task is
    # validated; existence and hash checks above are the durable requirements,
    # not whether these paths are dirty in the current worktree.
    if not GUIDE.is_file() or not MANIFEST.is_file():
        raise AssertionError("Task042 guide and manifest are missing")
    return {
        "status": "PASS",
        "task": "042",
        "checks": {
            "authoritative_source_hash": True,
            "four_prepared_segments": True,
            "formal_summary_derivation": True,
            "no_fallback_face_gate": True,
            "integration_scope_boundaries": True,
            "asset_hashes": True,
            "markdown_links": True,
            "sensitive_material_scan": True,
            "allowed_file_hygiene": True,
        },
        "local_markdown_links_checked": len(links),
        "asset_count": len(manifest["assets"]),
        "changed_paths_checked": len(changed),
        "commands_executed": [
            "manifest generation/validation only; no inference, board or NPU command",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="derive release/demo/manifest.json")
    args = parser.parse_args()
    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
