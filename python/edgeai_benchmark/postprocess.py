"""Backend-independent YOLOv5 detection postprocessing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


class PostprocessError(RuntimeError):
    """Raised when raw output or postprocessing configuration is invalid."""


@dataclass(frozen=True)
class DetectionConfig:
    confidence_threshold: float
    iou_threshold: float
    class_aware_nms: bool
    max_detections: int

    def validate(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise PostprocessError("confidence threshold must be in [0, 1]")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise PostprocessError("IoU threshold must be in [0, 1]")
        if self.class_aware_nms is not True:
            raise PostprocessError("Task 004 requires class-aware NMS")
        if self.max_detections <= 0:
            raise PostprocessError("maximum detections must be positive")


def xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    """Convert center-width-height boxes into corner boxes."""
    if boxes.ndim != 2 or boxes.shape[1] != 4:
        raise PostprocessError(f"expected Nx4 xywh boxes, observed {boxes.shape}")
    converted = np.empty_like(boxes, dtype=np.float32)
    converted[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.0
    converted[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.0
    converted[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.0
    converted[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.0
    return converted


def box_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    """Compute IoU between one xyxy box and an Nx4 array."""
    if box.shape != (4,) or boxes.ndim != 2 or boxes.shape[1] != 4:
        raise PostprocessError("IoU expects one xyxy box and an Nx4 box array")
    intersection_width = np.maximum(
        0.0,
        np.minimum(box[2], boxes[:, 2]) - np.maximum(box[0], boxes[:, 0]),
    )
    intersection_height = np.maximum(
        0.0,
        np.minimum(box[3], boxes[:, 3]) - np.maximum(box[1], boxes[:, 1]),
    )
    intersection = intersection_width * intersection_height
    box_area = max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))
    boxes_area = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(
        0.0, boxes[:, 3] - boxes[:, 1]
    )
    union = box_area + boxes_area - intersection
    return np.divide(
        intersection,
        union,
        out=np.zeros_like(intersection, dtype=np.float32),
        where=union > 0.0,
    )


def class_aware_nms(
    boxes: np.ndarray,
    scores: np.ndarray,
    class_ids: np.ndarray,
    candidate_indices: np.ndarray,
    iou_threshold: float,
    max_detections: int,
) -> list[int]:
    """Return deterministic candidate positions ordered by descending confidence."""
    count = len(scores)
    if boxes.shape != (count, 4):
        raise PostprocessError("NMS boxes and scores have inconsistent lengths")
    if class_ids.shape != (count,) or candidate_indices.shape != (count,):
        raise PostprocessError("NMS metadata and scores have inconsistent lengths")
    order = np.lexsort((candidate_indices, class_ids, -scores))
    kept: list[int] = []
    for position in order.tolist():
        if len(kept) >= max_detections:
            break
        same_class_kept = [index for index in kept if class_ids[index] == class_ids[position]]
        if same_class_kept:
            overlaps = box_iou(boxes[position], boxes[same_class_kept])
            if bool(np.any(overlaps > iou_threshold)):
                continue
        kept.append(position)
    return kept


def restore_and_clip_box(
    box: np.ndarray,
    letterbox_metadata: dict[str, Any],
) -> np.ndarray | None:
    """Undo letterbox geometry and clip a box to source-image boundaries."""
    scale = float(letterbox_metadata["scale"])
    padding = letterbox_metadata["padding"]
    original_size = letterbox_metadata["original_size"]
    if scale <= 0.0:
        raise PostprocessError(f"invalid letterbox scale: {scale}")
    restored = np.asarray(box, dtype=np.float32).copy()
    restored[[0, 2]] = (restored[[0, 2]] - float(padding["left"])) / scale
    restored[[1, 3]] = (restored[[1, 3]] - float(padding["top"])) / scale
    width = float(original_size["width"])
    height = float(original_size["height"])
    restored[[0, 2]] = np.clip(restored[[0, 2]], 0.0, width)
    restored[[1, 3]] = np.clip(restored[[1, 3]], 0.0, height)
    if restored[2] <= restored[0] or restored[3] <= restored[1]:
        return None
    return restored


def _rounded(value: float) -> float:
    return round(float(value), 6)


def decode_yolov5_output(
    raw_output: np.ndarray,
    class_names: list[str],
    letterbox_metadata: dict[str, Any],
    config: DetectionConfig,
) -> dict[str, Any]:
    """Decode one verified YOLOv5 raw output into deterministic detections."""
    config.validate()
    if raw_output.ndim != 3 or raw_output.shape[0] != 1:
        raise PostprocessError(
            f"expected batch-1 rank-3 raw output, observed {raw_output.shape}"
        )
    expected_attributes = 5 + len(class_names)
    if raw_output.shape[2] != expected_attributes:
        raise PostprocessError(
            f"expected {expected_attributes} attributes, observed {raw_output.shape[2]}"
        )
    if raw_output.dtype != np.float32:
        raise PostprocessError(f"expected float32 raw output, observed {raw_output.dtype}")
    if not np.isfinite(raw_output).all():
        raise PostprocessError("raw output contains non-finite values")

    candidates = raw_output[0]
    objectness = candidates[:, 4]
    class_scores = candidates[:, 5:]
    if np.any(objectness < 0.0) or np.any(objectness > 1.0):
        raise PostprocessError("objectness values fall outside [0, 1]")
    if np.any(class_scores < 0.0) or np.any(class_scores > 1.0):
        raise PostprocessError("class scores fall outside [0, 1]")
    class_ids = np.argmax(class_scores, axis=1).astype(np.int64)
    selected_class_scores = class_scores[np.arange(len(candidates)), class_ids]
    confidences = objectness * selected_class_scores
    threshold_mask = confidences >= config.confidence_threshold
    candidate_indices = np.nonzero(threshold_mask)[0].astype(np.int64)

    if candidate_indices.size == 0:
        return {
            "raw_candidate_count": int(len(candidates)),
            "threshold_candidate_count": 0,
            "nms_candidate_count": 0,
            "invalid_box_count": 0,
            "detections": [],
        }

    selected_xywh = candidates[candidate_indices, :4]
    if np.any(selected_xywh[:, 2:] <= 0.0):
        raise PostprocessError("thresholded candidates contain non-positive box sizes")
    boxes = xywh_to_xyxy(selected_xywh)
    selected_confidences = confidences[candidate_indices]
    selected_class_ids = class_ids[candidate_indices]
    kept_positions = class_aware_nms(
        boxes,
        selected_confidences,
        selected_class_ids,
        candidate_indices,
        config.iou_threshold,
        config.max_detections,
    )

    detections = []
    invalid_box_count = 0
    for position in kept_positions:
        restored = restore_and_clip_box(boxes[position], letterbox_metadata)
        if restored is None:
            invalid_box_count += 1
            continue
        candidate_index = int(candidate_indices[position])
        class_id = int(selected_class_ids[position])
        input_box = boxes[position]
        input_xywh = selected_xywh[position]
        detections.append(
            {
                "candidate_index": candidate_index,
                "class_id": class_id,
                "class_name": class_names[class_id],
                "objectness": _rounded(objectness[candidate_index]),
                "class_score": _rounded(selected_class_scores[candidate_index]),
                "confidence": _rounded(selected_confidences[position]),
                "box_xywh_input": [_rounded(value) for value in input_xywh],
                "box_xyxy_input": [_rounded(value) for value in input_box],
                "box_xyxy_source": [_rounded(value) for value in restored],
            }
        )

    for rank, detection in enumerate(detections, start=1):
        detection["rank"] = rank
    return {
        "raw_candidate_count": int(len(candidates)),
        "threshold_candidate_count": int(len(candidate_indices)),
        "nms_candidate_count": int(len(kept_positions)),
        "invalid_box_count": invalid_box_count,
        "detections": detections,
    }
