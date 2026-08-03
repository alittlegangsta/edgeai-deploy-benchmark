# Task 021

## Title

Anlogic DR1M90 UVC camera capture with bounded-latency object detection.

## Status

Completed

## Stage

Stage 3 ARM camera functional validation.

## Dependencies

Task 020 (`Completed`).

## Recommended Branch

`feature/arm-uvc-camera-inference`

## Recommended Commit

`feat(arm): validate DR1 UVC camera inference`

## Goal

Capture frames from a real UVC camera attached to the MLK-F3P-CZ02-DR1M90,
run the frozen YOLOv5n ncnn pipeline with bounded latest-frame latency, and
validate the camera application's detections against offline replay of the
same saved frames. This task is functional camera validation, not a real-time
or performance benchmark.

## Scope and invariants

The only runtime profile is Task 019's `recommended-dual-thread` profile:
ncnn `20240410` at commit
`56775de50990ab7f16627efdcf5529b49541206f`, `NCNN_OPENMP=ON`,
`NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, two configured ncnn threads, CPU-only
FP32 batch 1, 640x640 input, confidence threshold `0.25`, NMS IoU threshold
`0.45`, and the private hash-pinned `libgomp.so.1` loaded only from an
isolated deployment directory. The frozen model, input, labels, thresholds,
PC golden, and Task 017–020 evidence are read-only.

The camera device, negotiated V4L2/OpenCV backend, pixel format, dimensions,
and frame rate must be selected from real board capability evidence. The
pipeline uses one capture thread, one inference thread, and a capacity-one
latest-frame slot. Publishing a new valid frame overwrites an unprocessed old
frame; it never creates an unbounded queue. Capture, publication, processing,
overwrite/drop, invalid-capture, source sequence, capture timestamp, inference
age, and result age are recorded.

The application must support bounded short runs (at least 10 processed frames)
with no GUI requirement. Every processed frame is retained as a lossless raw
image for replay; first, middle, and last processed frames also have annotated
images. The approved offline single-image ncnn path is run on each retained
raw frame. Live and replay records must have matching finite detections, valid
boxes, class IDs, minimum class-matched IoU at least `0.99`, and maximum
confidence delta at most `0.01`. These checks validate pipeline equivalence,
not semantic truth of an unconstrained camera scene.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/021_anlogic_arm_uvc_camera_inference.md
cpp/CMakeLists.txt
cpp/apps/ncnn_camera.cpp
cpp/include/edgeai/common/camera_pipeline.hpp
cpp/src/common/camera_pipeline.cpp
cpp/tests/test_camera_pipeline.cpp
scripts/vendor/audit_anlogic_arm_camera.sh
scripts/vendor/build_anlogic_aarch64_camera.sh
scripts/vendor/deploy_anlogic_aarch64_camera.sh
scripts/vendor/validate_anlogic_arm_camera.py
scripts/vendor/replay_anlogic_arm_camera.py
tests/python/test_anlogic_arm_camera.py
.knowledge/manifests/anlogic_arm_uvc_camera_inference.yaml
docs/vendor/ANLOGIC_ARM_UVC_CAMERA_INFERENCE.md
results/evidence/021/camera_contract.json
results/evidence/021/camera_capabilities.json
results/evidence/021/camera_environment.json
results/evidence/021/camera_run.json
results/evidence/021/camera_frame_detections.json
results/evidence/021/camera_replay_validation.json
results/evidence/021/camera_validation.json
results/evidence/021/replay_json/
results/images/021/first_raw.png
results/images/021/first_annotated.png
results/images/021/middle_raw.png
results/images/021/middle_annotated.png
results/images/021/last_raw.png
results/images/021/last_annotated.png
results/logs/vendor/arm_uvc_camera/
```

## Forbidden Files and Actions

- Do not modify Task 017, 018, 019, or 020 task/evidence/manifest content.
- Do not modify the frozen model, input image, labels, thresholds, PC golden,
  ncnn revision, runtime profile, SDK, or board system state.
- Do not commit ARM ELF, model files, private libraries, SDK content, build
  directories, deployment packages, large raw video, or credentials.
- Do not use an unbounded capture queue, change governor/frequency/affinity,
  replace system libraries, install packages, use sudo, or flash storage.
- Do not claim real-time performance, run a formal benchmark, or enter video
  streaming, Vulkan, quantization, NPU, or camera hardware modification work.

## Build Commands

```text
bash scripts/vendor/audit_anlogic_arm_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --execute
```

## Run Commands

