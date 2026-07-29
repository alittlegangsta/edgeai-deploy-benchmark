#!/usr/bin/env python3
"""Generate the ignored Task 020 constant-frame lossless FFV1/AVI fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import cv2


EXPECTED_SOURCE_SHA256 = (
    "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
)
FRAME_COUNT = 30
FPS = 5.0
FOURCC = "FFV1"


class FixtureError(RuntimeError):
    """The generated fixture does not satisfy the frozen Task 020 contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", type=Path)
    return parser.parse_args()


def generate(source: Path, output: Path) -> dict[str, object]:
    if not source.is_file() or source.stat().st_size <= 0:
        raise FixtureError(f"source image is missing or empty: {source}")
    observed_source_hash = sha256_file(source)
    if observed_source_hash != EXPECTED_SOURCE_SHA256:
        raise FixtureError(
            "source image SHA256 differs from the frozen Task 014 input"
        )
    frame = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0 or frame.ndim != 3 or frame.shape[2] != 3:
        raise FixtureError("source image is not a decodable BGR image")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    writer = cv2.VideoWriter(
        str(output),
        cv2.VideoWriter_fourcc(*FOURCC),
        FPS,
        (int(frame.shape[1]), int(frame.shape[0])),
        True,
    )
    if not writer.isOpened():
        raise FixtureError("OpenCV could not open the lossless FFV1/AVI writer")
    for _ in range(FRAME_COUNT):
        writer.write(frame)
    writer.release()
    if not output.is_file() or output.stat().st_size <= 0:
        raise FixtureError("generated video is missing or empty")

    capture = cv2.VideoCapture(str(output))
    if not capture.isOpened():
        raise FixtureError("generated video cannot be reopened")
    metadata = {
        "width": int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH))),
        "height": int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))),
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "reported_frame_count": int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT))),
        "fourcc": int(round(capture.get(cv2.CAP_PROP_FOURCC))),
        "backend": capture.getBackendName(),
    }
    decoded = 0
    maximum_absolute_pixel_delta = 0
    while True:
        ok, decoded_frame = capture.read()
        if not ok:
            break
        if decoded_frame.shape != frame.shape:
            raise FixtureError(f"decoded frame {decoded} geometry differs")
        delta = cv2.absdiff(decoded_frame, frame)
        maximum_absolute_pixel_delta = max(
            maximum_absolute_pixel_delta, int(delta.max())
        )
        decoded += 1
    capture.release()
    if (
        metadata["width"] != frame.shape[1]
        or metadata["height"] != frame.shape[0]
        or not math.isclose(float(metadata["fps"]), FPS, abs_tol=0.01)
        or metadata["reported_frame_count"] != FRAME_COUNT
        or decoded != FRAME_COUNT
    ):
        raise FixtureError(f"generated video metadata/count differs: {metadata}")

    return {
        "schema_version": 1,
        "task": "020",
        "generator": "OpenCV VideoWriter",
        "opencv_version": cv2.__version__,
        "source_image": {
            "path": str(source),
            "sha256": observed_source_hash,
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0]),
            "channels": int(frame.shape[2]),
        },
        "video": {
            "path": str(output),
            "sha256": sha256_file(output),
            "size_bytes": output.stat().st_size,
            "container": "AVI",
            "requested_codec": "FFV1 lossless",
            "requested_fourcc": FOURCC,
            "fps": FPS,
            "frame_count": FRAME_COUNT,
            "decoded_frame_count": decoded,
            "width": metadata["width"],
            "height": metadata["height"],
            "capture_backend": metadata["backend"],
            "reported_fourcc_integer": metadata["fourcc"],
            "maximum_absolute_pixel_delta_from_source": maximum_absolute_pixel_delta,
        },
        "status": "PASS",
    }


def main() -> int:
    arguments = parse_args()
    try:
        result = generate(arguments.source, arguments.output)
    except (FixtureError, OSError, cv2.error) as error:
        print(f"Task 020 fixture generation: FAIL: {error}", file=sys.stderr)
        return 1
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.metadata is not None:
        arguments.metadata.parent.mkdir(parents=True, exist_ok=True)
        temporary = arguments.metadata.with_suffix(arguments.metadata.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(arguments.metadata)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
