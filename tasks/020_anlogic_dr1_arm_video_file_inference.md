# Task 020

## Title

Anlogic DR1M90 ARM video-file inference.

## Status

Completed

## Stage

Stage 3 ARM video-file inference

## Dependencies

Task 019 (`Completed`).

## Recommended Branch

`feature/arm-video-file-inference`

## Recommended Commit

`feat(arm): validate DR1 video-file inference`

## Goal

Run the frozen YOLOv5n ncnn pipeline over a reproducible short video on the
real MLK-F3P-CZ02-DR1M90 using the Task 019
`recommended-dual-thread` runtime profile. Preserve one structured detection
record per frame, write a decodable annotated output video, validate every
frame against the Task 014 PC ncnn golden, and stop for user playback review
before completion.

## Scope

The input is a 30-frame constant-frame-rate lossless FFV1/AVI generated from
the frozen Task 014 reference image. Every decoded frame is byte-identical to
that image and therefore has the same semantic golden. The annotated output is
MJPEG/AVI for broad playback compatibility. The application reuses the
existing configuration, letterbox,
preprocessing, ncnn adapter, output decoder, NMS, labels, JSON, visualization,
and video pipeline.

The runtime is fixed to ncnn `20240410`, commit
`56775de50990ab7f16627efdcf5529b49541206f`, CPU-only FP32, batch 1,
`640x640`, confidence threshold `0.25`, NMS IoU threshold `0.45`,
`NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, two configured
threads, and the private hash-pinned `libgomp.so.1` loaded only from the
isolated deployment directory.

Per-frame timings are functional diagnostics, not a formal performance
benchmark. Camera capture, streaming, async queues, frame batching, dropped
frames, Vulkan, FP16/BF16/INT8 runtime, quantization, NPU, and system tuning are
out of scope.

## Frozen Identities

```text
ncnn tag: 20240410
ncnn commit: 56775de50990ab7f16627efdcf5529b49541206f
libncnn.a SHA256: bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3
private libgomp.so.1 SHA256: 87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
model param SHA256: 72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
model bin SHA256: 658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0
source image SHA256: 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
runtime profile: recommended-dual-thread
configured threads: 2
effective parallel backend: openmp
```

The generated input-video and Task 020 executable hashes must be recorded from
the real artifacts before deployment. Their values are not preregistered.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/020_anlogic_dr1_arm_video_file_inference.md
cpp/CMakeLists.txt
cpp/apps/ncnn_video.cpp
cpp/include/edgeai/common/video_pipeline.hpp
cpp/src/common/video_pipeline.cpp
cpp/tests/test_video_pipeline.cpp
scripts/vendor/generate_anlogic_arm_reference_video.py
scripts/vendor/build_anlogic_aarch64_video.sh
scripts/vendor/deploy_anlogic_aarch64_video.sh
scripts/vendor/validate_anlogic_arm_video.py
tests/python/test_anlogic_arm_video.py
.knowledge/manifests/anlogic_arm_video_file_inference.yaml
docs/vendor/ANLOGIC_ARM_VIDEO_FILE_INFERENCE.md
results/evidence/020/video_contract.json
results/evidence/020/video_environment.json
results/evidence/020/video_frame_detections.json
results/evidence/020/video_validation.json
data/samples/videos/anlogic_arm_reference.avi
results/videos/anlogic_arm_ncnn_reference.avi
results/images/020/frame_first.png
results/images/020/frame_middle.png
results/images/020/frame_last.png
results/logs/vendor/arm_video_file/
```

The input/output video and transient logs remain ignored local artifacts. The
source generator, identities, small structured evidence, and representative
images may be tracked only when repository policy permits.

## Forbidden Files and Actions

- Do not modify Task 017, 018, or 019 formal task/evidence/manifest content.
- Do not modify the frozen model, input image, thresholds, PC golden, ncnn
  revision, runtime profile identities, SDK, or board system state.
- Do not commit ARM ELF, model param/bin, ncnn/OpenCV/FFmpeg/libgomp libraries,
  SDK content, build directories, deployment packages, large logs, or
  credentials.
- Do not install or download codecs or dependencies.
- Do not publish diagnostic frame timings as a formal benchmark.
- Do not add camera, network stream, async pipeline, Vulkan, quantization, or
  NPU behavior.
