# Task 011

## Title

Implement C++ ncnn single-image and video inference and compare it with ORT.

## Status

Completed

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
results/benchmarks/pc_cpp_ncnn_summary.json
results/benchmarks/pc_cpp_ncnn_summary.csv
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
- Real ncnn raw benchmark JSON plus machine-readable summary, CSV, and validation
  evidence using the Task 009 statistics/method.

## Implementation Requirements

- Validate the Task 010 TorchScript/pnnx-derived ncnn manifest, param/bin hashes,
  model version, config,
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
- Before the first ncnn correctness run, preserve the Task 010 preregistration:
  equal detection count and classes, finite in-bounds boxes, unchanged thresholds
  and golden result; target one-to-one class-matched IoU `>= 0.99` with absolute
  confidence difference `<= 0.01`; hard floor IoU `>= 0.98` with confidence
  difference `<= 0.02`. Passing the target may proceed normally. Passing only
  the hard floor must stop for human explanation; falling below it fails Task 011.
  Never weaken either gate after observing results.
- Reuse Task 008 video reader/writer and timing regions. ncnn inference timing
  excludes video read, visualization, and video write.
- Reopen and decode the output video; require human review of image/video.
- Reuse Task 009 benchmark config, warmup, repeat, thread count, Release proof,
  stage boundaries, statistics, memory/CPU metric, and FPS formula unchanged.
- Run only C++ ncnn in this task: five sequential, independent processes with
  warmup `10` and repeat `100` per process. Preserve all 500 formal samples and
  every outlier. Do not modify or rerun Task 009 Python/C++ ORT evidence.
- Each formal iteration must run preprocess, ncnn inference, and postprocess.
  Read the image once per process; do not cache the preprocessed tensor. Exclude
  image read, model/session load, drawing, and output writes from pipeline time.
- Record `model_load_ms` once per round; record
  `process_cpu_percent_one_core_basis` over the 100 formal iterations and Linux
  process-level peak RSS from `getrusage(RUSAGE_SELF).ru_maxrss * 1024`.
- Use the Task 009 shared nearest-rank implementation for per-round and aggregate
  mean/P50/P90/min/max. Calculate pipeline FPS only as `1000 / aggregate mean
  pipeline_total_ms`, and record fastest/slowest sample plus the five-round mean
  spread. A spread above 10% is a mandatory stop.
- Run an untimed C++ ORT/ncnn correctness comparison before warmup and after the
  formal loop in every process. Both must pass the preregistered target gate.
- A candidate cross-campaign table may cite immutable Task 009 ORT results and
  new Task 011 ncnn results only if it states that the campaigns were not run in
  a synchronized three-backend order. The six-round three-backend permutation
  campaign is reserved for Task 012 and must not run here.
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
  --profile ncnn-preregistered \
  --min-iou 0.99 \
  --max-confidence-delta 0.01 \
  --output results/evidence/011/ort_ncnn_comparison.json
./build/pc-all-release/edgeai_ncnn_video \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output results/videos/cpp_ncnn_reference.mp4 \
  --output-json results/evidence/011/cpp_ncnn_video.json \
  2>&1 | tee results/logs/011_cpp_ncnn_video.log
rm -f \
  results/benchmarks/pc_cpp_ncnn.json \
  results/benchmarks/pc_cpp_ncnn_summary.json \
  results/benchmarks/pc_cpp_ncnn_summary.csv \
  results/evidence/011/ncnn_benchmark_validation.json \
  results/logs/011_cpp_ncnn_benchmark.log
set -o pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
for round in 1 2 3 4 5; do
  ./build/pc-all-release/edgeai_benchmark_ncnn \
    --benchmark-config configs/benchmark_pc.json \
    --ncnn-manifest models/yolov5n-v7.0/ncnn_manifest.json \
    --reference-detections results/evidence/007/cpp_ort_detections.json \
    --round "$round" \
    --output results/benchmarks/pc_cpp_ncnn.json \
    2>&1 | tee -a results/logs/011_cpp_ncnn_benchmark.log
done
PYTHONPATH=python python3 tests/python/compare_detections.py \
  --benchmark-input results/benchmarks/pc_cpp_ncnn.json \
  --benchmark-config configs/benchmark_pc.json \
  --benchmark-summary results/benchmarks/pc_cpp_ncnn_summary.json \
  --benchmark-csv results/benchmarks/pc_cpp_ncnn_summary.csv \
  --benchmark-report results/evidence/011/ncnn_benchmark_validation.json \
  2>&1 | tee -a results/logs/011_cpp_ncnn_benchmark.log
