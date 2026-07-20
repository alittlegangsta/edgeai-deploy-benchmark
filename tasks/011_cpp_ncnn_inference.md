# Task 011

## Title

Implement C++ ncnn single-image and video inference and compare it with ORT.

## Status

Planned

## Batch

Batch C

## Dependencies

Task 010 (`Completed`).

## Recommended Branch

`feature/pc-batch-c-ncnn-acceptance`

## Recommended Commit

`feat(ncnn): add image video and benchmark inference`

## Goal

Add one C++ ncnn CPU backend that reuses the approved common image, video, and
benchmark modules; produce real single-image/video results; compare detections
with C++ ORT; and measure ncnn using the frozen Task 009 method.

## Why This Task Exists

The PC stage needs a second native backend tested under the same model identity,
preprocessing, postprocessing, samples, timing boundaries, and evidence schema.

## Knowledge Covered

- ncnn network/extractor lifecycle and tensor binding.
- Reuse of backend-neutral preprocessing/postprocessing.
- Cross-runtime detection alignment.
- Shared file-video pipeline operation.
- Comparable Release benchmark integration.

## Scope

Implement a narrow ncnn detector adapter plus image, video, and benchmark entry
points. Use Task 010 blob/artifact manifest, Task 006 common processing, Task 008
video pipeline, and Task 009 benchmark framework. Compare the fixed-image result
with approved C++ ORT output.

Do not alter model conversion, model/threshold/preprocessing contracts, ORT or
Python behavior, benchmark methodology, add GPU/Vulkan, or add ARM code.

## Allowed Files

```text
TASKS.md
tasks/011_cpp_ncnn_inference.md
cpp/CMakeLists.txt
cpp/include/edgeai/backends/ncnn_detector.hpp
cpp/src/backends/ncnn_detector.cpp
cpp/apps/ncnn_image.cpp
cpp/apps/ncnn_video.cpp
cpp/apps/benchmark_ncnn.cpp
cpp/tests/test_ncnn_detector.cpp
tests/python/compare_detections.py
results/images/cpp_ncnn_reference.png
results/videos/cpp_ncnn_reference.mp4
results/evidence/011/cpp_ncnn_detections.json
results/evidence/011/ort_ncnn_comparison.json
results/evidence/011/cpp_ncnn_video.json
results/evidence/011/ncnn_benchmark_validation.json
results/benchmarks/pc_cpp_ncnn.json
results/logs/011_cpp_ncnn_image.log
results/logs/011_cpp_ncnn_video.log
results/logs/011_cpp_ncnn_benchmark.log
```

Tasks 002–010 implementation, manifests, configs, fixtures, models, and existing
results are read-only inputs. Result video and ncnn binary remain uncommitted.

## Forbidden Files

- Model conversion, param/bin edits, source ONNX, frozen manifests/contracts,
  thresholds, common preprocessing semantics, or golden-result changes.
- Duplicated private preprocessing/video/benchmark implementations.
- Vulkan/GPU, quantization, FP16, ARM, camera, streaming, downloads, or vendoring.
- Hand-edited detections, video summaries, or benchmark values.
- Any file outside Allowed Files.

## Inputs

- Completed Task 010 param/bin and manifest with verified hashes/blob names.
- Completed Task 006 common modules, Task 008 video pipeline, and Task 009
  benchmark framework/config.
- Approved ORT detections, fixed image/video, and local pinned ncnn runtime.

## Expected Outputs

- `edgeai_ncnn_backend`, `edgeai_ncnn_image`, `edgeai_ncnn_video`, and
  `edgeai_benchmark_ncnn` targets.
- Real annotated image/video and structured ncnn detections/video metadata.
- Real ORT/ncnn one-to-one comparison JSON.
- Real ncnn benchmark JSON using the Task 009 schema/method.

## Implementation Requirements

- Validate ONNX-derived ncnn manifest, param/bin hashes, model version, config,
  and sample hashes before use.
- Bind only input/output blobs observed in Task 010; stop on missing/unexpected
  blobs or tensor layout/shape.
- Use CPU only with Vulkan and FP16 storage/arithmetic disabled. Record actual
  ncnn version and explicit thread count.
- Convert Task 006 contiguous FP32 CHW data to ncnn input without a second resize,
  color conversion, transpose, or normalization.
- Adapt real ncnn raw output to the shared Task 007 postprocessor; do not fork NMS,
  coordinate mapping, clipping, ordering, or visualization.
- Emit the same structured fields/hashes as ORT.
- Freeze ORT/ncnn comparison before first run: equal detection count and class,
  one-to-one class-matched IoU `>= 0.98`, and absolute confidence difference
  `<= 0.02`. Never weaken these tolerances after failure.
- Reuse Task 008 video reader/writer and timing regions. ncnn inference timing
  excludes video read, visualization, and video write.
- Reopen and decode the output video; require human review of image/video.
- Reuse Task 009 benchmark config, warmup, repeat, thread count, Release proof,
  stage boundaries, statistics, memory/CPU metric, and FPS formula unchanged.
