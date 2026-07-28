# Task 014

## Title

Run and validate the frozen YOLOv5n ncnn single-image pipeline on the Anlogic
DR1 ARM CPU.

## Status

Completed

## Stage

Stage 2

## Dependencies

Task 013 (`Completed`).

## Recommended Branch

`feature/arm-yolov5n-single-image`

## Recommended Commit

`feat(arm): add YOLOv5n ncnn single-image deployment`

## Goal

Cross-build, deploy, run, and validate the already approved YOLOv5n ncnn
single-image pipeline on the MLK-F3P-CZ02-DR1M90 CPU. Reuse the Task 010–012
model, input, configuration, common preprocessing/postprocessing, and PC ncnn
golden without conversion or threshold changes.

## Scope

This task is limited to:

- AArch64 Linux CPU execution on the MLK-F3P-CZ02-DR1M90;
- ncnn `20240410`, CPU-only, FP32 runtime, batch 1, `640x640`;
- exactly one ncnn thread;
- the approved `.param`/`.bin`, configuration, COCO-80 labels, and fixed image;
- the existing C++ ncnn adapter and shared image/preprocess/postprocess/
  visualization modules;
- one image inference producing detection JSON and an annotated PNG;
- class-matched comparison against the approved PC C++ ncnn result;
- small provenance, execution, correctness, and output evidence.

This task does not include benchmark, video, camera, Vulkan, FP16, BF16
runtime storage/arithmetic, INT8, NPU, model conversion, threshold tuning,
system-library installation, or system-image modification.

## Frozen Inputs

```text
ncnn tag: 20240410
ncnn commit: 56775de50990ab7f16627efdcf5529b49541206f
input blob: in0
output blob: out0
input contract: FP32 [1,3,640,640]
output contract: FP32 [1,25200,85]
confidence threshold: 0.25
NMS IoU threshold: 0.45
classes: COCO-80
threads: 1
```

```text
models/yolov5n-v7.0/yolov5n.ncnn.param
SHA256 72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4

models/yolov5n-v7.0/yolov5n.ncnn.bin
SHA256 658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0

data/samples/images/pc_reference.jpg
SHA256 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071

results/acceptance/cpp_ncnn_reference.json
SHA256 fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9

results/acceptance/cpp_ncnn_reference.png
SHA256 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
```

The ignored model binaries remain local deployment inputs and must not be
committed. They may be deployed only after their hashes match this contract.

## Allowed Files

```text
TASKS.md
tasks/014_arm_yolov5n_single_image.md
cpp/CMakeLists.txt
cpp/apps/ncnn_image.cpp
cpp/include/edgeai/backends/ncnn_detector.hpp
cpp/include/edgeai/common/config.hpp
cpp/include/edgeai/common/filesystem.hpp
cpp/include/edgeai/common/postprocess.hpp
cpp/include/edgeai/common/preprocess.hpp
cpp/include/edgeai/common/video_pipeline.hpp
cpp/include/edgeai/common/visualize.hpp
cpp/src/backends/ncnn_detector.cpp
cpp/src/common/config.cpp
cpp/src/common/postprocess.cpp
cpp/src/common/preprocess.cpp
cpp/src/common/video_pipeline.cpp
cpp/src/common/visualize.cpp
cpp/tests/test_ncnn_detector.cpp
cpp/tests/test_postprocess.cpp
scripts/vendor/build_anlogic_aarch64_yolov5n.sh
scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
.knowledge/manifests/anlogic_arm_yolov5n_single_image.yaml
docs/vendor/ANLOGIC_ARM_YOLOV5N_SINGLE_IMAGE.md
results/evidence/014/anlogic_arm_ncnn_detections.json
results/evidence/014/anlogic_arm_ncnn_comparison.json
results/evidence/014/anlogic_arm_ncnn_validation.json
results/images/anlogic_arm_ncnn_reference.png
```

Repository-external build and deployment assets are allowed only under:

```text
/tmp/edgeai-anlogic-yolov5n/
/home/uisrc/build/edgeai-arm-yolov5n/
/home/uisrc/vendor/anlogic/logs/arm_yolov5n_single_image/
/root/edgeai/yolov5n-ncnn-single-image/
```

## Forbidden Files and Actions

- Do not modify Tasks 001–013 or 016, PC benchmark/evidence, PC golden files,
  frozen model files/manifests, inference thresholds, or model conversion.
