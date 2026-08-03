#!/usr/bin/env python3
"""Offline validator for Task 021 bounded-latency camera evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys
import subprocess
from typing import Any, Dict, Iterable, List


ROOT = pathlib.Path(__file__).resolve().parents[2]
PARAM_SHA256 = "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
BIN_SHA256 = "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
NCNN_SHA256 = "bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
GOMP_SHA256 = "87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def decode_shape(path: pathlib.Path) -> List[int]:
    try:
        import cv2  # type: ignore
    except ImportError:
        completed = subprocess.run(
            ["identify", "-format", "%w %h %[channels]", str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"image cannot be decoded: {path}")
        fields = completed.stdout.strip().split()
        if len(fields) < 3:
            raise RuntimeError(f"image dimensions are unavailable: {path}")
        width, height = int(fields[0]), int(fields[1])
        channels = 4 if "a" in fields[2].lower() else 3
        return [width, height, channels]
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise RuntimeError(f"image cannot be decoded: {path}")
    return [int(image.shape[1]), int(image.shape[0]), int(image.shape[2])]


def latest_log(root: pathlib.Path, prefix: str) -> pathlib.Path | None:
    candidates = sorted(root.glob(prefix + "*"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def validate(
    evidence_dir: pathlib.Path,
    raw_dir: pathlib.Path,
    images_dir: pathlib.Path,
    logs_dir: pathlib.Path,
) -> Dict[str, Any]:
    validation_path = evidence_dir / "camera_validation.json"
    prior_validation: Dict[str, Any] = {}
    if validation_path.is_file():
        prior_validation = json.loads(validation_path.read_text(encoding="utf-8"))
    run = json.loads((evidence_dir / "camera_run.json").read_text(encoding="utf-8"))
    caps = json.loads((evidence_dir / "camera_capabilities.json").read_text(encoding="utf-8"))
    replay_path = evidence_dir / "camera_replay_validation.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    runtime = run["runtime"]
    camera = run["camera"]
    counts = run["counts"]
    frames = run["frames"]
    checks: Dict[str, Any] = {}
    checks["runtime_profile"] = (
        runtime["profile"] == "recommended-dual-thread"
        and int(runtime["configured_threads"]) == 2
        and bool(runtime["ncnn_openmp_compiled"])
        and bool(runtime["ncnn_threads_compiled"])
        and not bool(runtime["ncnn_simpleomp_compiled"])
        and runtime["effective_parallel_backend"] == "openmp"
        and runtime["ncnn_library_sha256"] == NCNN_SHA256
        and runtime["private_libgomp_sha256"] == GOMP_SHA256
        and runtime["param_sha256"] == PARAM_SHA256
        and runtime["bin_sha256"] == BIN_SHA256
    )
    checks["camera_identity"] = (
        camera["device"] == "/dev/video0"
        and camera["backend"] == "V4L2"
        and camera["negotiated_width"] == 640
        and camera["negotiated_height"] == 480
        and abs(float(camera["negotiated_fps"]) - 5.0) < 0.01
        and camera["negotiated_fourcc"] == "YUYV"
    )
    formats = {item["pixel_format"] for item in caps.get("formats", [])}
    checks["capability_audit"] = (
        caps.get("status") == "PASS"
        and caps.get("device") == "/dev/video0"
        and {"MJPG", "YUYV"}.issubset(formats)
    )
    pending = int(counts["pending_frame_at_stop"])
    checks["latest_frame_slot"] = (
        int(counts["latest_frame_capacity"]) == 1
        and int(counts["captured_frames"]) >= int(counts["published_frames"])
        and int(counts["published_frames"])
        == int(counts["processed_frames"]) + int(counts["overwritten_frames"]) + pending
        and int(counts["overwritten_frames"]) == int(counts["dropped_frames"])
        and int(counts["invalid_capture_frames"]) == 0
        and int(counts["processed_frames"]) >= 10
    )
    unpublished = int(counts.get("unpublished_at_shutdown", -1))
    checks["shutdown_accounting"] = (
        unpublished >= 0
        and int(counts["captured_frames"])
        == int(counts["published_frames"]) + unpublished
    )
    sequences = [int(frame["source_sequence"]) for frame in frames]
    checks["frame_sequences"] = (
        len(frames) == 10
        and [int(frame["processed_index"]) for frame in frames] == list(range(10))
        and sequences == sorted(set(sequences))
    )
    checks["frame_age"] = all(
        finite(frame["frame_age_at_inference_start_ms"])
        and finite(frame["end_to_end_age_ms"])
        and float(frame["frame_age_at_inference_start_ms"]) >= 0.0
        and float(frame["end_to_end_age_ms"]) >= float(frame["frame_age_at_inference_start_ms"])
        and finite(frame["timings_ms"]["pipeline"])
        and float(frame["timings_ms"]["pipeline"]) > 0.0
        for frame in frames
    )
    checks["raw_frames"] = all(
        (raw_dir / f"processed_{index}_raw.png").is_file()
        and (raw_dir / f"processed_{index}_raw.png").stat().st_size > 0
        for index in range(len(frames))
    )
    representative = {}
    for name in ("first_raw", "first_annotated", "middle_raw", "middle_annotated", "last_raw", "last_annotated"):
        path = images_dir / f"{name}.png"
        representative[name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "shape": decode_shape(path)}
    checks["representative_frames"] = all(item["shape"] == [640, 480, 3] for item in representative.values())
    checks["replay"] = replay.get("status") == "PASS_TARGET" and int(replay.get("verified_frames", 0)) == len(frames) and int(replay.get("failed_frames", 1)) == 0
    checks["exit"] = int(run.get("exit_code", 1)) == 0
    stderr = latest_log(logs_dir, "board_stderr_")
    checks["stderr_empty"] = stderr is not None and stderr.read_text(encoding="utf-8", errors="replace").strip() == ""
    checks["process_threads"] = int(runtime.get("observed_process_threads", 0)) >= 2
    all_checks_pass = all(checks.values())
    user_review_pass = (
        prior_validation.get("human_camera_review") == "PASS"
        and prior_validation.get("human_review_source") == "user"
        and prior_validation.get("candidate_approved") is True
    )
    payload = {
        "schema_version": 1,
        "task": "021",
        "status": "PASS" if all_checks_pass else "FAIL",
        "automated_validation": "PASS" if all_checks_pass else "FAIL",
        "checks": checks,
        "counts": counts,
        "source_sequence": sequences,
        "representative_frames": representative,
        "replay_status": replay.get("status"),
        "replay_verified_frames": replay.get("verified_frames"),
        "replay_failed_frames": replay.get("failed_frames"),
        "observed_process_threads_scope": "whole process including OpenCV/V4L2 and ncnn; not ncnn-only count",
        "formal_realtime_benchmark": False,
        "human_camera_review": "PASS" if user_review_pass else "PENDING",
        "human_review_source": "user" if user_review_pass else None,
        "candidate_approved": bool(all_checks_pass and user_review_pass),
    }
    if user_review_pass:
        payload["approval_recorded_at_wsl"] = prior_validation.get("approval_recorded_at_wsl")
        payload["approval_time_semantics"] = prior_validation.get("approval_time_semantics")
    validation_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default=str(ROOT / "results/evidence/021"))
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--images-dir", default=str(ROOT / "results/images/021"))
    parser.add_argument("--logs-dir", default=str(ROOT / "results/logs/vendor/arm_uvc_camera"))
    args = parser.parse_args()
    payload = validate(
        pathlib.Path(args.evidence_dir).resolve(),
        pathlib.Path(args.raw_dir).resolve(),
        pathlib.Path(args.images_dir).resolve(),
        pathlib.Path(args.logs_dir).resolve(),
    )
    print(f"camera_validation={payload['status']}")
    for key, value in payload["checks"].items():
        print(f"{key}={'PASS' if value else 'FAIL'}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"validate_anlogic_arm_camera error: {error}", file=sys.stderr)
        raise
