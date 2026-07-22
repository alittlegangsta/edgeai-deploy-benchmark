# Task 008

## Title

Add C++ ONNX Runtime video-file inference with separated stage timings.

## Status

Completed

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

Started: `2026-07-21T11:44:15+08:00`

Branch: `feature/pc-batch-b-cpp-ort`

Starting commit: `aeb2b52`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output after the Task 007 atomic commit).

Dependency: Task 007 is `Completed` in local commit `aeb2b52`. Task 008 is now
`In Progress`; no video, detections, frame counts, timings, source changes, or
artifacts have been produced yet.

### Input Audit and Blocking Report

Stopped: `2026-07-21T11:44:47+08:00`

The required local input check ran from the repository root:

```text
test -s data/samples/videos/pc_reference.mp4
exit status: 1
error: required video is missing or empty: data/samples/videos/pc_reference.mp4
```

`find data/samples -maxdepth 3 -type f -print` found only the existing Task 003
reference image. No video input was found. No substitute, generated video,
download, codec installation, source implementation, build, inference, output
video, detection, or timing result was attempted. Repair attempts: `0`; this is
a missing user-provided input and mandatory stop, not a code defect.

```text
Current Task: Task 008
Current Status: Blocked
Last Successful Step: Task 007 completed and was committed locally as aeb2b52; Task 008 branch/dependency/clean-worktree checks passed
Failed Command: test -s data/samples/videos/pc_reference.mp4
Exit Code: 1
Relevant Error: required video is missing or empty: data/samples/videos/pc_reference.mp4
Files Changed: TASKS.md; tasks/008_cpp_ort_video.md
Attempts Made: 0 repair attempts; stopped during required-input validation before implementation
Why Automatic Recovery Is Unsafe: Task 008 requires a real user-supplied licensed video; generating, downloading, substituting, or inventing its provenance is forbidden and would invalidate video correctness evidence
Exact Human Action Required: provide a nonempty licensed local MP4 at data/samples/videos/pc_reference.mp4 and state its author/source, creation or publication date when known, license, privacy status, and whether it is constant- or variable-frame-rate; do not add it to Git because the task requires input/output videos to remain ignored
Commands to Resume: rerun startup and recovery audits, then run test -s, file, stat, sha256sum, git check-ignore -v, ffprobe metadata inspection when locally available, and an OpenCV decode probe against data/samples/videos/pc_reference.mp4 before restoring Task 008 to In Progress
Git Status: only TASKS.md and tasks/008_cpp_ort_video.md contain the legal Task 008 Blocked-state record; no Task 008 files are staged
```

### Input Recovery Audit

Resumed: `2026-07-21T13:50:01+08:00`

The original failed command now succeeds for the user-provided local video.
Read-only inspection established:

```text
path: data/samples/videos/pc_reference.mp4
file type: ISO Media, MP4 Base Media v1 [ISO 14496-12:2003]
size: 1422392 bytes
SHA256: 275b88daea99ba797ebf65c788f06a4edcc853ad18b1f8fc81ccc17b79cc74d7
Git ignore rule: .gitignore:19:data/samples/videos/*
video codec: h264
pixel format: yuv420p
width: 1280
height: 720
r_frame_rate: 30/1
avg_frame_rate: 30/1
stream duration: 8.000000 seconds
container duration: 8.000000 seconds
reported frames: 240
```

Project Python `3.12.3` with OpenCV `4.10.0` opened the video and decoded every
frame. All `240/240` frames were nonempty BGR `1280x720` frames and the reported
FPS was `30.0`. Decoded frame BGR SHA256 samples were:

```text
frame 0:   197f4b48ac3fce3a4be1d08c1841624d71eb167bb69b6ba51f8aa8ffe2ec647d
frame 120: 2505606ef864e032fcfcdf244892e849c6103fbc4742f87658ccb5fcc89dc28d
frame 239: 4a960fe1abc58d36444fc4ba61dafecab636ea7090702192d29989b22faeeb7b
```

The repository owner states that the input is an owner-recorded, privacy-
sanitized derivative created on `2026-07-21`, with audio and source metadata
removed, authorized for local project testing, and not for Git distribution.
The file remains ignored and will not be staged or committed.

Branch, Task 007 completion commit `aeb2b52`, Task 008 Allowed Files, the clean
base plus legal Blocked-state record, ONNX model SHA256, manifest, read-only ONNX
Runtime SDK `1.18.1`, Python ORT `1.18.1`, CPU provider availability, SDK dynamic
dependencies, and C++ OpenCV `4.6.0` videoio linkage were revalidated. Task 008
is restored to `In Progress`. Repair attempts remain `0`; the prior stop was a
missing input, not an implementation failure.