```text
bash scripts/vendor/deploy_anlogic_aarch64_camera.sh --check
bash scripts/vendor/deploy_anlogic_aarch64_camera.sh --execute
python3 scripts/vendor/replay_anlogic_arm_camera.py --check
python3 scripts/vendor/replay_anlogic_arm_camera.py --execute
```

The deploy command must use an isolated board directory and perform hashes,
dependency checks, bounded camera execution, and evidence collection without
writing system directories. The replay command must use the approved offline
single-image executable and must not access the board.

## Test Commands

```text
bash -n scripts/vendor/audit_anlogic_arm_camera.sh scripts/vendor/build_anlogic_aarch64_camera.sh scripts/vendor/deploy_anlogic_aarch64_camera.sh
python3 -m py_compile scripts/vendor/validate_anlogic_arm_camera.py scripts/vendor/replay_anlogic_arm_camera.py tests/python/test_anlogic_arm_camera.py
PYTHONPATH=python .venv/bin/python -m unittest tests/python/test_anlogic_arm_camera.py -v
python3 scripts/vendor/validate_anlogic_arm_camera.py --evidence-dir results/evidence/021
cmake -S cpp -B build/ci-default-options-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-default-options-release --parallel
ctest --test-dir build/ci-default-options-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
git diff --check
```

## Acceptance Criteria

1. The board identifies at least one `/dev/video*` node and records real
   V4L2/OpenCV capabilities and the selected negotiated configuration.
2. The AArch64 camera ELF and isolated runtime profile have correct hashes,
   ABI, OpenMP/libgomp identity, and no unresolved dynamic dependencies.
3. The camera application uses a capacity-one latest-frame slot with thread-
   safe publication, monotonic source sequences, and internally consistent
   capture/publish/process/overwrite statistics.
4. A bounded real-camera run exits zero and processes at least ten frames;
   source sequences are monotonic and no unbounded queue is used.
5. Every processed frame is retained losslessly for replay; representative
   first/middle/last raw and annotated images decode successfully.
6. Offline replay of each retained raw frame matches the live record with
   finite values, valid boxes, class IDs, IoU >= `0.99`, and confidence delta
   <= `0.01`.
7. Structured evidence records device identity, negotiated format, runtime
   identity, hashes, frame ages, statistics, output paths, and exit status.
8. Task 017–020 evidence is byte-unchanged and all offline syntax, unit,
   CTest, evidence, link, sensitive-material, and whitespace checks pass.
9. The task is `Completed` with `automated_validation: PASS`,
   `human_camera_review: PASS`, `human_review_source: user`, and
   `candidate_approved: true` after the user inspected representative frames.

## Human Stop Conditions

Stop for a missing camera, physical reconnection, credentials, sudo, system
library replacement, flashing, an inability to capture any supported format,
or after automated validation passes and only user visual review remains.

## Execution Record

Started: 2026-08-03 on the WSL host. The branch and dependency baseline were
checked before this contract was created. Board capability, build, deployment,
runtime, replay, and validation results are appended here from real commands;
no expected output is substituted for measured evidence.

### Execution record

- Git baseline: branch `feature/arm-uvc-camera-inference`, HEAD
  `26640b86a9804aa7c0f610738664400b3899b559`; Task 017--020 evidence was
  checked unchanged before the Task 021 changes.
- Read-only board capability audit found `/dev/video0` and `/dev/video1`, both
  `USB 2.0 Camera: USB Camera` nodes driven by `uvcvideo`. V4L2 ioctl
  enumeration recorded `MJPG` and `YUYV`; the selected stable configuration is
  `/dev/video0`, V4L2, `YUYV`, `640x480`, requested and negotiated `5 FPS`.
  Board-side `v4l2-ctl`, ffmpeg, and GStreamer command-line tools were absent;
  the application ioctl probe supplied the capability evidence without
  installing a package.
- The VM build used CMake 3.16.9, the approved Linaro AArch64 GCC/G++ 7.5.0,
  ARM OpenCV 4.7 videoio/FFmpeg libraries, and the Task 019 OpenMP ncnn
  install. The resulting ELF is AArch64 with interpreter
  `/lib/ld-linux-aarch64.so.1`, SHA256
  `2962d94e10f798daa389e9bf43d8c4ee88259479747967d311e9cf20d1e910a9`. The
  private `libgomp.so.1` is used only through the isolated deployment directory.
