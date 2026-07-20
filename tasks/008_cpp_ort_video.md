# Task 008

## Title

Add C++ ONNX Runtime video-file inference with separated stage timings.

## Status

Planned

## Batch

Batch B

## Dependencies

Task 007 (`Completed`).

## Recommended Branch

`feature/pc-batch-b-cpp-ort`

## Recommended Commit

`feat(cpp): add ONNX Runtime video inference`

## Goal

Process a real local video file through the approved C++ ONNX Runtime pipeline,
write an annotated output video, and report video I/O and inference stages
separately without misrepresenting encoding as model latency.

## Why This Task Exists

Video introduces decoding, frame iteration, timestamps, writer configuration, and
encoding costs that a single-image application does not expose. Those costs must
remain distinct from model work.

## Knowledge Covered

- OpenCV video capture/writer lifecycle.
- Frame-by-frame detector reuse.
- Timing-boundary design.
- Video metadata and output validation.
- Graceful handling of malformed frames and writer errors.

## Scope

Add one C++ file-to-file ONNX Runtime video CLI. Reuse the Task 006 common modules
and Task 007 backend/session/decoder. Record video read, preprocess, inference,
postprocess, visualization, and video write durations separately per frame and in
aggregate.

Do not add camera/streaming support, ncnn, concurrency, frame batching, formal
benchmark percentiles, or changes to model/preprocessing/postprocessing behavior.

## Allowed Files

```text
TASKS.md
tasks/008_cpp_ort_video.md
cpp/CMakeLists.txt
cpp/include/edgeai/common/video_pipeline.hpp
cpp/src/common/video_pipeline.cpp
cpp/apps/ort_video.cpp
cpp/tests/test_video_pipeline.cpp
data/samples/videos/pc_reference.mp4
results/videos/cpp_ort_reference.mp4
results/evidence/008/cpp_ort_video.json
results/logs/008_cpp_ort_video.log
```

The Task 006/007 implementation, frozen model/config, and local video are inputs.
The input/output videos remain ignored and must not be committed.

## Forbidden Files

- Changes to detector, preprocessing, postprocessing, model contract, or frozen
  thresholds.
- ncnn, camera, network stream, asynchronous queue, or benchmark framework code.
- Downloaded/video-converted input hidden from provenance.
- Any file outside Allowed Files.

## Inputs

- Completed Task 007 native ORT detector and verified local runtime.
- A user-supplied, licensed local `pc_reference.mp4` with SHA256, codec/container,
  frame count, dimensions, and frame-rate metadata recorded from real inspection.
- A locally available OpenCV build capable of decoding and encoding the selected
  formats.

If the codec is unsupported, do not install/download codecs or silently choose a
different input/output format; stop and report the exact failure.

## Expected Outputs

- `edgeai_ort_video` reading a file and writing an annotated file.
- Real JSON containing input/output metadata, processed/written frame counts,
  detections per frame, and separately aggregated stage durations.
- A nonempty output video that can be reopened and decoded.
- A genuine log including runtime/model/video identity.

## Implementation Requirements

- Validate arguments, model/config/video hashes, capture open, positive geometry,
  frame-rate policy, writer open, frame decode, and write completion.
- Create one ORT session and reuse it for all frames.
- Preserve source frame order and dimensions; document the output codec/fourcc and
  actual writer-reported behavior.
- Time video read, preprocess, inference, postprocess, visualization, and video
  write as distinct non-overlapping regions with a monotonic clock.
- Report a measured pipeline total separately. It must state whether it excludes
  read, visualization, and write; inference must never include encoding.
- Keep per-frame timing records or sufficient real aggregates to audit totals.
- Distinguish decoded, processed, failed, and written frame counts. Reject silent
  frame drops and return nonzero on mid-stream errors.
- Draw only after postprocessing and never feed annotated frames back into the
  model.
- Reopen the generated video, decode at least first/middle/last reachable frames,
  and validate dimensions/nonempty content. Human visual review remains required.
- Single-run video timings are diagnostics for this task, not formal benchmark
  values.

## Build Commands

```bash
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root>
cmake --build build/pc-release --parallel
```

## Run Commands

```bash
mkdir -p results/videos results/evidence/008 results/logs
./build/pc-release/edgeai_ort_video \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output results/videos/cpp_ort_reference.mp4 \
  --output-json results/evidence/008/cpp_ort_video.json \
  2>&1 | tee results/logs/008_cpp_ort_video.log
test -s results/videos/cpp_ort_reference.mp4
file results/videos/cpp_ort_reference.mp4
```

## Test Commands

```bash
ctest --test-dir build/pc-release --output-on-failure
python3 -m json.tool results/evidence/008/cpp_ort_video.json >/dev/null
./build/pc-release/edgeai_ort_video --verify-output \
  results/videos/cpp_ort_reference.mp4 \
  --expected-metadata results/evidence/008/cpp_ort_video.json
git diff --check
```

## Acceptance Criteria

- Release build succeeds without warnings and reuses the Task 007 backend.
- Real input video identity/metadata and output codec are preserved in evidence.
- All decodable source frames are processed and written in order, with no silent
  drops; counts agree with the documented capture behavior.
- Read, preprocess, inference, postprocess, visualization, and write measurements
  are separate, and encoding is never presented as inference.
- The output video is nonempty, reopens successfully, and decoded verification
  confirms expected frame dimensions and content.
- Detection structures remain valid for every processed frame.
- Human visual review approves representative output frames/video.
- Error-path tests, real run, output verification, `ctest`, and
  `git diff --check` pass with only Allowed Files changed.

## Evidence to Preserve

Environment/runtime versions, input SHA/metadata, configure/build output, frame
counts, stage timing definitions and real aggregates, output SHA/size/codec,
decode verification, representative detection summaries, human review, tests,
attempts, and Git status.

## Automatic Retry Rules

At most three full repair loops may address video-pipeline defects. Never fold
write/read time into inference, silently drop frames, switch codecs/input, or
change detector settings to pass. Codec/environment errors and visual judgment
require an immediate stop.

## Human Stop Conditions

Stop for unsupported codecs, ambiguous frame count/rate, corrupted input, frame
drops, abnormal detections, required output-format change, visual review, or any
protocol condition.

## Codex Responsibilities

Maintain honest timing boundaries, preserve frame/order/count evidence, validate
the output by decoding it, avoid benchmark claims, and report codec errors exactly.

## User Responsibilities

Provide the licensed local video and working codecs, decide output-format changes,
inspect representative frames/video, and approve detection plausibility.

## Known Risks

- Container frame counts may be estimates.
- OpenCV codec availability varies by build.
- Variable-frame-rate input complicates output timing.
- Video writing can dominate end-to-end time.

## Completion Report Format

Report files, input/output identity and metadata, build result, frame counts,
timing boundaries and diagnostic values, decode/visual verification, error tests,
attempts, skips, risks, and final Git status.

## Execution Record

Not started. No video, detections, frame counts, or timings have been generated.