### Implementation and Automated Verification

Automated verification stopped for mandatory human video review at:
`2026-07-21T13:59:14+08:00`.

Implemented only the Task 008 scope:

- A backend-neutral common video module validates capture metadata, frames,
  detection structures, nonnegative stage timings, timing aggregation, and full
  output-video decoding with first/middle/last sample evidence.
- `edgeai_ort_video` reuses the completed Task 006 preprocessing,
  postprocessing, detection, coordinate, clipping, and visualization modules
  plus the completed Task 007 `OrtDetector` without modifying them.
- One ONNX Runtime session is created before the frame loop and reused for all
  frames with `CPUExecutionProvider`, intra-op/inter-op threads `1/1`, and
  `ORT_SEQUENTIAL`.
- The writer requests H.264 in MP4 through FourCC `avc1` using the local FFMPEG
  backend. It has no codec or container fallback.
- Per-frame JSON records retain detection objects, candidate counts, and distinct
  `video_read`, `preprocess`, `inference`, `postprocess`, `visualization`,
  `video_write`, and `pipeline_total` measurements.
- `pipeline_total` is measured from preprocess start through postprocess end and
  explicitly excludes video read, visualization, and write. Writer close/flush
  is measured separately. All values are single-run functional diagnostics, not
  Task 009 benchmark data.

Verified environment:

```text
GCC: 13.3.0
CMake: 3.28.3
Ninja: 1.11.1
C++ OpenCV: 4.6.0 with videoio
Python OpenCV used for independent decode: 4.10.0
ffprobe: 6.1.1-3ubuntu5
ONNX Runtime C++: 1.18.1 from the authorized read-only SDK
execution provider: CPUExecutionProvider
build type: Release
compiler warnings: none observed
```

Required commands and results:

```text
cmake Release configuration with verified ONNXRUNTIME_ROOT   exit 0
cmake --build build/pc-release --parallel                    exit 0 (11/11)
ctest --test-dir build/pc-release --output-on-failure        exit 0 (5/5 PASS)
edgeai_ort_video required 240-frame run                      exit 0
test -s and file output video checks                         exit 0
python3 -m json.tool cpp_ort_video.json                      exit 0
edgeai_ort_video --verify-output required command            exit 0 (PASS)
ffprobe input/output inspection                              exit 0
independent OpenCV full output decode                        exit 0 (240/240)
per-frame detection/timing consistency validation           exit 0
git diff --check                                             exit 0
```

The CTest run passed all common, postprocess, image invalid-argument, video
invalid-argument, and real H.264/avc1 pipeline tests.

Actual video identities:

```text
input: data/samples/videos/pc_reference.mp4
  SHA256: 275b88daea99ba797ebf65c788f06a4edcc853ad18b1f8fc81ccc17b79cc74d7
  size: 1422392 bytes
  stream: H.264, yuv420p, 1280x720, 30/1 FPS, 8.0 s, 240 frames, video only
output: results/videos/cpp_ort_reference.mp4
  SHA256: af3720d602a3a28ea885f164bc1642eab9bd9874685b804a0806cf9504089bc9
  size: 1790126 bytes
  stream: H.264, yuv420p, 1280x720, 30/1 FPS, 8.0 s, 240 frames, video only
results/evidence/008/cpp_ort_video.json
  SHA256: 3787bacc883abe9e5164b9c0cc14c7c41f158d32b1224e770b04579d19a8ee4a
  size: 1109526 bytes
results/logs/008_cpp_ort_video.log
  SHA256: 77ad021a2e1233000eb8e0dd8aa0ef357f8d943ef38348665a2fd291b1a01322
  size: 792 bytes
```

The input and output videos are both covered by existing Git ignore rules and
will not be staged or committed. The log remains ignored by `*.log`; its real
hash and contents are summarized here.

Actual frame counts:

```text
reported input: 240
decoded input: 240
processed: 240
failed: 0
written: 240
decoded during output verification: 240
```

The independent output decode confirmed every frame is BGR `1280x720`. Decoded
output sample SHA256 values were:

```text
frame 0:   6c3bd10bc7963abdd1dbad87900ec58edace06335f4fe2a381264b9c1dff41e0
frame 120: 68641141eb502f5ac1b49dd80f4f359b3c4f20bdc828c9db5fd61a2c79f4c225
frame 239: 522f5912a6f58c50092c90035ef17467a8c7d5c57d27f5e5398a852fe1b04f5c
```