- Do not commit the ARM ELF, `libncnn.a`, model `.param`/`.bin`, SDK files,
  build directories, VM tools, private keys, passwords, or authentication data.
- Do not install or replace board system libraries or modify the board boot
  assets, network, SSH configuration, eMMC image, kernel, or device tree.
- Do not run a formal benchmark, video, camera, Vulkan, quantization, or NPU
  workflow.
- Do not use output differences to justify threshold, golden, preprocessing,
  postprocessing, or model changes.

## Build Contract

- Build host: existing Ubuntu 18.04.4 x86_64 Anlogic VM.
- CMake: `/home/uisrc/.local/cmake-3.16.9/bin/cmake`.
- Toolchain: `configs/toolchains/anlogic-dr1-aarch64.cmake`.
- Compiler: Linaro GCC/G++ 7.5.0, target `aarch64-linux-gnu`.
- Sysroot: the Task 013 glibc 2.25 sysroot.
- ncnn root: `/home/uisrc/build/ncnn-aarch64/install`.
- OpenCV root:
  `/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64`.
- Required OpenCV modules: `core`, `imgproc`, and `imgcodecs` only.
- Build type: Release; C++17.
- ncnn runtime options: one thread, CPU only, Vulkan/FP16/BF16/INT8 disabled.

The ARM target must compile the existing ncnn backend and shared image pipeline.
An ARM-only duplicate preprocessing or postprocessing implementation is not
allowed.

## Correctness Contract

The existing `tests/python/compare_detections.py` must compare the board JSON
with `results/acceptance/cpp_ncnn_reference.json` using the pre-registered ncnn
profile:

```text
target minimum class-matched IoU: 0.99
target maximum confidence delta: 0.01
hard-floor minimum class-matched IoU: 0.98
hard-floor maximum confidence delta: 0.02
```

A target-level pass may proceed to human image review. A hard-floor-only result
requires explicit human disposition and cannot complete the task. A result
below the hard floor fails. The known low-confidence `mouse` false positive
must remain present.

## Acceptance Criteria

1. The ARM application reuses the existing common C++ preprocessing,
   postprocessing, visualization, configuration, and ncnn backend.
2. The Release cross-build uses the frozen toolchain, ncnn, and ARM OpenCV
   inputs and produces an ELF64 AArch64 application.
3. Host inspection records the ELF hash, interpreter, ABI requirements, and
   dynamic dependencies; no x86, Vulkan, Python, or OpenMP dependency exists.
4. The deployment package contains only the approved application, model,
   manifest/config, fixed input, needed non-system OpenCV libraries, run
   script, and a complete hash manifest.
5. Board hashes exactly match the deployment manifest and `ldd` reports no
   missing dependency.
6. The board runs CPU-only, FP32, batch-1, `640x640`, one-thread inference and
   exits zero without a system-library or system-image change.
7. The board JSON parses; every numeric value is finite; all boxes and classes
   are valid; the annotated PNG is nonempty and decodes at the input dimensions.
8. Detection count/classes match the PC C++ ncnn golden, minimum class-matched
   IoU is at least `0.99`, and maximum confidence delta is at most `0.01`.
9. Model/input/executable/output hashes, board environment, command, stdout,
   stderr, exit code, dependency closure, configuration, and diagnostic
   timings are recorded.
10. A human reviews the returned board PNG and explicitly accepts or rejects
    it. Automated success alone leaves this criterion pending.
11. Repository syntax, unit tests, CTest, evidence reconciliation, sensitive
    scan, Allowed Files, and diff checks pass.

Task 014 becomes `Completed` only after all criteria, including human visual
review, pass. All criteria have now passed. Task 015 remains `Planned`.

## Build, Run, and Test Commands

The checked-in build and deployment scripts must preserve the exact commands
used. The repository validation includes:

```bash
bash -n scripts/vendor/build_anlogic_aarch64_yolov5n.sh
bash -n scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
python3 -m json.tool results/evidence/014/anlogic_arm_ncnn_detections.json
PYTHONPATH=python python3 tests/python/compare_detections.py \
  --reference results/acceptance/cpp_ncnn_reference.json \
  --candidate results/evidence/014/anlogic_arm_ncnn_detections.json \
  --profile ncnn-preregistered \
  --min-iou 0.99 \
  --max-confidence-delta 0.01 \
  --output results/evidence/014/anlogic_arm_ncnn_comparison.json
git diff --check
```

