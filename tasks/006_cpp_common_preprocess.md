# Task 006

## Title

Create reusable C++ detection types, configuration, preprocessing, and visualization.

## Status

Completed

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

Started: `2026-07-21T10:53:26+08:00`

Branch: `feature/pc-batch-b-cpp-ort`

Starting commit: `16687e4`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output).

Dependencies: Tasks 001–005 are `Completed`; the user explicitly approved
Checkpoint A on `2026-07-21`.

Alignment tolerances frozen before the first comparison run:

```text
metadata and tensor shape: exact match
maximum absolute tensor difference: <= 1/255 + 1e-6
mean absolute tensor difference: <= 1e-6
```

No preprocessing alignment values have been measured yet.

### Repair Attempt 1

Failure: the first required Release build stopped while compiling
`cpp/src/common/config.cpp`; `cpp/src/common/visualize.cpp` also emitted three
narrowing warnings.

Root Cause: an unsigned `cv::FileNode` sequence index was ambiguous against
OpenCV 4.6's string and integer index overloads, including index zero. Braced
construction of `cv::Scalar` also required explicit conversion from integer
color components to `double` under the configured warnings.

Files Modified: `cpp/src/common/config.cpp`, `cpp/src/common/visualize.cpp`, and
this Execution Record.

Fix Applied: sequence values are read through `cv::FileNode` iterators, and the
three deterministic color components are explicitly converted to `double`.
Warning settings and all frozen alignment tolerances remain unchanged.

Commands Re-run: the complete configure/build, test, probe, and Python comparison
sequence will be rerun.

Result: the complete Release configure/build, C++ tests, probe, and Python
comparison all passed after the fix. Repair attempts completed: `1`.

Completed: `2026-07-21T11:03:27+08:00`

### Environment

```text
GCC: 13.3.0
CMake: 3.28.3
Ninja: 1.11.1
C++ OpenCV: 4.6.0
Python: 3.12.3 from the project .venv
Python OpenCV: 4.10.0
NumPy: 1.26.4
python -m pip check: No broken requirements found
```

Read-only fixed-input hashes were verified before implementation:

```text
configs/yolov5n_v7_inference.json
  SHA256: 82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d
data/samples/images/pc_reference.jpg
  SHA256: 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
```

### Implementation and Backend Boundary

- Added plain detection, tensor, letterbox, box, and stage-timing value types.
- Added validated JSON configuration loading with frozen COCO class ordering,
  input/threshold/maximum-detection checks, and letterbox validation.
- Added OpenCV-based BGR loading, letterbox, RGB NCHW FP32 construction, inverse
  coordinate mapping, clipping, deterministic drawing, and checked image writes.
- Added a probe that writes metadata and a temporary raw FP32 tensor only below
  `build/pc-release/`.
- Added pure common-module tests and a Python comparator that uses the existing
  frozen Python preprocessing reference.
- A case-insensitive search of the common headers, common sources, probe, tests,
  and comparator found no ONNX Runtime or ncnn symbols. No inference backend,
  raw-output decoder, video pipeline, or benchmark was added.

### Commands and Results

The first required configure command exited `0`. Its associated first build
exited `1` with the compiler error and warnings recorded in Repair Attempt 1.

After the repair, the complete required build sequence was rerun from an empty
`build/pc-release`:

```text
rm -rf build/pc-release                                      exit 0
cmake -S cpp -B build/pc-release -G Ninja
      -DCMAKE_BUILD_TYPE=Release                             exit 0
cmake --build build/pc-release --parallel                    exit 0
```

The successful build completed `10/10` Ninja steps. The final build output
contained no compiler warnings.

```text
ctest --test-dir build/pc-release --output-on-failure        exit 0
edgeai_common_tests                                          PASS
edgeai_preprocess_probe with the required fixed inputs       exit 0
tests/python/compare_preprocess.py with required arguments   exit 0
python3 -m json.tool preprocess_alignment.json               exit 0
git diff --check                                             exit 0
```

CTest ran `1/1` registered executable tests with zero failures. The executable
checks configuration rejection, four letterbox geometries, RGB NCHW normalized
layout, inverse mapping, clipping, empty values, invalid image input, and
copy-preserving visualization.

### Real Preprocessing Alignment

```text
Python shape: [1, 3, 640, 640]
C++ shape: [1, 3, 640, 640]
shape match: true
metadata match: true
original size: 1280x960
target size: 640x640
resized size: 640x480
scale: 0.5
padding: left=0, top=80, right=0, bottom=80
maximum absolute tensor difference: 0.0
mean absolute tensor difference: 0.0
maximum allowed absolute difference: 0.0039225686274509805
maximum allowed mean absolute difference: 0.000001
alignment status: PASS
```

Six sampled tensor locations were also recorded from the real tensors; every
sample had an absolute difference of `0.0`.

### Evidence

```text
build/pc-release/cpp_preprocess.json
  SHA256: 5edc9e2e37f531007864c40fb359c14bf513101ee0dedaa8c6930c191c303158
  size: 785 bytes
build/pc-release/cpp_preprocess.f32
  SHA256: da7341562470c2bdc037b98bef7e6b2569a160418083e45a39fb989017e83693
  size: 4915200 bytes
results/evidence/006/preprocess_alignment.json
  SHA256: ee0576201532fbec56f2af9202ced514effb287554f94584ec3cb160b3a81930
  size: 3606 bytes
results/logs/006_cpp_common.log
  SHA256: 035c7f6137e544dbfb1323b4172a7df5a97f7114bd593a1d6ef70031bee549c5
  size: 235 bytes
```

The raw tensor and C++ metadata remain reproducible ignored build artifacts and
are not committed. The `*.log` policy keeps the real probe log local; its hash
and output summary are recorded here. The compact alignment JSON is preserved.

### Skips and Human Review

No required command or check was skipped. Task 006 produced no visualization
sample, so no new image required human visual review; the visualization API was
exercised by unit tests without persisting an image. No timing was collected or
reported as benchmark data.

Final Acceptance Criteria status: all passed. Task 006 is `Completed`. The local
atomic commit uses the required message `feat(cpp): add shared detection
preprocessing modules`; its hash is the commit containing this Execution Record.