```

## Test Commands

```bash
ctest --test-dir build/pc-all-release --output-on-failure
python3 -m json.tool results/evidence/011/cpp_ncnn_detections.json >/dev/null
python3 -m json.tool results/evidence/011/ort_ncnn_comparison.json >/dev/null
python3 -m json.tool results/evidence/011/cpp_ncnn_video.json >/dev/null
python3 -m json.tool results/benchmarks/pc_cpp_ncnn.json >/dev/null
python3 -m json.tool results/benchmarks/pc_cpp_ncnn_summary.json >/dev/null
python3 -m json.tool results/evidence/011/ncnn_benchmark_validation.json >/dev/null
test -s results/benchmarks/pc_cpp_ncnn_summary.csv
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
- ORT/ncnn counts/classes match one-to-one and pass the target IoU `>= 0.99` and
  confidence-delta `<= 0.01` gate. A hard-floor-only result (`0.98`/`0.02`) is
  preserved but cannot be accepted without a human decision.
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

Started: `2026-07-21T17:29:44+08:00`

Branch: `feature/pc-batch-c-ncnn-acceptance`

Starting commit: `a6aded0` (`feat(ncnn): add reproducible model conversion`)

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output). Task 010 is `Completed`; the pinned ncnn manifest, ignored model
artifacts, SDK, fixed image/video, and completed ORT evidence exist as read-only
inputs. No Task 011 inference, result, image, video, or benchmark had run before
the target/hard correctness gates above were written.

Repair attempt 1:

- Failure: `ctest --test-dir build/pc-all-release --output-on-failure` exited 8;
  `edgeai_ncnn_detector_tests` could not open the repository-relative param path
  while CTest used the build directory as its working directory.
- Root cause: Task 010 intentionally records repository-relative generated-model
  paths, but the initial adapter resolved them only against the process working
  directory.
- Files modified: `cpp/src/backends/ncnn_detector.cpp`.
- Fix applied: resolve relative manifest artifacts by searching ancestors of the
  absolute manifest path, preserving the recorded path and SHA256 contract.
- Commands to re-run: Release build, full CTest, standard-library Python unittest
  discovery, then the real fixed-image run and registered comparison.
- Separate optional check: `.venv/bin/python -m pytest -q` exited 1 because pytest
  is not installed. Task 011 does not require pytest; no package was installed and
  the repository's tests use `unittest`.

Repair attempt 1 result:

- `cmake --build build/pc-all-release --parallel` exited 0 without warnings.
- `ctest --test-dir build/pc-all-release --output-on-failure` exited 0; 11/11
  CTest cases passed, including the real zero-input ncnn load/layout test.
- `PYTHONPATH=python python -m unittest discover -s tests/python -p
  'test_*.py' -v` exited 0; 58/58 tests passed.

Fixed-image execution:

- `edgeai_ncnn_image` exited 0 using ncnn `1.0.20240410`, CPU, one thread,
  FP32 `in0 [1,3,640,640]` and `out0 [1,25200,85]`.
- The real output contains five detections: `keyboard`, `tv`, `cup`, `mouse`,
  and `mouse`. The second lower-confidence `mouse` is preserved for visual review
  and was not hidden by a threshold or golden-result change.
- `compare_detections.py --profile ncnn-preregistered --min-iou 0.99
  --max-confidence-delta 0.01` exited 0 with `PASS_TARGET`: detection count 5,
  classes matched one-to-one, minimum IoU `0.999997080011`, and maximum absolute
  confidence difference `2.02655792236e-06`.