Formal benchmark commands are forbidden in this task.

## Repair Rules

At most three complete repair loops may address build, link, deployment,
dependency, image I/O, model path, thread, or runtime errors. Each loop must
record the failing command, exact error, diagnosis, change, rebuild/redeploy,
and retest. Never pass by changing frozen assets, thresholds, the PC golden,
the runtime revision, the output schema, or the comparison gate.

## Human Stop Conditions

Stop for human action if:

- the board is offline or physical connectivity requires intervention;
- credentials, `sudo`, system-library replacement, or boot-image changes are
  required;
- a frozen model, input, configuration, PC golden, runtime, or algorithm would
  need to change;
- automated correctness reaches only the hard floor rather than the target;
- the returned annotated image needs the required human visual review;
- three complete safe repair loops fail or the technology route must change.

Ordinary path, quoting, transfer, execute-bit, CMake, linker, working-directory,
or private deployment-library issues are repairable within this task.

## Execution Record

Started: `2026-07-28T16:00:00+08:00`

Completed record time: `2026-07-28T16:11:11+08:00`

Branch: `feature/arm-yolov5n-single-image`

Starting commit: `6d50c6daad99b4faf779f991bba8059d95ff7328`

Starting Git status: clean; HEAD equals local `dev`.

Preflight checks:

- Frozen param, bin, input, PC ncnn JSON, and PC ncnn PNG hashes match.
- The VM is reachable and has CMake 3.16.9, the Task 013 ncnn install tree,
  and AArch64 OpenCV 4.7.0 core/imgproc/imgcodecs libraries.
- The board is reachable and reports AArch64, Buildroot 2022.02.6, kernel
  6.1.111-rt42, glibc 2.25, sufficient free space, and sufficient memory.
- No inference, build, deployment, or benchmark had run when this record was
  opened.

Resume instructions: implement the narrow ARM cross-build entry using the
existing C++ modules, build in the independent VM workspace, inspect and
package the ELF, deploy to the independent board directory, run once for
correctness, return evidence, run the frozen comparison, and stop for human
image review before marking the task `Completed`.

### Implementation and Build

The application was kept on the PC Stage 3 code path. CMake gained a
default-on `EDGEAI_ENABLE_VIDEO` option so the ARM single-image target can
resolve only OpenCV core/imgproc/imgcodecs. The ncnn application now accepts
the explicit `--model-param`, `--model-bin`, `--input`, and `--threads 1`
arguments while preserving the original PC CLI. The backend validates explicit
model paths against the unchanged Task 010 manifest hashes.

The validated GCC 7.5 toolchain exposed two compatibility issues:

1. Build attempt 1 failed because GCC 7.5 has no standard `<filesystem>`.
   `cpp/include/edgeai/common/filesystem.hpp` now selects the experimental
   implementation only on GNU compilers older than 8, and CMake links
   `stdc++fs` only for that compiler range.
2. Build attempt 2 failed because the experimental path type has no
   `lexically_normal()`. The nonessential calls were removed and file streams
   use explicit path strings.
3. Build attempt 3 passed from a new source-archive hash and clean build
   directory.

The successful build inputs and output were:

```text
source archive SHA256:
ad7adebb6e4ad9a4b93c7db40ef8dd626bf3467b9350c87ff6eeda588d8a422e

libncnn.a SHA256:
5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a

edgeai_ncnn_image SHA256:
a4d3f1a405284881d2c2bd9790033b3997d02de69142644b4d2c24dbb55056f1
```

Host inspection reports ELF64 AArch64, interpreter
`/lib/ld-linux-aarch64.so.1`, maximum requirements GLIBC 2.17 and
GLIBCXX 3.4.21, and no Vulkan, Python, or OpenMP dependency.

### Deployment and Runtime

The deployment manifest and SHA list were verified before transfer and on the
board:

```text
deployment_manifest.json:
6d02105089d6a79c420f19cb66373f410e7098bd0366784ddc61754d4f76b173

SHA256SUMS:
ab50df6e0ce70ff45845a4e753b29a79d7c7d79f57381fd1a49bd3c5ca911ae1
```

