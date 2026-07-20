# Task 007

## Title

Implement C++ ONNX Runtime single-image detection and compare it with Python.

## Status

Planned

## Batch

Batch B

## Dependencies

Task 006 (`Completed`).

## Recommended Branch

`feature/pc-batch-b-cpp-ort`

## Recommended Commit

`feat(cpp): add ONNX Runtime image inference`

## Goal

Add a narrow C++ ONNX Runtime CPU adapter and single-image CLI that reuse Task
006, print actual model I/O, emit real detections, and agree with the approved
Python reference within frozen tolerances.

## Why This Task Exists

It validates native runtime integration while preserving a known-good model,
preprocessing pipeline, postprocessing contract, and comparison target.

## Knowledge Covered

- Target-level ONNX Runtime discovery and linking.
- Runtime sessions, tensor lifetime, and CPU provider options.
- Model metadata validation and raw-output decoding.
- Cross-language structured detection matching.
- Native error handling and artifact generation.

## Scope

Implement only C++ CPU ONNX Runtime single-image inference. Reuse Task 006 for
configuration, preprocessing, detection types, coordinate mapping, and drawing.
Add the minimum YOLOv5 raw-output decoder and comparison tooling.

Do not add video, ncnn, formal benchmark loops, downloads, dependency fetching,
or alternate model-contract handling.

## Allowed Files

```text
TASKS.md
tasks/007_cpp_ort_single_image.md
cpp/CMakeLists.txt
cpp/include/edgeai/backends/ort_detector.hpp
cpp/include/edgeai/common/postprocess.hpp
cpp/src/backends/ort_detector.cpp
cpp/src/common/postprocess.cpp
cpp/apps/ort_image.cpp
cpp/tests/test_postprocess.cpp
tests/python/compare_detections.py
results/images/cpp_ort_reference.png
results/evidence/007/cpp_ort_detections.json
results/evidence/007/python_cpp_ort_comparison.json
results/logs/007_cpp_ort_image.log
```

The ONNX Runtime installation, frozen model/manifest/config, common modules,
Python result, golden fixture, and reference image are read-only inputs.

## Forbidden Files

- Downloaded or vendored ONNX Runtime and FetchContent.
- Changes to Task 002 contract, Python reference/golden result, or Task 006
  preprocessing behavior.
- Video, ncnn, model conversion, or benchmark implementation.
- Global include/library directories when target-level settings work.
- Any file outside Allowed Files.

## Inputs

- Completed Task 006 common library and alignment evidence.
- A user-provided compatible local ONNX Runtime C/C++ installation.
- Frozen model, manifest, inference config, reference image, and Python golden
  detection result.

Missing/incompatible headers or libraries require a stop. CMake must not download
or substitute ONNX Runtime.

## Expected Outputs

- An `edgeai_ort_backend` target and `edgeai_ort_image` executable.
- Actual printed and structured session I/O metadata.
- A nonempty annotated C++ result image and structured detection JSON.
- Real Python/C++ comparison JSON with one-to-one matches and tolerance metrics.

## Implementation Requirements

- Discover ONNX Runtime from an explicit local installation/root and fail clearly
  when headers/library/version are missing or incompatible.
- Use C++17 target-level includes, links, features, warnings, and no extensions.
- Validate model SHA and manifest contract before inference.
- Use CPU execution, record the actual runtime version/provider, and make intra-
  and inter-op thread counts explicit.
- Enumerate and print actual input/output names, shapes, and dtypes; compare all
  values to Task 002 and stop on mismatch.
- Keep runtime-owned names and tensor buffers alive for the required duration.
- Reuse Task 006 input tensor without hidden transpose, normalization, or resize.
- Decode objectness and class scores, use combined confidence, convert `xywh` to
  `xyxy`, apply frozen class-aware NMS, inverse-map, clip, and deterministically
  order detections.