- Do not modify board system libraries, governor, frequency, services, boot
  files, or storage outside the isolated deployment directory.

## Build Commands

Generate the ignored deterministic-input fixture from the frozen image:

```bash
python3 scripts/vendor/generate_anlogic_arm_reference_video.py \
  --source data/samples/images/pc_reference.jpg \
  --output data/samples/videos/anlogic_arm_reference.avi
```

Audit and cross-build in the isolated VM workspace:

```bash
bash scripts/vendor/build_anlogic_aarch64_video.sh --check
bash scripts/vendor/build_anlogic_aarch64_video.sh --execute
```

## Run Commands

```bash
bash scripts/vendor/deploy_anlogic_aarch64_video.sh --check
bash scripts/vendor/deploy_anlogic_aarch64_video.sh --execute
```

The deployment script must use an isolated directory, verify every transferred
hash, use a private `LD_LIBRARY_PATH`, execute the full video, return output and
evidence, and never modify board system directories.

## Test Commands

```bash
bash -n \
  scripts/vendor/build_anlogic_aarch64_video.sh \
  scripts/vendor/deploy_anlogic_aarch64_video.sh
python3 -m py_compile \
  scripts/vendor/generate_anlogic_arm_reference_video.py \
  scripts/vendor/validate_anlogic_arm_video.py \
  tests/python/test_anlogic_arm_video.py
PYTHONPATH=python .venv/bin/python -m unittest \
  tests/python/test_anlogic_arm_video.py -v
python3 scripts/vendor/validate_anlogic_arm_video.py \
  --evidence-dir results/evidence/020
cmake -S cpp -B build/ci-default-options-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-default-options-release --parallel
ctest --test-dir build/ci-default-options-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests/python -p 'test_*.py' -v
git diff --check
```

## Acceptance Criteria

1. VM audit proves the selected AArch64 OpenCV `videoio` and FFmpeg libraries,
   codecs, ABI, dependencies, and hashes used by the executable.
2. The input is exactly 30 lossless constant frames generated from the frozen
   image; its dimensions, FPS, FFV1/AVI identity, generator, and SHA256 are
   recorded. The output codec is separately recorded as MJPEG/AVI.
3. The AArch64 ELF has the correct loader/ABI, links only approved private
   runtime libraries, and fail-closed runtime-profile validation reports
   OpenMP, two configured/observed threads, and the frozen ncnn/libgomp hashes.
4. The isolated deployment passes all pre-run hashes and `ldd` has no
   unresolved dependency.
5. The application exits zero and decoded, processed, written, verified, and
   declared frame counts are all 30 with zero failed frames and contiguous
   frame indices.
6. Every frame has five finite, valid detections with matching classes,
   minimum class-matched IoU at least `0.99`, and maximum confidence delta at
   most `0.01` against the Task 014 PC ncnn golden. Cross-frame results are
   semantically identical within the same gate.
7. Structured JSON parses and records runtime identity, asset hashes, video
   metadata, frame counts, detections, and separated diagnostic timings.
8. The annotated video reopens in WSL, decodes exactly 30 frames at the expected
   dimensions/FPS, and first/middle/last representative PNGs decode.
9. Task 017-019 tracked evidence remains byte-unchanged; offline syntax,
   unit, CTest, link, evidence, sensitive-material, hygiene, and whitespace
   checks pass.
10. The user plays or inspects the returned video/samples and explicitly
    approves playback, frame continuity, annotation placement/readability,
    colors, and encoding quality.

Task 020 became `Completed` only after automated criteria 1-9 passed and the
user explicitly approved criterion 10.

## Repair Rules

At most three complete diagnose/modify/rebuild/retest/rerun loops may repair
Task 020. Each attempt and failing command must be recorded below. Codec
fallbacks must use libraries already present in the approved ARM bundle, keep
the same input frames and semantic pipeline, and preserve all failure evidence.

## Human Stop Conditions

Stop for required physical board/VM/network action, credentials, `sudo`,
system-library replacement, flashing, frozen-asset/protocol changes, exhaustion
of the approved local codec paths, or final video playback review. Ordinary
source, CMake, ABI, codec-selection, dependency-closure, transfer, permission,
JSON, and validation defects are repairable.

## Evidence Brief