- `results/images/cpp_ncnn_reference.png` is a decodable 1280x960 PNG, SHA256
  `57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.
- Structured evidence SHA256 values: detections
  `ca215f4cb66b5cecee1ba3551ac8527f45b21c77ce5ed3accdb86996b185648e`;
  comparison
  `6af0faf13d2960e7ccf851047f7f0967eb7f81f45ff8d6a072b9de36865c5ab4`;
  image log
  `072b28c0ca455a59c82a0527a62dea8309956811c0c498d4c8f38205c424adad`.
- The printed single-run stage timings are diagnostic only and are not formal
  benchmark evidence.

### Blocking Report

Current Task: Task 011, C++ ncnn image/video inference and benchmark integration

Current Status: Blocked

Last Successful Step: Real fixed-image ncnn inference, JSON validation, PNG
decode validation, and preregistered ORT/ncnn comparison all passed.

Failed Command: N/A; the successful fixed-image run generated an output that
requires the protocol's mandatory human visual judgment.

Exit Code: 0 for the image run and comparison that triggered this stop.

Relevant Error: No command error. `results/images/cpp_ncnn_reference.png` has
`visual_review=PENDING_HUMAN_REVIEW`; protocol section Correctness requires a stop.

Files Changed: `TASKS.md`, `tasks/011_cpp_ncnn_inference.md`, `cpp/CMakeLists.txt`,
`cpp/include/edgeai/backends/ncnn_detector.hpp`,
`cpp/src/backends/ncnn_detector.cpp`, `cpp/apps/ncnn_image.cpp`,
`cpp/apps/ncnn_video.cpp`, `cpp/tests/test_ncnn_detector.cpp`,
`tests/python/compare_detections.py`, `results/images/cpp_ncnn_reference.png`,
`results/evidence/011/cpp_ncnn_detections.json`, and
`results/evidence/011/ort_ncnn_comparison.json`. The generated image log is
preserved at `results/logs/011_cpp_ncnn_image.log` and remains Git-ignored.

Attempts Made: One repair attempt completed successfully for manifest-relative
artifact resolution. No correctness-gate repair was attempted or needed.

Why Automatic Recovery Is Unsafe: Numerical agreement cannot replace visual
confirmation of labels, clipping, coordinate placement, duplicate suppression,
and whether the known low-confidence mouse false positive remains semantically
consistent with the approved ORT result.

Exact Human Action Required: Open `results/images/cpp_ncnn_reference.png` and
compare it with `results/images/cpp_ort_reference.png`. Confirm image dimensions,
the five labels and boxes, no systematic coordinate shift, no new duplicate or
out-of-bounds boxes, label clipping, and whether the low-confidence second
`mouse` remains the known earbud-case model false positive rather than an ncnn
implementation error.

Commands to Resume: Re-read `AGENTS.md`, `TASKS.md`, the PC protocol, and this
file; check branch/status; rerun the fixed-image command and registered comparison
to verify the reviewed artifact identity; if human review is approved, restore
Task 011 to `In Progress`, run the full 240-frame ncnn video path, and stop again
for its required visual review before any formal benchmark.

Git Status: Task 011 source/status/evidence paths are modified or untracked as
listed above; no Task 011 commit exists, and no unrelated tracked file is changed.

### Fixed-Image Visual Review Recovery

Resumed: `2026-07-21T18:49:01+08:00`

The user approved the exact reviewed PNG and `PASS_TARGET` evidence. Repository
revalidation reproduced its identity before restoring this task to `In Progress`:

```text
reviewed PNG: 1280x960 BGR, decodable
reviewed PNG SHA256: 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
detections JSON SHA256: ca215f4cb66b5cecee1ba3551ac8527f45b21c77ce5ed3accdb86996b185648e
comparison JSON SHA256: 6af0faf13d2960e7ccf851047f7f0967eb7f81f45ff8d6a072b9de36865c5ab4
detections: 5 / 5 with identical classes
minimum class-matched IoU: 0.9999970800108954
maximum confidence delta: 2.0265579223632812e-06
comparison status: PASS_TARGET
```

Human review confirms correct `keyboard`, `tv`, `cup`, and true-mouse boxes and
labels. The lower-confidence second `mouse` remains the same earbud-case false
positive as the ORT baseline, without an ncnn-specific coordinate or confidence
anomaly. No new scale, coordinate, class, duplicate, boundary, label-placement,
or clipping defect was observed. This is a model limitation rather than a pnnx,
ncnn inference, shared postprocessing, or visualization difference.

The model-lineage distinction remains explicit: Python ORT and C++ ORT use the
same frozen ONNX file, while C++ ncnn uses a separate TorchScript/pnnx model
generated from the same frozen YOLOv5n v7.0 source weights and validated for
semantic equivalence.

### Release Revalidation and Video Execution

Stopped: `2026-07-21T18:54:37+08:00`

The fixed identities were reverified before rebuilding:

```text
ncnn tag: 20240410
ncnn revision: 56775de50990ab7f16627efdcf5529b49541206f
ncnn runtime version: 1.0.20240410
weights SHA256: 4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3
frozen ONNX SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
TorchScript SHA256: 1ea5813fac07158ca4ff5eb98b273353b1bf5baafdd46f1ced4ab33835247892
ncnn param SHA256: 72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
ncnn bin SHA256: 658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0
ORT manifest SHA256: 764f3e4980c1f6b18ea245262af99703d13e817fedc52bf97bbfc5a1389f06c2
TorchScript manifest SHA256: 24401522387fd91d6afe6dfbc7029140aea564a8ea3cd09f0db55763ad14e8f2
ncnn manifest SHA256: 9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff
libncnn.a SHA256: f1936728d19ce288ad7180926670ac7f1833107a13cc9446d178d2bef340fcc1
```

The source status still reports only the Task 010-documented, pre-existing
`M python/pybind11` submodule-pointer difference. The provenance confirms Python
was disabled and this submodule was not used by the runtime build.

The complete `build/pc-all-release` directory was removed and configured again
with CMake 3.28.3, GCC 13.3.0, OpenCV 4.6.0, ONNX Runtime 1.18.1, the fixed ncnn
root, Ninja, and `CMAKE_BUILD_TYPE=Release`. Configuration and all 39 build steps
exited 0 without warnings. This build includes `edgeai_ncnn_backend`, image,
video, and per-round benchmark targets. The benchmark target was only built and
its invalid-argument path tested; no formal sample was generated.

Validation after the clean build:

```text
CTest: 12/12 passed
Python unittest discovery: 58/58 passed
pytest: not run and not required
fixed-image inference: exited 0
fixed-image comparison: PASS_TARGET
fixed-image PNG SHA256: 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
reproduced detections JSON SHA256: b30f6e404bbf7978dfda23dc0ea5c02b31fdcc1c62f723a445e623b62add6f8a
reproduced comparison JSON SHA256: 37fa4959d66050f81292855784e1115f7c487b9311ab906d34f4eda7ff6d8fa9
runtime contract: CPU, FP32, 1 thread, Vulkan/FP16/BF16/INT8 disabled
git diff --check: passed before video execution
```

The regenerated PNG is byte-identical to the human-reviewed PNG. Detection
count/classes and the approved IoU/confidence metrics are unchanged; only the
diagnostic timing fields changed the structured-evidence hashes.

The fixed input video remained Git-ignored and decoded independently as exactly
240 H.264/yuv420p frames at 1280x720 and 30 FPS with SHA256
`275b88daea99ba797ebf65c788f06a4edcc853ad18b1f8fc81ccc17b79cc74d7`.
The ncnn video command then exited 0 and produced:

```text
reported input frames: 240
decoded input frames: 240
processed frames: 240
failed frames: 0
written frames: 240
verified output frames: 240
output codec/pixel format: H.264 / yuv420p
output dimensions: 1280x720
output container FPS: 30
output duration: 8.000000 seconds
output size: 1790126 bytes
output video SHA256: af3720d602a3a28ea885f164bc1642eab9bd9874685b804a0806cf9504089bc9
video JSON SHA256: 66a54923c94bcb32bb1868c8b2d1770af10e4e22ed9d3fc21c300298eed27400
video log SHA256: 8b219393f61dae3a15900796b7559708668843595809ee3629e1c9e454cba286
```

Independent JSON checks verified all 240 frame records, runtime flags, exact
frame counts, and `pipeline_total = preprocess + inference + postprocess` for
every frame. OpenCV reopened and decoded all 240 output frames at 1280x720. The
30 FPS value is container playback metadata and is not reported as actual ncnn
processing throughput. Diagnostic aggregate timings remain only in the generated
JSON/log and are not Task 011 formal benchmark data.

### Video Visual Review Blocking Report

Current Task: Task 011, C++ ncnn image/video inference and benchmark integration

Current Status: Blocked

Last Successful Step: The full 240-frame ncnn video pipeline, structured JSON
validation, ffprobe inspection, and independent complete output decode passed.

Failed Command: N/A; the successful video run generated an output requiring the
protocol's mandatory human visual judgment.

Exit Code: 0 for video inference, JSON checks, ffprobe, and full decode.

Relevant Error: No command error. `results/evidence/011/cpp_ncnn_video.json`
records `visual_review=PENDING_HUMAN_REVIEW`; formal benchmark execution is also
deferred because performance evidence requires human confirmation and the exact
ncnn placement relative to Task 009's already-completed alternating order must
not be silently invented.

Files Changed: `TASKS.md`, `tasks/011_cpp_ncnn_inference.md`, `cpp/CMakeLists.txt`,
`cpp/include/edgeai/backends/ncnn_detector.hpp`,
`cpp/src/backends/ncnn_detector.cpp`, `cpp/apps/ncnn_image.cpp`,
`cpp/apps/ncnn_video.cpp`, `cpp/apps/benchmark_ncnn.cpp`,
`cpp/tests/test_ncnn_detector.cpp`, `tests/python/compare_detections.py`,
`results/images/cpp_ncnn_reference.png`,
`results/evidence/011/cpp_ncnn_detections.json`,
`results/evidence/011/ort_ncnn_comparison.json`, and
`results/evidence/011/cpp_ncnn_video.json`. The output video and image/video logs
are preserved but Git-ignored as required.

Attempts Made: One earlier repair attempt completed successfully. No video
repair was needed; the first complete 240-frame video run passed.

Why Automatic Recovery Is Unsafe: Automated frame-count and decode checks cannot
judge playback continuity, frame/box synchronization, semantic plausibility,
label placement, or encoding quality. Running formal data before this visual
gate would violate the required stop. The historical Task 009 data alternated
Python ORT and C++ ORT; adding ncnn to an interleaving without an explicit order
could change the benchmark method or require new ORT evidence outside this task.

Exact Human Action Required: Play `results/videos/cpp_ncnn_reference.mp4` from
start to finish and compare representative sections with the input and approved
C++ ORT video. Confirm duration/order/speed, no corrupt/black/skipped frames,
boxes synchronized to the current frame, no historical-box residue or systematic
coordinate shift, correct clipping/labels near boundaries, and acceptable encode
quality. Identify any model false positives separately from pipeline defects.
Also confirm whether the next formal step should run five independent ncnn
process rounds against the already-approved immutable Task 009 results, or
provide an explicit three-backend per-round order and corresponding Allowed Files
if fresh Python/C++ ORT samples are required for literal interleaving.

Commands to Resume: Re-read the repository instructions, task table, PC protocol,
Task 010, and this file; check branch/status and all fixed hashes; rerun the full
video command and decode validation to reproduce the reviewed artifact; after
visual and exact benchmark-order approval, restore Task 011 to `In Progress`,
finalize the recorded benchmark invocation/validator, run five independent
Release ncnn rounds without replacing any sample, preserve all raw data, and stop
again immediately for performance review.

Git Status: Task 011 source/status/image/JSON evidence paths are modified or
untracked; the large output video and logs are ignored; no Task 011 commit exists,
and no unrelated tracked file is changed.

### Video Review and Benchmark Recovery

Resumed: `2026-07-21T19:04:07+08:00`

The user approved the full human video review. The reviewed 240-frame ncnn video
plays from start to finish with correct duration, order, speed, continuity, and
frame-synchronous boxes. No black/corrupt/skipped frames, historical-box residue,
one-frame lag, systematic coordinate shift, abnormal scale, boundary overflow,
or label-clipping defect was observed. The visualization is consistent with the
C++ ORT video. Occasional `book`, `bed`, `cat`, and `dog` detections are preserved
as model false positives, not attributed to ncnn, pnnx, coordinate restoration,
or the video pipeline. The 30 FPS value is container playback metadata, not
measured processing throughput, and the video timing remains diagnostic only.

The user also froze the remaining Task 011 benchmark campaign: run only C++ ncnn
as five independent processes, each with 10 warmups and 100 formal full-pipeline
iterations. Task 009 Python/C++ ORT raw JSON, CSV, hashes, and conclusions are
immutable read-only inputs and must not be regenerated or overwritten. The ncnn
campaign uses the same 640x640 batch-1 FP32 image, one ncnn/OpenCV thread, CPU
only, scheduler-managed affinity, WSL2 environment, exact stage boundaries,
nearest-rank statistics, CPU metric, peak-RSS scope, and FPS formula. Correctness
must pass the target ORT/ncnn gate before and after every round. All samples and
outliers remain preserved; spread above 10% stops the task.

Any candidate three-backend view at this point is explicitly cross-campaign:
the ORT rows come from the approved Task 009 campaign and ncnn from Task 011.
It is not a synchronized three-backend comparison. Task 012 alone may run the
separately approved six-round full-permutation campaign with 600 new samples per
backend and new filenames; that campaign is forbidden during Task 011.

### Formal ncnn Benchmark Execution

Stopped: `2026-07-21T19:13:30+08:00`

Before the formal campaign, a clean Release configuration and all 39 build steps
completed using GCC 13.3.0, CMake 3.28.3, OpenCV 4.6.0, ONNX Runtime 1.18.1,
and ncnn 1.0.20240410. The build emitted no warnings. CTest passed 12/12 and the
required standard-library Python unittest discovery passed 58/58. `pytest` was
not run and is not a Task 011 acceptance command.

The fixed-image run again produced the same human-reviewed PNG SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`
and the same five detections. The regenerated comparison remained `PASS_TARGET`
with minimum class-matched IoU `0.999997080011` and maximum confidence delta
`2.02655792236e-06`. The 240-frame video rerun produced the same reviewed video
SHA256 `af3720d602a3a28ea885f164bc1642eab9bd9874685b804a0806cf9504089bc9`.
ffprobe and an independent OpenCV decode confirmed H.264/yuv420p, 1280x720,
30 FPS container metadata, 8.000000 seconds, and all 240 frames. All 240 JSON
frame records passed the stage-sum and runtime checks. Two initial temporary
inline audit assertions used incorrect JSON field/index assumptions; after
inspecting the real schema, the corrected read-only audit passed. No product
code, model, threshold, output, or acceptance rule was changed for those checks.