- The final board run was `20260803T082616Z`. It exited zero with 113 captured,
  112 published, 10 processed, 101 overwritten/dropped, zero invalid captures,
  one unpublished frame at shutdown, and one latest-frame pending at stop.
  The recorded accounting is `113 = 112 + 1` for captured/published/unpublished
  and `112 = 10 + 101 + 1` for published/processed/overwritten/pending.
  Processed source sequences were
  `0,11,22,34,45,56,67,78,89,100`; the capacity-one accounting equation passes.
  Whole-process observed thread count was 6; this is not a claim that ncnn
  inference used six threads. Frame-age and stage-timing fields are diagnostic
  only, not a realtime benchmark.
- Every retained raw frame was replayed with the approved native single-image
  ncnn path. Replay status is `PASS_TARGET` for 10/10 frames, with minimum
  class-matched IoU `0.9999769312514045` and maximum confidence delta
  `0.000006020069122314453`; this validates pipeline equivalence, not semantic
  ground truth for an unconstrained camera scene.
- The first board attempt (`20260803T082404Z`) is retained outside the Git
  evidence set as repair evidence: a JSON FileStorage array-shape bug caused an
  exit before evidence completion. It was not mixed into the final run and is
  not described as a formal camera-frame failure. A prior shared-path transfer
  error also produced no board deployment.
- Automated checks passed: runtime/profile identity, capability audit, slot
  accounting, monotonic source sequences, frame ages, raw and representative
  PNG decoding, offline replay, exit code, empty stderr, and dependency checks.
  The task was later completed after the user reviewed the six representative
  images; the approval record is below.

### Human review record

The user inspected the six files under `results/images/021/` as raw and
annotated first/middle/last pairs and confirmed that they open correctly,
retain orientation, proportions, exposure and color, and show clear, sensibly
placed boxes, labels and confidence text. The recorded result is:

```text
human_camera_review: PASS
human_review_source: user
candidate_approved: true
approval_recorded_at_wsl: 2026-08-03T16:50:00+08:00
```

The approval timestamp is the WSL record time, not camera capture time or board
inference time. It must not be attributed to Codex. Task 017--020 evidence is
unchanged, and camera timing remains diagnostic rather than a realtime
performance result.

### Actual commands and results

The following commands were run in this execution (no command below is an
expected-output placeholder):

```text
/home/dministrator/bin/anlogic-board-ssh 'echo board_ssh=PASS; uname -a; uname -m; ls -l /dev/video0 /dev/video1'
bash scripts/vendor/audit_anlogic_arm_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --execute
bash scripts/vendor/deploy_anlogic_aarch64_camera.sh --execute
python3 scripts/vendor/replay_anlogic_arm_camera.py --execute
python3 scripts/vendor/validate_anlogic_arm_camera.py --evidence-dir results/evidence/021 --raw-dir results/logs/vendor/arm_uvc_camera/replay_frames/20260803T082616Z
bash -n scripts/vendor/audit_anlogic_arm_camera.sh scripts/vendor/build_anlogic_aarch64_camera.sh scripts/vendor/deploy_anlogic_aarch64_camera.sh
python3 -m py_compile scripts/vendor/validate_anlogic_arm_camera.py scripts/vendor/replay_anlogic_arm_camera.py tests/python/test_anlogic_arm_camera.py
PYTHONPATH=python .venv/bin/python -m unittest tests/python/test_anlogic_arm_camera.py -v
cmake -S cpp -B build/ci-default-options-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-default-options-release --parallel 2
ctest --test-dir build/ci-default-options-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
git diff --check
```

The VM build succeeded after one repair attempt: the GCC 7 compiler rejected a
filesystem-path ternary in the first camera source. The source was changed to
an explicit `if` assignment, then the isolated build was rebuilt and exported;
no compiler, SDK, model, or system package was changed. The first board run
also exposed an OpenCV FileStorage array-shape serialization error. That run
and its returned evidence remain outside the final evidence set; the JSON
tensor shape was corrected, and the independent run `20260803T082616Z` passed.
One read-only audit check initially saw a transient WSL vsock wrapper error;
the unchanged wrapper was retried and the audit returned `board_ssh=PASS` and
`camera_audit_status=PASS`.

The final VM artifact has SHA256
`2962d94e10f798daa389e9bf43d8c4ee88259479747967d311e9cf20d1e910a9`. The
board run exited zero and produced 113/112/10 captured/published/processed
frames, 101 overwritten frames, zero invalid captures, and one pending frame.
Replay and validation both passed. The local camera pipeline CTest and all 108
Python unit tests passed. The task is now Completed; no board or VM access was
used during the approval and offline closeout pass.