- Return nonzero on every invalid input, hash/blob/shape mismatch, runtime error,
  non-finite output, or artifact failure.

## Build Commands

```bash
rm -rf build/pc-all-release
cmake \
  -S cpp \
  -B build/pc-all-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root> \
  -DNCNN_ROOT=<verified-local-ncnn-root>
cmake --build build/pc-all-release --parallel
```

## Run Commands

```bash
mkdir -p \
  results/images \
  results/videos \
  results/evidence/011 \
  results/benchmarks \
  results/logs
./build/pc-all-release/edgeai_ncnn_image \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/images/cpp_ncnn_reference.png \
  --output-json results/evidence/011/cpp_ncnn_detections.json \
  2>&1 | tee results/logs/011_cpp_ncnn_image.log
PYTHONPATH=python python3 tests/python/compare_detections.py \
  --reference results/evidence/007/cpp_ort_detections.json \
  --candidate results/evidence/011/cpp_ncnn_detections.json \
  --min-iou 0.98 \
  --max-confidence-delta 0.02 \
  --output results/evidence/011/ort_ncnn_comparison.json
./build/pc-all-release/edgeai_ncnn_video \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output results/videos/cpp_ncnn_reference.mp4 \
  --output-json results/evidence/011/cpp_ncnn_video.json \
  2>&1 | tee results/logs/011_cpp_ncnn_video.log
./build/pc-all-release/edgeai_benchmark_ncnn \
  --benchmark-config configs/benchmark_pc.json \
  --output results/benchmarks/pc_cpp_ncnn.json \
  2>&1 | tee results/logs/011_cpp_ncnn_benchmark.log
```

## Test Commands

```bash
ctest --test-dir build/pc-all-release --output-on-failure
python3 -m json.tool results/evidence/011/cpp_ncnn_detections.json >/dev/null
python3 -m json.tool results/evidence/011/ort_ncnn_comparison.json >/dev/null
python3 -m json.tool results/evidence/011/cpp_ncnn_video.json >/dev/null
python3 scripts/validate_benchmark.py \
  --config configs/benchmark_pc.json \
  --inputs results/benchmarks/pc_cpp_ncnn.json \
  --report results/evidence/011/ncnn_benchmark_validation.json
test -s results/images/cpp_ncnn_reference.png
test -s results/videos/cpp_ncnn_reference.mp4
git diff --check
```

## Acceptance Criteria

- Release build succeeds without warnings against the pinned Task 010 ncnn.
- Artifact hashes and observed blob contract match before inference.
- CPU/FP32/thread settings are explicit and no Vulkan path is active.
- Task 006 preprocessing and shared postprocessing/visualization are reused.
- Real single-image inference succeeds and annotated output is nonempty/decodable.
- ORT/ncnn counts/classes match one-to-one; every IoU is `>= 0.98` and confidence
  delta `<= 0.02`.
- Real video processes/writes all expected frames, preserves separated timing
  regions, reopens/decodes, and never counts encoding as inference.
- Image and representative video output receive human visual approval.
- Formal ncnn benchmark uses unchanged Task 009 Release method and schema; real
  results receive human performance review.
- All tests, comparisons, validations, and `git diff --check` pass.
- Only Allowed Files changed and no result is fabricated or hand-edited.

## Evidence to Preserve

ncnn/model/config/sample hashes and versions, Release build output, threads and
blob/tensor metadata, image/video results, ORT/ncnn match metrics, frame/timing
summary, benchmark samples/statistics/FPS/resource metrics, visual/performance
reviews, tests, attempts, and Git status.

## Automatic Retry Rules

At most three full repair loops may fix ncnn-adapter code. Never change converter,
models, common processing, thresholds, comparison tolerances, benchmark method,
or measured output. Any blob/shape mismatch, cross-backend tolerance failure,
codec issue, suspicious benchmark, or visual decision is an immediate stop.

## Human Stop Conditions

Every protocol condition applies, including dependency/version problems,
unexpected tensors, ORT/ncnn mismatch, empty/abnormal detections, visual review,
outliers/environment drift, or any proposed change to shared/model/benchmark rules.

## Codex Responsibilities

Keep the adapter narrow, maximize actual reuse, validate all identities, execute
real comparisons/video/benchmark, preserve truth, and stop for required reviews.

## User Responsibilities

Maintain the pinned ncnn environment, review image/video and comparison evidence,
confirm ncnn performance authenticity, and decide any incompatibility or method
change.

## Known Risks

- ncnn layer/operator interpretation may differ from ONNX Runtime.
- Blob layout conversion errors can look like plausible low-confidence output.
- Numeric kernels and NMS tie ordering may differ.
- One shared thread count may not be optimal, but changing it breaks comparability.

## Completion Report Format

Report files, versions/hashes, Release build, blob/tensor contract, real image and
video results, ORT/ncnn comparison metrics, video timing boundaries, ncnn benchmark
table/method, human reviews, tests, attempts, risks, and final Git status.

## Execution Record

Not started. No ncnn inference, detection, image, video, or benchmark exists.