The formal Task 011 campaign then ran exactly once. Five independent Release
processes (PIDs 4, 6, 8, 10, and 12) each loaded the fixed image once, loaded the
ncnn param/bin once, recorded model load, ran 10 warmups, and recorded 100 full
preprocess/inference/postprocess samples. Correctness before warmup and after the
formal loop was `PASS_TARGET` for every round. CPU, FP32, one ncnn thread, one
OpenCV thread, scheduler-managed affinity, disabled pinning, and disabled
Vulkan/FP16/BF16/INT8 were validated. All 500 samples and outliers are preserved.

Per-round pipeline results:

```text
round  model_load_ms  mean_ms    P50_ms     P90_ms     min_ms     max_ms     CPU one-core %  peak_rss_bytes
1      30.144124      69.895691  69.585100  72.215106  66.849924  74.611258  111.109192      187932672
2      29.158383      70.073017  69.861764  71.991236  67.632012  74.494036  111.108057      188166144
3      28.777215      70.111099  70.042967  72.309551  66.990389  74.069472  111.107006      188170240
4      29.470123      69.622281  69.169363  71.764464  66.913363  77.137607  111.108404      187973632
5      28.641495      70.144438  69.820598  71.802441  67.461633  75.408164  111.098710      187789312
```

Nearest-rank aggregate results from the same Task 009 shared implementation:

```text
stage           mean_ms     P50_ms     P90_ms     min_ms     max_ms
preprocess       1.616431    1.578966   1.740760   1.491675   2.474641
inference       64.654359   64.463607  66.652167  61.567599  71.524894
postprocess      3.698515    3.648324   3.879366   3.538345   4.705110
pipeline_total  69.969305   69.759019  72.083295  66.849924  77.137607
pipeline FPS: 14.291981 (1000 / aggregate mean pipeline_total_ms)
fastest sample: aggregate 99, round 1 iteration 99, 66.849924 ms
slowest sample: aggregate 373, round 4 iteration 73, 77.137607 ms
five-round pipeline mean maximum relative difference: 0.749985%
stability gate: PASS (limit 10%)
```

`process_cpu_percent_one_core_basis` is process user+system CPU time divided by
wall time, multiplied by 100. Here roughly 111% indicates some additional
process/runtime activity beyond continuous use of one logical CPU; one configured
ncnn thread does not mean the entire process has exactly one thread. Peak RSS is
process-level memory from process startup through formal measurement completion,
including the executable, dynamic libraries, runtime, model, and loaded state; it
is not pure model memory.

The raw and derived evidence passed an independent 500-sample reconstruction,
exact integer-nanosecond stage-sum check, 24-row CSV check, correctness checks,
and stability calculation:

```text
raw JSON SHA256: 0719578b3da1c036e7fb20eadac295b7e7aa19ccf92302f01a8ac88ed77bb673
summary JSON SHA256: 2750462a117cfccd461b6aeb7e9d40aa18fff868e0ba087255fca398941f08e1
summary CSV SHA256: 88326b374e7651da9f108ff5d78cd8e9f14aa95c73609dc6f8d24765fabe8411
validation JSON SHA256: 2d11f0d8e7e38573b25e702d3bb90a88c6d16dcf9cd4ee7527f65830bf19b594
benchmark log SHA256: 191ae031d38c7ae654bffa85eef3ae57e0c30a1824a3d34ef6fabef3394934d4
```

The immutable Task 009 hashes remained exactly `125f1fa1...7c41` for Python ORT
raw JSON, `8b8a6cfb...c5c8e` for C++ ORT raw JSON, `4ac971e4...be63` for the ORT
CSV, and `b3edd666...fcfc` for its validation report. No Task 009 command was
rerun and no Task 009 evidence was modified. Any later three-backend observation
must retain the documented cross-campaign limitation; Task 012's new balanced
campaign has not started.

### Formal Benchmark Human-Review Blocking Report

Current Task: Task 011, C++ ncnn image/video inference and benchmark integration

Current Status: Blocked

