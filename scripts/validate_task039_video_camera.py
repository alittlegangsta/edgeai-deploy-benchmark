#!/usr/bin/env python3
"""Offline validator for Task 039 dynamic-input integration evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/039"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load(name: str) -> dict[str, Any]:
    with (EVIDENCE / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate() -> dict[str, Any]:
    validation = load("validation.json")
    require(validation["task"] == "039", "task mismatch")
    require(validation["status"] == "PASS", "Task 039 validation is not PASS")
    require(validation["source"]["frame_count"] == 30, "source frame count changed")
    require(validation["source"]["fps"] == 5.0, "source FPS changed")
    require(validation["source"]["width"] == 1280 and validation["source"]["height"] == 960,
            "source geometry changed")
    require(SHA256.fullmatch(validation["source"]["sha256"]) is not None,
            "source hash malformed")

    runs = validation["runs"]
    require(set(runs) == {
        "pc_ort_fp32", "pc_ncnn_fp32", "pc_tensorrt_fp16", "dr_camera_ncnn_int8"
    }, "run matrix mismatch")
    for name, item in runs.items():
        evidence = load(item["evidence_file"])
        is_camera = name == "dr_camera_ncnn_int8"
        require(evidence["mode"] == ("camera" if is_camera else "video"), f"{name} mode mismatch")
        require(evidence["backend"]["name"] == item["backend"], f"{name} backend mismatch")
        require(evidence["backend"]["fallback"] == "none", f"{name} fallback policy changed")
        require(evidence["backend"]["input_shape"] == [1, 3, 640, 640], f"{name} input shape mismatch")
        require(evidence["backend"]["output_shape"] == [1, 25200, 85], f"{name} output shape mismatch")
        source = evidence["source"]["metadata"]
        if is_camera:
            require(evidence["backend"]["precision"] == "int8", "camera precision mismatch")
            require(source["width"] == 640 and source["height"] == 480, "camera geometry mismatch")
            require(source["fps"] == 25.0 and source["fourcc"] == "YUYV", "camera negotiation mismatch")
        else:
            require(source["width"] == 1280 and source["height"] == 960, f"{name} input geometry mismatch")
            require(source["fps"] == 5.0 and source["reported_frame_count"] == 30, f"{name} input metadata mismatch")
        counts = evidence["counts"]
        expected_counts = ({
            "captured_frames": 3, "processed_frames": 3, "dropped_frames": 0,
            "failed_frames": 0, "written_frames": 3,
        } if is_camera else {
            "captured_frames": 30, "processed_frames": 30, "dropped_frames": 0,
            "failed_frames": 0, "written_frames": 30,
        })
        require(counts == expected_counts, f"{name} frame accounting mismatch")
        require(evidence["queue"]["mode"] == "synchronous", f"{name} queue mode mismatch")
        require(evidence["queue"]["capacity"] == 0, f"{name} unbounded queue claim")
        output = evidence["output_video"]["metadata"]
        if is_camera:
            require(output["width"] == 640 and output["height"] == 480, "camera output geometry mismatch")
            require(output["fps"] == 25.0 and output["reported_frame_count"] == 3, "camera output metadata mismatch")
        else:
            require(output["width"] == 1280 and output["height"] == 960, f"{name} output geometry mismatch")
            require(output["fps"] == 5.0 and output["reported_frame_count"] == 30, f"{name} output metadata mismatch")
        artifact = item["output_artifact"]
        require(artifact["retained_outside_git"] is True, f"{name} output retention policy missing")
        require(SHA256.fullmatch(artifact["sha256"]) is not None, f"{name} output hash malformed")
        require(artifact["size_bytes"] > 0, f"{name} output size missing")
        require(len(evidence["frames"]) == (3 if is_camera else 30), f"{name} per-frame evidence missing")
        if not is_camera:
            require(all(len(frame["detections"]) == 5 for frame in evidence["frames"]),
                    f"{name} detection continuity changed")
        else:
            require(all(frame["raw_shape"] == [1, 25200, 85] for frame in evidence["frames"]),
                    "camera raw output shape mismatch")
        require(evidence["first_frame_golden"]["status"] in {"PASS", "NOT_REQUESTED"},
                f"{name} unexpected Golden status")
        for stage in ("capture_read", "preprocess", "inference", "postprocess",
                      "visualization", "video_write", "pipeline_end_to_end"):
            metrics = evidence["timings_ms"][stage]
            require(all(metrics[key] > 0.0 for key in ("mean_ms", "p50_ms", "p95_ms")),
                    f"{name} timing missing for {stage}")
        require(evidence["timings_ms"]["effective_processing_fps"] > 0.0,
                f"{name} effective FPS missing")

    trt = load("pc_tensorrt_fp16_video.json")
    require(trt["first_frame_golden"]["status"] == "NOT_REQUESTED",
            "TensorRT FP16 strict single-image diagnostic was silently relabeled")
    diagnostic = validation["tensorrt_fp16_diagnostic"]
    require(diagnostic["source"] == "results/evidence/037/correctness.json",
            "TensorRT FP16 diagnostic provenance changed")
    require(diagnostic["minimum_iou"] == 0.9935288429260254,
            "TensorRT FP16 diagnostic IoU changed")
    require(diagnostic["maximum_confidence_delta"] == 0.005570024251937866,
            "TensorRT FP16 diagnostic confidence delta changed")

    camera = validation["camera_probe"]
    require(camera["status"] == "PASS", "camera probe did not pass")
    require(camera["device"] == "/dev/video0", "camera device identity changed")
    require(camera["runtime_profile"] == "recommended-dual-thread", "camera runtime profile changed")
    require(camera["configured_threads"] == 2, "camera configured thread count changed")
    require(camera["effective_parallel_backend"] == "openmp", "camera parallel backend changed")
    require(camera["requested"] ==
            "OpenCV/V4L2 default negotiation; edgeai_demo exposes no camera size/FPS override",
            "camera requested-mode provenance changed")
    require(camera["negotiated"] == {
        "width": 640, "height": 480, "fourcc": "YUYV", "fps": 25.0, "backend": "V4L2"
    }, "camera negotiation evidence changed")
    capabilities = load("dr_camera_capabilities.json")
    require(capabilities["status"] == "PASS", "camera capabilities evidence missing")
    require(capabilities["identity"]["serial"] == "SN0001", "camera serial identity changed")
    require(capabilities["enumeration"]["format_count"] == 2, "camera format enumeration changed")
    require(camera["does_not_claim_camera_realtime"] is True,
            "camera run was incorrectly promoted to realtime performance")
    require(camera["source_rate_is_not_processing_rate"] is True,
            "camera source/processing rate distinction missing")
    require(validation["tests"]["full_python"] == "PASS 164/164 using .venv",
            "full Python test evidence missing")
    return {
        "schema_version": 1,
        "task": "039",
        "status": "PASS",
        "checks": {
            "video_source_and_output": True,
            "frame_accounting": True,
            "bounded_synchronous_semantics": True,
            "shared_backend_contract": True,
            "tensorrt_fp16_diagnostic_scoped": True,
            "camera_probe_pass": True,
        },
    }


def main() -> int:
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
