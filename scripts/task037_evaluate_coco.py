#!/usr/bin/env python3
"""Evaluate TensorRT COCO detections on an exact image-id subset.

This is a small, dependency-free (apart from numpy) COCO bbox evaluator for
Task 037.  It intentionally implements only the fixed all-area, max-dets=100
contract used by the project; it does not download data or infer missing IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def image_ids(path: Path) -> list[int]:
    ids: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            ids.append(int(line))
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate image ID in subset")
    return ids


def iou_xywh(a: list[float], b: list[float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + max(0.0, aw), ay1 + max(0.0, ah)
    bx2, by2 = bx1 + max(0.0, bw), by1 + max(0.0, bh)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = max(0.0, aw) * max(0.0, ah) + max(0.0, bw) * max(0.0, bh) - inter
    return inter / union if union > 0.0 else 0.0


def load_predictions(path: Path, allowed: set[int]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("prediction root is not an array")
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for item in raw:
        iid, cid = int(item["image_id"]), int(item["category_id"])
        if iid not in allowed:
            raise ValueError(f"prediction image {iid} is outside subset")
        box = [float(x) for x in item["bbox"]]
        score = float(item["score"])
        if len(box) != 4 or not math.isfinite(score) or not all(math.isfinite(x) for x in box):
            raise ValueError("non-finite or malformed prediction")
        grouped[(iid, cid)].append({"bbox": box, "score": score})
    return grouped


def evaluate(annotations: dict[str, Any], predictions: dict[tuple[int, int], list[dict[str, Any]]],
             subset: list[int], max_dets: int = 100) -> dict[str, Any]:
    cats = sorted(int(c["id"]) for c in annotations["categories"])
    subset_set = set(subset)
    gt: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for ann in annotations["annotations"]:
        iid, cid = int(ann["image_id"]), int(ann["category_id"])
        if iid in subset_set:
            gt[(iid, cid)].append(ann)

    thresholds = [0.50 + 0.05 * i for i in range(10)]
    recall_thresholds = np.linspace(0.0, 1.0, 101)
    per_threshold: list[float] = []
    per_category: dict[str, dict[str, float]] = {}
    for tiou in thresholds:
        cat_aps: list[float] = []
        for cid in cats:
            records: list[tuple[float, int, bool, bool]] = []  # score, matched, ignored, fp
            n_gt = 0
            for iid in subset:
                gts = gt.get((iid, cid), [])
                gt_ignore = [bool(g.get("iscrowd", 0)) for g in gts]
                n_gt += sum(not x for x in gt_ignore)
                dts = sorted(predictions.get((iid, cid), []), key=lambda x: -x["score"])[:max_dets]
                used = [False] * len(gts)
                for dt in dts:
                    best = -1
                    best_iou = tiou
                    for gi, g in enumerate(gts):
                        if used[gi] and not bool(g.get("iscrowd", 0)):
                            continue
                        val = iou_xywh(dt["bbox"], [float(x) for x in g["bbox"]])
                        if val >= best_iou:
                            best_iou, best = val, gi
                    if best >= 0:
                        crowd = bool(gts[best].get("iscrowd", 0))
                        if not crowd:
                            used[best] = True
                        records.append((dt["score"], 1, crowd, False))
                    else:
                        records.append((dt["score"], 0, False, True))
            if n_gt == 0:
                continue
            records.sort(key=lambda x: -x[0])
            tp = np.cumsum([r[1] and not r[2] for r in records], dtype=float)
            fp = np.cumsum([r[3] and not r[2] for r in records], dtype=float)
            if not records:
                precision = np.zeros(101, dtype=float)
            else:
                recall = tp / float(n_gt)
                prec = tp / np.maximum(tp + fp, np.finfo(float).eps)
                for j in range(len(prec) - 2, -1, -1):
                    prec[j] = max(prec[j], prec[j + 1])
                precision = np.array([prec[np.where(recall >= r)[0][0]] if np.any(recall >= r) else 0.0
                                      for r in recall_thresholds])
            cat_aps.append(float(np.mean(precision)))
            key = str(cid)
            entry = per_category.setdefault(key, {"ap50": 0.0, "ap50_95_sum": 0.0, "thresholds": 0})
            entry["ap50_95_sum"] += float(np.mean(precision))
            entry["thresholds"] += 1
            if tiou == 0.5:
                entry["ap50"] = float(np.mean(precision))
        per_threshold.append(float(np.mean(cat_aps)) if cat_aps else 0.0)

    # COCO AP averages over categories and IoU thresholds; category entries are
    # retained as a diagnostic but are not needed to reproduce the gate.
    return {
        "mAP50": per_threshold[0],
        "mAP50_95": float(np.mean(per_threshold)),
        "per_iou": {f"{t:.2f}": v for t, v in zip(thresholds, per_threshold)},
        "category_count_with_ground_truth": sum(1 for v in per_category.values() if v["thresholds"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--ids", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ids = image_ids(args.ids)
    anns = json.loads(args.annotations.read_text(encoding="utf-8"))
    available = {int(x["id"]) for x in anns["images"]}
    if not set(ids) <= available:
        raise ValueError("subset contains unknown annotation image ID")
    pred = load_predictions(args.predictions, set(ids))
    metrics = evaluate(anns, pred, ids)
    result = {
        "schema_version": 1,
        "evaluator": "task037_dependency_free_coco_bbox_subset",
        "annotations_sha256": sha256(args.annotations),
        "subset_ids_sha256": sha256(args.ids),
        "subset_count": len(ids),
        "prediction_sha256": sha256(args.predictions),
        "prediction_count": sum(len(v) for v in pred.values()),
        "prediction_image_count": len({k[0] for k in pred}),
        "confidence_threshold": 0.001,
        "nms_iou_threshold": 0.6,
        "max_detections_per_image": 100,
        "metrics": metrics,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