Last Successful Step: The one approved five-process ncnn campaign generated all
500 raw samples; shared-statistics derivation, independent validation, stability,
correctness, JSON/CSV checks, and `git diff --check` passed.

Failed Command: N/A; the first complete formal ncnn data set was generated
successfully and reached the mandatory performance-review stop.

Exit Code: 0 for all five benchmark processes and the final validator.

Relevant Error: No command error. Evidence status is
`PENDING_HUMAN_REVIEW`; Task 011 cannot be marked `Completed` until the user
reviews the environment, raw sample count, five-round stability, performance,
CPU/RSS scope, and outliers.

Files Changed: `TASKS.md`, `tasks/011_cpp_ncnn_inference.md`, `cpp/CMakeLists.txt`,
`cpp/include/edgeai/backends/ncnn_detector.hpp`,
`cpp/src/backends/ncnn_detector.cpp`, `cpp/apps/ncnn_image.cpp`,
`cpp/apps/ncnn_video.cpp`, `cpp/apps/benchmark_ncnn.cpp`,
`cpp/tests/test_ncnn_detector.cpp`, `tests/python/compare_detections.py`,
`results/images/cpp_ncnn_reference.png`,
`results/evidence/011/cpp_ncnn_detections.json`,
`results/evidence/011/ort_ncnn_comparison.json`,
`results/evidence/011/cpp_ncnn_video.json`,
`results/benchmarks/pc_cpp_ncnn.json`,
`results/benchmarks/pc_cpp_ncnn_summary.json`,
`results/benchmarks/pc_cpp_ncnn_summary.csv`, and
`results/evidence/011/ncnn_benchmark_validation.json`. Generated video and logs
remain ignored and uncommitted.

Attempts Made: One earlier product repair loop fixed manifest-relative model
paths and passed complete revalidation. No benchmark repair or selective rerun
occurred; the formal campaign succeeded on its first execution and is frozen.

Why Automatic Recovery Is Unsafe: Performance authenticity, interpretation of
the ncnn-vs-ORT cross-campaign difference, acceptance of observed outliers, and
approval of the approximately 111% process CPU measurements require the mandated
human decision. Re-executing could replace approved first-run samples, and starting
Task 012 would cross a task/checkpoint boundary.

Exact Human Action Required: Review
`results/benchmarks/pc_cpp_ncnn.json`,
`results/benchmarks/pc_cpp_ncnn_summary.json`,
`results/benchmarks/pc_cpp_ncnn_summary.csv`, and
`results/evidence/011/ncnn_benchmark_validation.json`. Confirm 500 samples,
five independent rounds, 0.749985% stability spread, all preserved min/max
samples, correctness before/after each round, the 14.291981 pipeline FPS formula,
process-level CPU/RSS scope, and the cross-campaign limitation against immutable
Task 009 ORT results.