```text
task: Task 020 Anlogic DR1M90 ARM video-file inference
board: MLK-F3P-CZ02-DR1M90
SDK tag: SDK_2025_07 local asset identity; exact official repository tag compatibility unproven
runtime: ncnn 20240410 / 56775de50990ab7f16627efdcf5529b49541206f
sources consulted: Tasks 008, 011, 014, 018, and 019 plus their tracked evidence
documented facts: Task 019 recommends the OpenMP dual-thread profile; the repository already has a shared video pipeline and ncnn video entry point
assumptions: none remain for the completed acceptance criteria
conflicts: the initial lossy MJPEG input changed a low-confidence detection; that failed attempt is retained outside Git and excluded from the accepted FFV1-input result
unresolved blockers: none
proposed action: preserve the approved Task 020 evidence and keep camera, streaming, performance benchmark, Vulkan, quantization, and NPU work in separate tasks
```

## Execution Record

Started: `2026-07-29` on the WSL host. The initial command second was not
captured separately and is intentionally not reconstructed.

Branch: `feature/arm-video-file-inference`

Starting commit: `9cc313d8e78d68aa4c59bb00b542c5fc1a40eff7`

Starting status: clean; HEAD equals local `dev` and `origin/dev`.

Initial audit:

- Task 019 is `Completed` and its recommended OpenMP dual-thread profile is the
  required runtime.
- The existing `edgeai_ncnn_video` already reuses the shared preprocessing,
  ncnn adapter, postprocessing/NMS, visualization, and video verification
  modules, but it is fixed to one thread and an `avc1` writer.
- The existing ignored PC H.264 input has 240 non-identical frames and is not a
  suitable per-frame Task 014 golden fixture.
- No Task 020 build, board run, detection, frame count, output video, or timing
  result has been claimed at task creation.

Repair attempt 1:

```text
failing command:
PYTHONPATH=python .venv/bin/python -m unittest
  tests/python/test_anlogic_arm_video.py -v

error:
the synthetic output-video test wrote representative images under /tmp, while
the validator assumed every sample path was below the repository before
recording a display path

diagnosis:
artifact validation was correct, but path presentation had an unnecessary
repository-only precondition

repair:
record repository-relative paths when possible and otherwise record the
absolute synthetic-test path; no video, runtime, inference, or gate changed

result:
PASS; the four focused Python tests, native Release video target, and two
focused CTest cases passed
```

Repair attempt 2:

```text
failing command:
bash scripts/vendor/build_anlogic_aarch64_video.sh --execute

first failure:
Linaro GCC 7.5 does not provide the standard <filesystem> header used by the
previously PC-only shared video module

repair:
route the video module, application, and test paths through the existing
edgeai::filesystem compatibility alias

second failure:
the GCC 7 experimental filesystem path lacks lexically_normal()

repair:
compare already-absolute input/output paths directly; the no-overwrite safety
gate remains intact

result:
PASS; native rebuild and focused CTest passed
```

Repair attempt 3:

```text
failing command:
bash scripts/vendor/deploy_anlogic_aarch64_video.sh --execute

real board/application result:
the profiled AArch64 application exited zero and decoded, processed, wrote, and
reopened all 30 MJPEG frames, but independent correctness validation rejected
the result because frame 0 had four detections instead of five

diagnosis:
the MJPEG input is lossy. Real inspection showed the first encoded frames
differed from each other and from the frozen image; the low-confidence mouse
golden crossed threshold. This is an input-fixture defect, not an inference or
board-runtime failure.

repair:
retain the failed deployment and returned evidence, switch only the generated
input container payload to the already available lossless FFV1 codec, keep AVI
and all 30 source frames, and retain MJPEG/AVI only for the annotated playback
output. A local FFV1 probe decoded 30/30 frames with zero pixel delta and one
unique decoded-frame hash.

result:
PASS; the regenerated lossless fixture and new isolated real-board run passed
```

Automated phase completed: `2026-07-29T10:56:01+08:00` (WSL record time).
The board clock remained unsynchronized at `Thu Jan 1 00:56:43 UTC 1970`.

Build and runtime identity:

```text
VM: Ubuntu 18.04.4 x86_64
CMake: 3.16.9
compiler: Linaro aarch64-linux-gnu-g++ 7.5.0
source archive SHA256:
f25c93a12bbffbc58b9aa419c806c20c97e59b47cd9f532a3c176d8134daef82
video ELF SHA256:
8de717cc21e3a74f9072489d18bc32d56813d3bc37bef0f4782bf3cc8c725094
ELF: ELF64 AArch64, interpreter /lib/ld-linux-aarch64.so.1
libncnn.a SHA256:
bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3
private libgomp.so.1 SHA256:
87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
runtime profile: recommended-dual-thread
configured ncnn threads: 2
observed process threads: 5 (whole process, including OpenCV/FFmpeg; not five ncnn inference threads)
effective parallel backend: openmp
ldd: PASS, no not found
```

Accepted input and output:

```text
input: lossless FFV1/AVI, 1280x960, 5 FPS, 30 frames
input size: 14767146 bytes
input SHA256:
3953653b6364a844e829be68df76fce8ce673add5c4bfaf9176c5fb205e5da49
decoded input pixel delta from Task 014 source: 0

output: MJPEG/AVI, 1280x960, 5 FPS, 30 frames
output size: 3908260 bytes
output SHA256:
2669ec2fd0bd4eaaa1bf06f5ef3636e2100023f32bc0a77622f01fab5673a8bc
WSL output decode: PASS, 30/30 frames
```

Real-board result:

```text
directory:
/root/edgeai/yolov5n-ncnn-video-file-20260729T025346Z
exit code: 0
stderr: empty
declared/decoded/processed/written/verified: 30/30/30/30/30
failed frames: 0
frame indices: contiguous 0..29
detections per frame: 5
classes/finite values/valid boxes: PASS/PASS/PASS
minimum golden IoU: 0.9999855075776749
maximum golden confidence delta: 0.0000050067901611328125
minimum cross-frame IoU: 1.0
maximum cross-frame confidence delta: 0.0
automated correctness: PASS_TARGET
```

Diagnostic mean-per-frame times were retained to audit boundaries only:
decode `338.935314 ms`, preprocess `35.596406 ms`, inference
`1865.914369 ms`, postprocess `53.864972 ms`, visualization `4.160104 ms`,
encode `413.089050 ms`, and the defined compute pipeline
`1955.375748 ms`. These are not formal video benchmark results; the 5 FPS
container field is only playback metadata.

Representative WSL-decoded images:

```text
frame 0:
d595945e490cdc2b72083a0d32c7e69c115361c9d9e088cf60c621a1857f52a8
frame 15:
d58c42846dd63cdc75b80f0882930083952faa457fcdb94a0be5ab7f4acab671
frame 29:
d58c42846dd63cdc75b80f0882930083952faa457fcdb94a0be5ab7f4acab671
```

Automated and human acceptance:

```text
automated_validation: PASS_TARGET
human_video_review: PASS
human_review_source: user
candidate_approved: true
Task 020: Completed
```

The user played `results/videos/anlogic_arm_ncnn_reference.avi` from start to
finish and inspected the first, middle, and last PNGs. The user approved the
six-second playback, continuous 30-frame ordering, geometry/colors, stable
boxes, readable labels/confidences, and absence of corruption, drawing
pollution, or frame artifacts. The known low-confidence earbud-case `mouse`
remains consistent with the PC and ARM single-image results.

Final offline validation after user approval:
`2026-07-29T11:21:13+08:00` (WSL record time).

```text
independent evidence recomputation: PASS
focused Task 020 Python tests: PASS (6/6)
all Python unit tests: PASS (104/104)
model-independent Release configure/build: PASS
full CTest: PASS (12/12)
Bash syntax: PASS
Python syntax: PASS
YAML parse: PASS (28 files)
Task 020 JSON parse: PASS (4 files)
Markdown internal links: PASS (32 checked)
frozen param/bin/source-image/input-video hashes: PASS
Task 020 evidence SHA256 reconciliation: PASS (4/4)
Task 017-019 tracked evidence immutability: PASS
sensitive-material scan: PASS
active-task allowed-path check: PASS
ignored input/output video and raw log policy: PASS
git diff --check: PASS
```

The representative PNGs decode as `1280x960x3`; automated inspection found
the expected five annotations. This does not replace the required user playback
and visual approval.

Human approval recorded: `2026-07-29T11:18:31+08:00`.

```text
human_video_review: PASS
human_review_source: user
candidate_approved: true
time basis: WSL approval record time; not board run time
```

The approval was supplied by the user. It was not performed or inferred by
Codex.

Completed: `2026-07-29T11:21:13+08:00` (WSL record time).
