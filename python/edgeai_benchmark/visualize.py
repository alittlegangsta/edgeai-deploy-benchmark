"""Deterministic OpenCV visualization for structured detections."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np


class VisualizationError(RuntimeError):
    """Raised when detections cannot be rendered or saved."""


def class_color(class_id: int) -> tuple[int, int, int]:
    """Return a stable high-contrast BGR color for a class ID."""
    return (
        int((37 * class_id + 67) % 192 + 32),
        int((17 * class_id + 149) % 192 + 32),
        int((29 * class_id + 101) % 192 + 32),
    )


def draw_detections(
    image: np.ndarray,
    detections: list[dict[str, Any]],
) -> np.ndarray:
    """Draw on a copy so preprocessing source pixels are never mutated."""
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise VisualizationError(
            f"expected uint8 BGR image, observed shape={image.shape} dtype={image.dtype}"
        )
    output = image.copy()
    height, width = output.shape[:2]
    for detection in detections:
        x1, y1, x2, y2 = detection["box_xyxy_source"]
        left = min(max(int(round(x1)), 0), width - 1)
        top = min(max(int(round(y1)), 0), height - 1)
        right = min(max(int(round(x2)), 0), width - 1)
        bottom = min(max(int(round(y2)), 0), height - 1)
        if right <= left or bottom <= top:
            raise VisualizationError(f"invalid detection box after raster clipping: {detection}")
        color = class_color(int(detection["class_id"]))
        label = f"{detection['class_name']} {float(detection['confidence']):.3f}"
        cv2.rectangle(output, (left, top), (right, bottom), color, 2, cv2.LINE_8)
        (text_width, text_height), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            1,
        )
        label_top = max(0, top - text_height - baseline - 4)
        label_right = min(width - 1, left + text_width + 4)
        cv2.rectangle(
            output,
            (left, label_top),
            (label_right, top),
            color,
            cv2.FILLED,
            cv2.LINE_8,
        )
        cv2.putText(
            output,
            label,
            (left + 2, max(text_height + 1, top - baseline - 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return output


def save_png(path: Path, image: np.ndarray) -> None:
    """Write a PNG and reject silent OpenCV write failures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise VisualizationError(f"OpenCV failed to write output image: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        raise VisualizationError(f"output image is missing or empty after write: {path}")