Commands to Resume: Re-read repository instructions, task table, PC protocol,
Tasks 009–011; verify branch/status and every recorded raw/derived hash; do not
rerun the frozen campaign; rerun only deterministic JSON/CSV/statistics/test/Git
checks. If the user approves this exact data set, record approval, mark Task 011
`Completed`, stage only Allowed Files, create the specified local atomic commit,
and then assess Task 012 under the Batch C protocol.

Git Status: Task 011 source/status/image/JSON/CSV evidence paths are modified or
untracked exactly as listed above; output video and logs are ignored; Task 009
evidence is unchanged; no Task 011 commit exists and Task 012 has not started.

### Formal Benchmark Human Approval Recovery

Resumed: `2026-07-22T10:11:20+08:00`

The user approved the exact first Task 011 ncnn campaign as the formal current
C++ ncnn result. Approval covers all five independent processes, 10 warmups and
100 measured iterations per process, all 500 preserved raw samples and outliers,
all ten before/after `PASS_TARGET` correctness checks, the `0.749985%` five-round
mean spread and `PASS` stability gate, and the recorded process-level CPU/RSS
definitions. No sample may be deleted, replaced, selectively rerun, or edited.

The approved aggregate values are unchanged:

```text
preprocess mean: 1.616431 ms
inference mean: 64.654359 ms
postprocess mean: 3.698515 ms
pipeline mean: 69.969305 ms
pipeline P50/P90/min/max: 69.759019 / 72.083295 / 66.849924 / 77.137607 ms
pipeline FPS: 14.291981
five-round mean spread: 0.749985%
```

`process_cpu_percent_one_core_basis` remains the exact CPU metric. Approximately
100% means sustained use of one logical CPU; the preserved values near 111% show
limited additional process, Runtime, or system-thread activity even though the
ncnn inference thread count is 1. CPU affinity was scheduler managed, pinning was
disabled, and the environment was WSL2. Peak RSS remains the complete process
peak, including executable, dynamic libraries, Runtime, model, and loaded state;
it is not pure model memory.

The approved interpretation boundary is:

```text
The Task 009 ORT and Task 011 ncnn measurements use the same benchmark
methodology and configuration, but were collected in separate campaigns.
Their comparison is therefore a staged observation rather than the final
order-balanced three-backend result.
```

Reading the two approved campaigns shows that C++ ncnn and C++ ORT preprocess
means (`1.616431` versus `1.655221` ms) and postprocess means (`3.698515` versus
`3.684627` ms) are close in this environment. The larger staged difference is
in inference (`64.654359` versus `41.528575` ms); ncnn pipeline mean is
`69.969305` ms versus C++ ORT `46.868423` ms. These are cross-campaign observations,
not a synchronized fair three-backend result, universal backend ranking,
language-level conclusion, ARM result, or cross-platform kernel conclusion.
Task 012 alone may run the new balanced three-backend campaign.

Recovery did not execute any benchmark process. The four approved Task 011
evidence SHA256 values matched exactly. Re-derivation from the unchanged raw JSON
was directed only to `/tmp`; regenerated summary JSON and CSV were byte-for-byte
equal to repository evidence, and the validation report was semantically equal
after normalizing only its temporary output paths. Independent reconstruction
again confirmed 5 rounds, 5 distinct process IDs, 500 samples, exact integer
stage sums, all 10 correctness gates, retained fastest/slowest samples, and
spread `0.749985253751%`. Task 009's four approved evidence hashes were unchanged.
CTest passed 12/12 and the required Python unittest discovery passed 58/58.

Task 011 is restored to `In Progress` only to record this approval, perform final
whitespace/Allowed Files/cached-diff checks, transition to `Completed`, and create
the authorized local atomic commit. Task 012 remains `Planned` and must not start
in this turn.

### Completion Record

Completed: `2026-07-22T10:12:04+08:00`

Every Acceptance Criterion has passed through real build, test, image, video,
comparison, benchmark, deterministic evidence validation, and required human
review. Final pre-completion checks found exactly 18 changed Task 011 Allowed
Files, no unrelated path, no tracked or untracked whitespace error, and unchanged
Task 009 evidence. The approved Task 011 raw benchmark was not rerun, overwritten,
truncated, filtered, or edited during recovery or completion.

Task 011 is `Completed`. The specified local atomic commit is created immediately
after explicit Allowed Files staging and cached-diff inspection. Its SHA is
reported to the user after Git creates the commit. Task 012 remains `Planned`;
no Task 012 source, benchmark, result, README, acceptance report, or state change
was started.