Board attempt 1 stopped before executing the ELF because the orchestration
script opened evidence files before creating `results/`. The script was fixed
to create that task-owned directory first and to reuse existing local/board
packages only after their SHA lists pass. Board attempt 2 then passed:

```text
board: MLK-F3P-CZ02-DR1M90
architecture: aarch64
OS: Buildroot 2022.02.6
kernel: 6.1.111-rt42
libc: glibc 2.25
dependency check: PASS, zero missing
exit code: 0
stderr: empty
detections: 5
classes: keyboard, tv, cup, mouse, mouse
```

The board clock remains unsynchronized. WSL capture time
`2026-07-28T15:52:43+08:00` establishes evidence ordering.

### Automated Correctness

The returned JSON and PNG hashes are:

```text
results/evidence/014/anlogic_arm_ncnn_detections.json
e93a3489d24632a5ff9327a3364a9a62753cfb8d0969994bd62525dabe47dd2c

results/evidence/014/anlogic_arm_ncnn_comparison.json
fee041817ffd1bf36b9beae4bb98cc9cca7baad3773e19c006c3f0a01eac0e92

results/images/anlogic_arm_ncnn_reference.png
57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
```

The image decodes as `1280x960x3` and is byte-identical to the approved PC
ncnn PNG. The frozen comparison produced:

```text
detection count: 5 versus 5
classes: exact match
minimum class-matched IoU: 0.999985507578
maximum confidence delta: 0.0000050067901611328125
status: PASS_TARGET
```

JSON parsing, finite numeric checks, source-box bounds, model/input hashes,
one-thread runtime settings, and the retained low-confidence `mouse` all pass.
The single timing record is diagnostic only and is not benchmark evidence.

### Human Visual Acceptance and Final Status

Human visual check: `PASS`

Human visual approval source: user

Approval record time: `2026-07-28T16:11:11+08:00` (WSL record time, not board
runtime time).

The user confirmed that the image decodes and displays normally; detection
boxes, class text, and confidence text are normal; the `keyboard`, `tv`, `cup`,
and `mouse` placements are reasonable; the low-confidence earbud-case `mouse`
false positive matches the PC golden; no black frame, corruption, color
anomaly, coordinate offset, or text anomaly is present; and the ARM image is
visually consistent with the PC ncnn golden.

Automated correctness is `PASS_TARGET`, and all Acceptance Criteria 1–11 now
pass. Task 014 is `Completed`; Task 015 remains `Planned`; NPU remains `HOLD`.
No formal benchmark, video, camera, Vulkan, FP16/BF16/INT8 inference, NPU
workflow, model conversion, threshold change, input change, or PC-golden
change occurred.

### Repository Validation

- Release incremental build: PASS (`ninja: no work to do` after the successful
  full local build).
- CTest: 12/12 PASS.
- Python validation attempt 1 used the system `python3` instead of the
  repository environment and failed test import with missing `numpy`, `onnx`,
  and `cv2`. No dependency was installed and this was not treated as a code
  failure.
- Python validation attempt 2 used the documented command
  `PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p
  'test_*.py' -v`: 64/64 PASS.
- Both vendor scripts pass `bash -n`.
- Task 014 YAML and JSON files parse; the returned PNG decodes as
  `1280x960x3`.
- Frozen input, output, and evidence hashes revalidate; comparison
  reconciliation is deterministic and remains `PASS_TARGET`.
- Sensitive-material scan and `git diff --check`: PASS.

### Final Closeout Validation

After the user visual approval was recorded:

- model-independent Release incremental build: PASS;
- CTest: 12/12 PASS;
- Python unittest: 64/64 PASS using the documented project `.venv`;
- Task 014 YAML and JSON parse: PASS;
- comparison evidence reconciliation: `PASS_TARGET`;
- returned PNG decode and hash: PASS (`1280x960x3`);
- Markdown links and both vendor-script `bash -n` checks: PASS;
- frozen model, input, PC golden, detections, comparison, and PNG hashes:
  unchanged and PASS;
- updated validation JSON SHA256:
  `e5f7c13831cb7134064e6ca180c5aab30f5c15fe7b19ccf05f4812a23985b342`;
- sensitive-material scan and `git diff --check`: PASS.

No ARM inference, PC benchmark, formal ARM benchmark, video, camera, Vulkan,
quantization, or NPU command was run during final closeout.
