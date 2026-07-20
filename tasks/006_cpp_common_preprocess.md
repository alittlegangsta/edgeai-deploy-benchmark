# Task 006

## Title

Create reusable C++ detection types, configuration, preprocessing, and visualization.

## Status

Planned

## Batch

Batch B

## Dependencies

Task 005 (`Completed`) and human approval of Checkpoint A.

## Recommended Branch

`feature/pc-batch-b-cpp-ort`

## Recommended Commit

`feat(cpp): add shared detection preprocessing modules`

## Goal

Implement inference-backend-independent C++17 modules that both ONNX Runtime and
ncnn can reuse, and prove C++ preprocessing matches the approved Python reference.

## Why This Task Exists

Sharing data types, configuration, letterbox preprocessing, postprocessing-ready
metadata, and drawing prevents backend adapters from drifting into separate
pipelines and makes cross-backend comparisons meaningful.

## Knowledge Covered

- Stable C++ detection and tensor data contracts.
- Explicit letterbox geometry and contiguous NCHW layout.
- Configuration validation and deterministic visualization.
- Unit testing pure geometry.
- Python/C++ preprocessing alignment.

## Scope

Add plain C++ value types for model geometry, letterbox metadata, detections, and
stage timing; validated configuration loading; OpenCV-based preprocessing; box
mapping/clipping utilities; and deterministic visualization. Add a small probe
that emits preprocessing metadata for comparison with Python.

Do not include ONNX Runtime, ncnn, model loading, inference, raw-output decoding
that depends on a backend, video processing, or formal benchmarking.

## Allowed Files

```text
TASKS.md
tasks/006_cpp_common_preprocess.md
cpp/CMakeLists.txt
cpp/include/edgeai/common/detection.hpp
cpp/include/edgeai/common/config.hpp
cpp/include/edgeai/common/preprocess.hpp
cpp/include/edgeai/common/visualize.hpp
cpp/src/common/config.cpp
cpp/src/common/preprocess.cpp
cpp/src/common/visualize.cpp
cpp/apps/preprocess_probe.cpp
cpp/tests/test_common.cpp
tests/python/compare_preprocess.py
results/evidence/006/preprocess_alignment.json
results/logs/006_cpp_common.log
```

The Python reference, fixed configuration, model manifest, and reference image
are read-only inputs. Temporary tensor data under `build/pc-release/` is a
reproducible build artifact and must not be committed.

## Forbidden Files

- ONNX Runtime or ncnn includes, libraries, sessions, extractors, or adapters.
- Changes to Python reference behavior, golden data, frozen config, or model.
- Video or benchmark implementation.
- Vendored dependencies, FetchContent, or global CMake include directories.
- Any file outside Allowed Files.

## Inputs

- Approved Task 005 fixed model/image/config hashes and Python preprocessing.
- Existing C++17, CMake, Ninja, and OpenCV environment from Task 001.
- `configs/yolov5n_v7_inference.json` as read-only configuration.

## Expected Outputs

- One backend-neutral `edgeai_common` CMake target.
- Reusable detection/config/preprocessing/visualization headers and sources.
- Unit-test and preprocessing-probe executables.
- Real JSON quantifying Python/C++ input-shape, letterbox, sampled-value,
  max-absolute, and mean-absolute differences.

## Implementation Requirements

- Use C++17, target-level include/link/feature settings, no compiler extensions,
  and `-Wall -Wextra -Wpedantic` for GCC/Clang.
- Keep data structures plain and independent of runtime-specific tensor classes.
- Validate input dimensions, thresholds, maximum detections, class names, and
  letterbox settings when loading configuration.
- Match Python's interpolation, padding color, scale calculation, split-padding
  rounding, BGR-to-RGB, HWC-to-CHW, FP32 conversion, normalization, batch layout,
  and contiguous channel order.
- Preserve original size, resized size, scale, and each padding edge.
- Provide box inverse mapping and clipping without decoding model output.
- Draw from a copy with deterministic colors/text formatting; report image-write
  failures.
- The probe must write machine-readable metadata and a temporary raw FP32 tensor
  for the comparison process; remove or leave it only under ignored build output.
- Freeze alignment tolerance before the first run: identical metadata and shape,
  maximum absolute tensor difference `<= 1/255 + 1e-6`, and mean absolute
  difference `<= 1e-6`. Do not loosen it after failure.

## Build Commands

```bash
rm -rf build/pc-release
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/pc-release --parallel
```

## Run Commands

```bash
mkdir -p results/evidence/006 results/logs
./build/pc-release/edgeai_preprocess_probe \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --metadata build/pc-release/cpp_preprocess.json \
  --tensor build/pc-release/cpp_preprocess.f32 \
  2>&1 | tee results/logs/006_cpp_common.log
PYTHONPATH=python python3 tests/python/compare_preprocess.py \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --cpp-metadata build/pc-release/cpp_preprocess.json \
  --cpp-tensor build/pc-release/cpp_preprocess.f32 \
  --output results/evidence/006/preprocess_alignment.json
```

## Test Commands

```bash
ctest --test-dir build/pc-release --output-on-failure
python3 -m json.tool results/evidence/006/preprocess_alignment.json >/dev/null
git diff --check
```

## Acceptance Criteria

- A backend-neutral C++ library builds in Release without warnings.
- No ONNX Runtime or ncnn symbol appears in the common modules.
- Configuration validation rejects malformed values.
- Unit tests cover letterbox geometry, layout, mapping, clipping, empty values,
  and invalid input.
- The real C++ probe and Python comparator run on the fixed image.
- Shapes and all letterbox metadata match exactly.
- Tensor max absolute difference is `<= 1/255 + 1e-6` and mean absolute
  difference is `<= 1e-6`.
- Real alignment JSON/logs are preserved; no tensor values are invented.
- Build, tests, run, and `git diff --check` pass with only Allowed Files changed.
- Any visual sample produced is reviewed by a human before acceptance.

## Evidence to Preserve

CMake/compiler/OpenCV versions, configure/build output, warning count, unit-test
results, image/config hashes, both preprocessing metadata sets, alignment metrics,
probe/comparator exit codes, attempts, visual review, diff check, and Git status.

## Automatic Retry Rules

Use at most three complete repair loops for common-module defects. Do not loosen
alignment tolerances or change Python/frozen config. A persistent mismatch,
missing dependency, or visual judgment immediately invokes the stop protocol.

## Human Stop Conditions

Stop for any protocol condition, any proposed configuration/reference change,
alignment outside tolerance, ambiguous interpolation/rounding behavior, warning
requiring suppressed diagnostics, or output requiring visual approval.

## Codex Responsibilities

Keep modules backend neutral, run Release builds and all comparisons, preserve
real metrics, record repairs, and refuse to hide mismatches.

## User Responsibilities

Approve Batch B, provide/maintain the local toolchain, review alignment evidence
and any image, and decide how to resolve cross-language mismatch.

## Known Risks

- Python and C++ OpenCV builds may round resize pixels differently.
- Locale or JSON numeric parsing can affect configuration.
- Text rendering is not appropriate for pixel-exact visualization comparison.
- Too-permissive common structures can leak backend assumptions later.

## Completion Report Format

Report files, tool versions, build/warnings, common API scope, unit tests,
preprocessing shapes/metadata/difference metrics, visual review, attempts, skips,
risks, and final Git status with real-versus-static labels.

## Execution Record

Not started. No preprocessing alignment values have been measured.