- Emit the same structured fields as Python, including model/image/config hashes.
- Compare one-to-one by class with identical detection count, IoU `>= 0.99`, and
  absolute confidence difference `<= 0.001`. Freeze these values before the first
  acceptance run and do not weaken them.
- Return nonzero for bad arguments, missing files, contract/SHA mismatch, runtime
  errors, non-finite output, or artifact-write failure.

## Build Commands

```bash
rm -rf build/pc-release
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root>
cmake --build build/pc-release --parallel
```

Record the resolved ONNX Runtime include, library, and version. Do not replace a
configuration failure with automatic fetching.

## Run Commands

```bash
mkdir -p results/images results/evidence/007 results/logs
./build/pc-release/edgeai_ort_image \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/images/cpp_ort_reference.png \
  --output-json results/evidence/007/cpp_ort_detections.json \
  2>&1 | tee results/logs/007_cpp_ort_image.log
PYTHONPATH=python python3 tests/python/compare_detections.py \
  --reference tests/fixtures/python_ort_golden.json \
  --candidate results/evidence/007/cpp_ort_detections.json \
  --min-iou 0.99 \
  --max-confidence-delta 0.001 \
  --output results/evidence/007/python_cpp_ort_comparison.json
test -s results/images/cpp_ort_reference.png
file results/images/cpp_ort_reference.png
```

## Test Commands

```bash
ctest --test-dir build/pc-release --output-on-failure
python3 -m json.tool results/evidence/007/cpp_ort_detections.json >/dev/null
python3 -m json.tool results/evidence/007/python_cpp_ort_comparison.json >/dev/null
test -s results/images/cpp_ort_reference.png
git diff --check
```

## Acceptance Criteria

- Release configure/build succeeds without warnings using the verified local
  ONNX Runtime installation.
- The executable prints real ONNX Runtime version/provider and complete model I/O.
- Runtime I/O and model SHA exactly match Task 002.
- The common Task 006 input tensor path is reused unchanged.
- Real inference, decoding, NMS, coordinate restore, clipping, and image writing
  succeed.
- The result image is nonempty/decodable and receives human visual approval.
- C++ and Python detection counts/classes match one-to-one; every matched IoU is
  at least `0.99` and confidence delta no more than `0.001`.
- Unit/integration/invalid-input tests and `git diff --check` pass.
- Only Allowed Files changed and all evidence is real.

## Evidence to Preserve

Compiler/CMake/OpenCV/ONNX Runtime versions and paths, Release build log, provider
and thread settings, model I/O, hashes, C++ detections/image, comparison matches
and worst deltas, test output, visual decision, attempts, and final Git status.

## Automatic Retry Rules

At most three full repair loops are allowed for adapter/decoder defects. Do not
change Python, model contract, thresholds, preprocessing, or tolerances. Missing
runtime dependencies, I/O/SHA mismatch, out-of-tolerance results, or visual doubt
requires an immediate stop.

## Human Stop Conditions

All protocol conditions apply, especially dependency/version issues, any model
I/O mismatch, Python/C++ comparison failure, abnormal/empty detections, image
review, or a request to change threading/model/preprocessing.

## Codex Responsibilities

Integrate only the local dependency, print and verify real I/O, reuse common code,
preserve true results, run comparisons/tests, and report failures exactly.

## User Responsibilities

Provide a compatible local ONNX Runtime installation, review the result image and
comparison, and make decisions about dependency or contract incompatibilities.

## Known Risks

- ONNX Runtime distributions expose different CMake/pkg-config layouts.
- C++ API behavior differs across runtime versions.
- NMS ordering can diverge for equal scores.
- Small resize or floating-point differences can move threshold-edge detections.

## Completion Report Format

Report files, dependency resolution/version, build/warnings, model I/O, provider
and threads, real detections/image, Python comparison metrics, tests, attempts,
stops/skips, risks, and Git status.

## Execution Record

Not started. No C++ ORT detection, comparison, image, or timing has been produced.