Every structured detection had a finite `[0, 1]` confidence and a finite,
positive, clipped source box within `1280x720`. Per-frame detection counts ranged
from `0` to `10`, with mean `3.466666666666667`; `8` frames had no detections.
Actual class occurrence counts across all frames were:

```text
bed=82, book=106, cat=17, cell phone=39, cup=86, dog=1,
keyboard=125, laptop=9, mouse=224, remote=12, tv=131
```

These values are evidence, not claims of semantic correctness. Classes such as
the large `book` box around the desk/mouse-pad region near frame 120, the large
`bed` box touching the top/left bounds near frame 239, and the occasional
`cat`/`dog` detections require human judgment. No threshold, NMS setting, model,
input, or detector behavior was changed in response.

Actual aggregate timing diagnostics from the single functional run:

```text
sum ms:
  video_read=134.161726
  preprocess=422.541788
  inference=10049.275581
  postprocess=878.570499
  visualization=64.029497
  video_write=469.098824
  pipeline_total=11350.482479
loop_total=12019.376510 ms

mean per frame ms:
  video_read=0.559007192
  preprocess=1.760590783
  inference=41.871981588
  postprocess=3.660710412
  visualization=0.266789571
  video_write=1.954578433
  pipeline_total=47.293676996

separate setup/close/verification ms:
  config_load=0.050777
  video_open=9.646691
  session_create=68.880166
  writer_open=13.737757
  writer_close_and_flush=126.774254
  output_verification=95.588580
```

The aggregate values were recomputed from all 240 per-frame records and matched
the stored totals. They are not formal latency or FPS benchmark results and must
not be copied into Task 009 as such.

Repair attempts: `0`. The first implementation build, tests, full run, and
automated acceptance checks all passed; the active stop is mandatory visual
review, not an implementation failure.

### Human-Review Blocking Report

```text
Current Task: Task 008
Current Status: Blocked
Last Successful Step: all automated acceptance checks passed, including Release build, CTest 5/5, processing/writing 240/240 frames, JSON validation, ffprobe inspection, and two independent full output decodes
Failed Command: none; mandatory full-video human visual review is the active stop condition
Exit Code: N/A
Relevant Error: no automated error; output visual_review remains PENDING_HUMAN_REVIEW and semantic plausibility/continuity/encoding quality require human judgment
Files Changed: TASKS.md; tasks/008_cpp_ort_video.md; cpp/CMakeLists.txt; cpp/include/edgeai/common/video_pipeline.hpp; cpp/src/common/video_pipeline.cpp; cpp/apps/ort_video.cpp; cpp/tests/test_video_pipeline.cpp; results/evidence/008/cpp_ort_video.json; data/samples/videos/pc_reference.mp4 (ignored user input); results/videos/cpp_ort_reference.mp4 (ignored generated output); results/logs/008_cpp_ort_video.log (ignored generated log)
Attempts Made: 0 repair attempts; automated implementation and validation passed on the first run
Why Automatic Recovery Is Unsafe: playback continuity, box/label persistence, semantic plausibility, boundary-label rendering, motion behavior, and perceived encoding quality are visual decisions; automated box validation cannot determine whether detected classes correspond to real objects
Exact Human Action Required: play results/videos/cpp_ort_reference.mp4 from start to end and compare it with data/samples/videos/pc_reference.mp4; approve or reject playback, duration, frame order/continuity, box placement, label readability/clipping, detection flicker/duplicates, and encoding quality; specifically inspect around frames 0, 120, and 239, the large book and bed boxes, and occasional cat/dog classes
Commands to Resume: repeat startup/recovery/SDK/model/video audits; rerun Release configure/build, CTest, the exact frozen 240-frame inference command, JSON validation, --verify-output, ffprobe, full OpenCV decode, detection/timing consistency checks, and git diff --check; record the user's visual decision before changing status
Git Status: only Task 008 Allowed Files are modified or untracked; input/output videos and log remain ignored, no Task 008 files are staged, and no Task 008 commit exists
```

Task 009 has not started. No formal benchmark implementation or result was
produced.

### Human-Review Recovery

Resumed: `2026-07-21T14:06:20+08:00`

The user reported full-video visual acceptance: normal playback from start to
end; correct duration, frame order, motion continuity, and playback speed; no
black/corrupt/dropped frames or visible encoding defect; current-frame-aligned
boxes without stale overlays; no systematic coordinate shift, abnormal scale,
out-of-bounds or duplicate boxes; and acceptable boundary clipping, labels, and
encoding quality.

