"""Deterministic image loading and YOLOv5 input construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np


class PreprocessError(RuntimeError):
    """Raised when an image cannot produce the frozen input tensor."""


def load_bgr_image(path: Path) -> np.ndarray:
    """Read one nonempty three-channel uint8 image with OpenCV."""
    if path.is_symlink():
        raise PreprocessError(f"reference image must not be a symbolic link: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        raise PreprocessError(f"reference image is missing or empty: {path}")
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise PreprocessError(f"OpenCV failed to decode reference image: {path}")
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise PreprocessError(
            f"expected uint8 BGR image, observed shape={image.shape} dtype={image.dtype}"
        )
    return image


def letterbox(
    image: np.ndarray,
    target_size: tuple[int, int] = (640, 640),
    pad_color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, dict[str, Any]]:
    """Resize with fixed interpolation and symmetric constant padding."""
    if image.ndim != 3 or image.shape[2] != 3:
        raise PreprocessError(f"letterbox expects HWC three-channel input: {image.shape}")
    target_height, target_width = target_size
    if target_height <= 0 or target_width <= 0:
        raise PreprocessError(f"invalid target size: {target_size}")
    original_height, original_width = image.shape[:2]
    if original_height <= 0 or original_width <= 0:
        raise PreprocessError(f"invalid source size: {image.shape}")

    scale = min(target_height / original_height, target_width / original_width)
    resized_width = int(round(original_width * scale))
    resized_height = int(round(original_height * scale))
    if (resized_width, resized_height) != (original_width, original_height):
        resized = cv2.resize(
            image,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
    else:
        resized = image.copy()

    horizontal_padding = target_width - resized_width
    vertical_padding = target_height - resized_height
    left = int(round(horizontal_padding / 2 - 0.1))
    right = int(round(horizontal_padding / 2 + 0.1))
    top = int(round(vertical_padding / 2 - 0.1))
    bottom = int(round(vertical_padding / 2 + 0.1))
    output = cv2.copyMakeBorder(
        resized,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=pad_color,
    )
    if output.shape[:2] != (target_height, target_width):
        raise PreprocessError(
            f"letterbox produced {output.shape[:2]}, expected {(target_height, target_width)}"
        )

    metadata = {
        "original_size": {"width": original_width, "height": original_height},
        "target_size": {"width": target_width, "height": target_height},
        "scale": float(scale),
        "resized_size": {"width": resized_width, "height": resized_height},
        "padding": {"left": left, "top": top, "right": right, "bottom": bottom},
        "pad_color_bgr": list(pad_color),
        "interpolation": "cv2.INTER_LINEAR",
    }
    return output, metadata


def prepare_image_tensor(
    image: np.ndarray,
    target_size: tuple[int, int] = (640, 640),
) -> tuple[np.ndarray, dict[str, Any]]:
    """Convert BGR HWC uint8 pixels into contiguous RGB NCHW FP32 [0, 1]."""
    letterboxed, metadata = letterbox(image, target_size=target_size)
    rgb = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    chw = np.transpose(rgb, (2, 0, 1))
    normalized = chw.astype(np.float32) / np.float32(255.0)
    tensor = np.ascontiguousarray(normalized[np.newaxis, ...])
    if not np.isfinite(tensor).all():
        raise PreprocessError("input tensor contains non-finite values")
    metadata["transforms"] = [
        "BGR_TO_RGB",
        "HWC_TO_CHW",
        "uint8_TO_float32",
        "divide_by_255",
        "add_batch_dimension",
    ]
    return tensor, metadata


def load_and_prepare_image(
    path: Path,
    target_size: tuple[int, int] = (640, 640),
) -> tuple[np.ndarray, dict[str, Any]]:
    """Load an image and construct its deterministic input tensor."""
    return prepare_image_tensor(load_bgr_image(path), target_size=target_size)
