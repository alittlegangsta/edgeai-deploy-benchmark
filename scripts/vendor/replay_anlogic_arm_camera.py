#!/usr/bin/env python3
"""Replay Task 021 camera frames through the approved native single-image path."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = ROOT / "results" / "evidence" / "021"
DEFAULT_RAW_ROOT = ROOT / "results" / "logs" / "vendor" / "arm_uvc_camera" / "replay_frames"
DEFAULT_EXECUTABLES = (
    ROOT / "build" / "pc-all-release" / "edgeai_ncnn_image",
    ROOT / "build" / "pc-acceptance-release" / "edgeai_ncnn_image",
    ROOT / "build" / "pc-pr-audit-release" / "edgeai_ncnn_image",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def newest_raw_dir(root: pathlib.Path) -> pathlib.Path:
    candidates = sorted((path for path in root.glob("*") if path.is_dir()), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise RuntimeError(f"no replay frame directory found below {root}")
    return candidates[-1]


def find_executable(explicit: str | None) -> pathlib.Path:
    candidates = [pathlib.Path(explicit)] if explicit else list(DEFAULT_EXECUTABLES)
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    raise RuntimeError("approved native edgeai_ncnn_image executable was not found")


def detection_key(detection: Dict[str, Any]) -> Tuple[int, int]:
    return int(detection["class_id"]), int(detection["rank"])


def run_replay(
    evidence_dir: pathlib.Path,
    raw_dir: pathlib.Path,
    executable: pathlib.Path,
    manifest: pathlib.Path,
    config: pathlib.Path,
    param: pathlib.Path,
    model_bin: pathlib.Path,
) -> Dict[str, Any]:
    live = json.loads((evidence_dir / "camera_run.json").read_text(encoding="utf-8"))
    frame_records = live.get("frames")
    if not isinstance(frame_records, list) or not frame_records:
        raise RuntimeError("camera_run.json has no processed frame records")
    replay_dir = evidence_dir / "replay_json"
    replay_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for record in frame_records:
        index = int(record["processed_index"])
        raw = raw_dir / f"processed_{index}_raw.png"
        if not raw.is_file():
            raise RuntimeError(f"missing retained raw frame: {raw}")
        output_json = replay_dir / f"processed_{index}_replay.json"
        output_image = replay_dir / f"processed_{index}_replay.png"
        command = [
            str(executable),
            "--manifest",
            str(manifest),
            "--model-param",
            str(param),
            "--model-bin",
            str(model_bin),
            "--config",
            str(config),
            "--input",
            str(raw),
            "--output-image",
            str(output_image),
            "--output-json",
            str(output_json),
            "--threads",
            "1",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"offline replay failed for frame {index} with exit {completed.returncode}: "
                f"{completed.stderr.strip()[:240]}"
            )
        replay = json.loads(output_json.read_text(encoding="utf-8"))
        replay_detections = replay.get("detections", [])
        live_detections = record.get("detections", [])
        live_map = {detection_key(item): item for item in live_detections}
        replay_map = {detection_key(item): item for item in replay_detections}
        if set(live_map) != set(replay_map):
            class_match = False
        else:
            class_match = True

        def iou(left: List[float], right: List[float]) -> float:
            x1 = max(float(left[0]), float(right[0]))
            y1 = max(float(left[1]), float(right[1]))
            x2 = min(float(left[2]), float(right[2]))
            y2 = min(float(left[3]), float(right[3]))
            intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            area_left = max(0.0, float(left[2]) - float(left[0])) * max(
                0.0, float(left[3]) - float(left[1])
            )
            area_right = max(0.0, float(right[2]) - float(right[0])) * max(
                0.0, float(right[3]) - float(right[1])
            )
            union = area_left + area_right - intersection
            return intersection / union if union > 0.0 else 0.0

        ious: List[float] = []
        confidence_deltas: List[float] = []
        if class_match:
            for key in sorted(live_map):
                live_item = live_map[key]
                replay_item = replay_map[key]
                ious.append(
                    iou(live_item["box_xyxy_source"], replay_item["box_xyxy_source"])
                )
                confidence_deltas.append(
                    abs(float(live_item["confidence"]) - float(replay_item["confidence"]))
                )
        frame_result = {
            "processed_index": index,
            "raw_path": str(raw.relative_to(ROOT)),
            "raw_sha256": sha256(raw),
            "live_detection_count": len(live_detections),
            "replay_detection_count": len(replay_detections),
            "classes_match": class_match,
            "finite_values": all(
                all(
                    isinstance(item.get(field), (int, float))
                    for field in ("confidence",)
                )
                for item in live_detections + replay_detections
            ),
            "valid_boxes": all(
                len(item.get("box_xyxy_source", [])) == 4
                and float(item["box_xyxy_source"][2]) > float(item["box_xyxy_source"][0])
                and float(item["box_xyxy_source"][3]) > float(item["box_xyxy_source"][1])
                for item in live_detections + replay_detections
            ),
            "minimum_class_matched_iou": min(ious) if ious else 0.0,
            "maximum_confidence_delta": max(confidence_deltas) if confidence_deltas else 0.0,
            "replay_json": str(output_json.relative_to(ROOT)),
            "replay_image": str(output_image.relative_to(ROOT)),
        }
        frame_result["status"] = (
            "PASS"
            if (
                frame_result["classes_match"]
                and frame_result["finite_values"]
                and frame_result["valid_boxes"]
                and frame_result["minimum_class_matched_iou"] >= 0.99
                and frame_result["maximum_confidence_delta"] <= 0.01
            )
            else "FAIL"
        )
        results.append(frame_result)
    payload = {
        "schema_version": 1,
        "task": "021",
        "replay_method": "approved native edgeai_ncnn_image; same frozen param/bin/config",
        "offline_executable": str(executable.relative_to(ROOT)),
        "offline_executable_sha256": sha256(executable),
        "frames": results,
        "verified_frames": sum(item["status"] == "PASS" for item in results),
        "failed_frames": sum(item["status"] != "PASS" for item in results),
        "status": "PASS_TARGET" if all(item["status"] == "PASS" for item in results) else "FAIL",
    }
    (evidence_dir / "camera_replay_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--raw-dir")
    parser.add_argument("--offline-executable")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    evidence_dir = pathlib.Path(args.evidence_dir).resolve()
    raw_dir = pathlib.Path(args.raw_dir).resolve() if args.raw_dir else newest_raw_dir(DEFAULT_RAW_ROOT)
    executable = find_executable(args.offline_executable)
    for required in (
        evidence_dir / "camera_run.json",
        ROOT / "models/yolov5n-v7.0/ncnn_manifest.json",
        ROOT / "models/yolov5n-v7.0/yolov5n.ncnn.param",
        ROOT / "models/yolov5n-v7.0/yolov5n.ncnn.bin",
        ROOT / "configs/yolov5n_v7_inference.json",
    ):
        if not required.is_file():
            raise RuntimeError(f"required replay input is missing: {required}")
    if args.check and not args.execute:
        print(f"replay_check=PASS raw_dir={raw_dir} executable={executable}")
        return 0
    if not args.execute:
        parser.error("use --check or --execute")
    payload = run_replay(
        evidence_dir,
        raw_dir,
        executable,
        ROOT / "models/yolov5n-v7.0/ncnn_manifest.json",
        ROOT / "configs/yolov5n_v7_inference.json",
        ROOT / "models/yolov5n-v7.0/yolov5n.ncnn.param",
        ROOT / "models/yolov5n-v7.0/yolov5n.ncnn.bin",
    )
    print(
        f"camera_replay={payload['status']} verified={payload['verified_frames']} failed={payload['failed_frames']}"
    )
    return 0 if payload["status"] == "PASS_TARGET" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"replay_anlogic_arm_camera error: {error}", file=sys.stderr)
        raise