The user classified the large `book` detection near frame 120, the boundary-
touching `bed` detection near frame 239, and occasional `cat`/`dog` detections as
model false positives. They were not attributed to frame alignment,
preprocessing, postprocessing, coordinate restoration, visualization, or video
encoding. The `30 FPS` value is explicitly the output container playback frame
rate, not measured processing throughput. The single-run Task 008 timings remain
functional diagnostics and are not approved as formal benchmark results.

The visual decision is recorded but completion remains conditional on a fresh
Release configure/build, full CTest run, complete frozen 240-frame inference,
output verification, stream/decode validation, consistency comparison with the
reviewed artifacts, and Git checks. The reviewed JSON and output video were
copied read-only to `/tmp` before regeneration. Branch, Allowed Files, SDK,
model SHA256, input-video SHA256, and CPU provider were revalidated. No model,
video, threshold, NMS, configuration, or contract was changed. Task 008 is
restored to `In Progress`; repair attempts remain `0`.

### Final Acceptance

Completed: `2026-07-21T14:07:49+08:00`

The post-review recovery reran the complete required validation. The initial
incremental build command succeeded with `ninja: no work to do`; to ensure a
real fresh compilation, all reproducible CMake target outputs were then cleaned
and rebuilt. The clean Release compilation completed `22/22` steps without
warnings, and CTest again passed `5/5`.

The frozen video inference rerun again reported:

```text
input reported frames: 240
decoded: 240
processed: 240
failed: 0
written: 240
verified output decoded: 240
runtime: ONNX Runtime 1.18.1 CPUExecutionProvider
threads: intra-op=1, inter-op=1
```

The required JSON check, `--verify-output`, `ffprobe`, full OpenCV decode, and
`git diff --check` all exited `0`. The regenerated output remained H.264,
`yuv420p`, `1280x720`, `30/1` container FPS, `8.0` seconds, and `240` frames.
The `30 FPS` metadata is playback/container cadence only; it is not inference,
pipeline, or processing throughput and must never be reported as such.

The regenerated output video is byte-for-byte identical to the human-reviewed
video:

```text
input video SHA256:
  275b88daea99ba797ebf65c788f06a4edcc853ad18b1f8fc81ccc17b79cc74d7
output video SHA256:
  af3720d602a3a28ea885f164bc1642eab9bd9874685b804a0806cf9504089bc9
regenerated evidence JSON SHA256:
  c77a68a444fe17c48056e513c2abcdeb24c550114b2ee634464a2284db600df4
regenerated runtime log SHA256:
  15e484d60064d96f147ed1c968bde75d4cbd389a2e2bb8820c94c28ffe1bf9ee
```

All 240 decoded frames matched the reviewed output pixel-for-pixel, and every
frame's candidate counts and structured detections matched the reviewed JSON.
Representative decoded hashes remained:

```text
frame 0:   6c3bd10bc7963abdd1dbad87900ec58edace06335f4fe2a381264b9c1dff41e0
frame 120: 68641141eb502f5ac1b49dd80f4f359b3c4f20bdc828c9db5fd61a2c79f4c225
frame 239: 522f5912a6f58c50092c90035ef17467a8c7d5c57d27f5e5398a852fe1b04f5c
```

Human visual acceptance is `PASS`. Playback, duration, ordering, continuity,
speed, box/frame synchronization, coordinate scaling, clipping, labels,
duplicate suppression, and encoding quality were approved. No black frame,
corrupt frame, dropped frame, stale box, systematic coordinate shift, abnormal
scale, boundary overflow, or visible codec problem was observed.

The large `book` result near frame 120, boundary-touching `bed` result near frame
239, and occasional `cat`/`dog` classes are recorded as YOLOv5n model false
positives. They are not video frame-alignment, preprocessing, ONNX Runtime,
postprocessing, coordinate-restoration, visualization, or encoding defects. No
model, input video, threshold, NMS setting, or contract was changed to hide them.

Fresh single-run functional timing diagnostics were:

```text
sum ms:
  video_read=147.528767
  preprocess=423.908383
  inference=10502.929278
  postprocess=907.187354
  visualization=70.277372
  video_write=448.409874
  pipeline_total=11834.076101
loop_total=12501.969696 ms
```

These changed naturally from the reviewed run and remain Task 008 diagnostic
data only. They are not formal benchmark measurements and will not be copied
into a Task 009 performance table. No required check was skipped. Total repair
attempts: `0`. Final Acceptance Criteria: all passed. Task 008 is `Completed`;
the local atomic commit uses `feat(cpp): add ONNX Runtime video inference` and
is the commit containing this Execution Record.
