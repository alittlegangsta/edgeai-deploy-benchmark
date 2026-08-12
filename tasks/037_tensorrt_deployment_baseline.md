# Task 037 — TensorRT Deployment Baseline

Status: Completed
Dependency: Task 012 + Task 030 + Task 035
Recommended branch: `dev`
Recommended commit: `perf(pc): establish TensorRT deployment baseline`

## Objective

Build and validate TensorRT FP32/FP16 YOLOv5n v7.0 engines and a project-owned
C++ GPU runner under the frozen PC model contract. DR1 NPU work is outside this
task and remains `WAITING_FOR_VENDOR_INPUT`.

## Frozen contract

- YOLOv5n v7.0, ONNX SHA256 recorded in `models/yolov5n-v7.0/manifest.json`.
- Input: FP32 NCHW `[1,3,640,640]`, batch 1, static shape.
- Output: `[1,25200,85]`, no graph NMS.
- Existing project preprocessing, decode, NMS, confidence threshold, inputs and
  Golden reference must be reused unchanged.

## Acceptance criteria

1. A real CUDA GPU, driver, TensorRT headers/libs and builder are identified.
2. A TensorRT FP32 engine is built from the frozen ONNX and hash-recorded.
3. FP16 is enabled only when the real GPU/TensorRT stack supports it.
4. A project-owned C++ runner reports H2D, inference, D2H, postprocess and
   end-to-end timings with warmup/repeat settings.
5. TensorRT FP32 passes the strict single-image Golden. FP16 is accepted only
   after the fixed 4,500-image COCO gate (absolute mAP50 and mAP50-95 deltas
   <= 0.01, no catastrophic zero-detection images); its single-image Golden
   remains a secondary diagnostic and is not used to change the gate.
6. The project runner reports the same H2D, inference, D2H and pipeline protocol
   for both accepted precisions, and evidence/tests are complete without
   changing the model contract.

## Allowed files

`TASKS.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`, this task file,
`cpp/CMakeLists.txt`, `cpp/apps/`, `cpp/include/edgeai/backends/`,
`cpp/src/backends/`, `configs/task037/`, `scripts/`, `results/evidence/037/`,
`docs/benchmark/TENSORRT_DEPLOYMENT_BASELINE.md`, and Task 037-specific tests.

## Forbidden changes

Do not alter the frozen YOLOv5n ONNX, preprocessing, decoder, NMS, thresholds,
Golden evidence, or any Task 001–036 evidence. Do not install packages or
download CUDA/TensorRT/models without explicit user approval; the current
toolkit-only CUDA 12.9 and TensorRT 10.13.3 installation is explicitly approved
for this task. Never install or replace a Linux NVIDIA display driver. Do not
claim GPU/FP16 results without real execution. Do not push or create a PR.

## Execution record

Start: 2026-08-12 Asia/Shanghai

- Branch: `dev`; worktree was clean before this task.
- Frozen model manifest was read successfully. It records YOLOv5 v7.0,
  opset 12, static batch-1 640x640 FP32 NCHW input, `[1,25200,85]` output and
  no graph NMS.
- The first sandbox-local probe was not authoritative for the named WSL distro:
  it could not see `/dev/dxg` and reported an NVML access error. It was retained
  as an execution-environment observation, not as a host verdict.
- Read-only Windows PowerShell audit succeeded: `nvidia-smi` exit 0 identified
  one `NVIDIA GeForce RTX 4060 Ti`, driver `591.86`, reported CUDA `13.1`,
  8188 MiB, and UUID `GPU-d625b2cc-aa13-c4f0-2bee-7fdf9c0f57ee`. The captured
  `Get-ComputerInfo` product string was `Windows 10 Pro`, build `26200.8246`,
  while the user identifies the host as Windows 11; both observations are kept.
- `wsl --version` reported `2.7.11.0`; `wsl --status` selected Ubuntu as the
  default version-2 distribution; `wsl -l -v` showed Ubuntu running as WSL2.
- Read-only probes through `wsl.exe -d Ubuntu` succeeded. The actual Ubuntu
  distro is Ubuntu 24.04.4 LTS on kernel
  `6.18.33.2-microsoft-standard-WSL2`; `/dev/dxg` is present as
  `crw-rw-rw- ... 10, 258`, and `/usr/lib/wsl/lib/nvidia-smi -L` sees the
  RTX 4060 Ti with exit 0. WSL bridge libraries `libcuda.so*`,
  `libnvidia-ml.so.1` and `libdxcore.so` are present and in `ldconfig`.
- The actual Ubuntu distro has no `nvcc`, no `trtexec`, no `NvInfer.h`, no
  `libnvinfer*`/`libnvonnxparser*`; `python3 -m pip` is also absent, so the
  Python TensorRT module was not independently resolved. Therefore
  CUDA Toolkit and TensorRT C++ are simply not installed; this is distinct from
  Windows driver health and WSL GPU passthrough.
- Direct WSL invocation of Windows executables still showed
  `UtilBindVsockAnyPort:307: socket failed 1`, but an elevated PowerShell
  invocation works. This is recorded as an interop issue only and is not mixed
  into the GPU/toolkit verdict.
- NVIDIA documentation was read-only consulted. The conservative proposed
  pair is CUDA Toolkit `12.9 Update 1` with TensorRT `10.13.3` C++ Linux
  x86-64 artifacts built for CUDA 12.9. TensorRT 11.2.1's C++ packages prefer
  CUDA 13.3 Update 1 and are not selected until the newer driver/toolkit path
  is separately verified. The user then approved a toolkit-only installation.
- Approved installation completed in the named Ubuntu WSL distro using the
  NVIDIA CUDA WSL repository and NVIDIA Ubuntu TensorRT repository. The exact
  `cuda-toolkit-12-9` meta-package is `12.9.1-1`, `cuda-nvcc-12-9` is
  `12.9.86-1`, and the installed TensorRT C++ packages are
  `10.13.3.9-1+cuda12.9`. No `cuda-drivers`, `nvidia-driver`, `nvidia-dkms`,
  or `nvidia-kernel-common` package is installed.
- Environment gate passed: `nvcc` reports CUDA 12.9 V12.9.86; `trtexec --help`
  identifies TensorRT v101303; NvInfer/NvOnnxParser headers and TensorRT
  libraries are present; the minimal `scripts/task037_cuda_probe.cu` compiled
  with nvcc and exited 0 after enumerating one RTX 4060 Ti (compute capability
  8.9), allocating, clearing, synchronizing, and freeing GPU memory. The
  probe binary is retained only in `/tmp`.
- Exact package SHA256 values and the structured gate result are recorded in
  `results/evidence/037/environment_audit.json`.

## Historical blocking report (resolved by approved installation)

Current Task: Task 037 — TensorRT Deployment Baseline
Current Status at report time: Blocked
Last Successful Step: Frozen YOLOv5n manifest and read-only Windows/actual-Ubuntu WSL GPU audit
Failed Command: `nvcc --version` (toolkit absence probe)
Exit Code: non-zero (`nvcc: not found`)
Relevant Error: CUDA Toolkit and TensorRT C++ development artifacts are not installed.
Files Changed: `TASKS.md`, this task file, `results/evidence/037/environment_audit.json`
Attempts Made: 2 read-only environment audits; no build repair attempted
Why Automatic Recovery Is Unsafe: TensorRT engine construction requires a
  user-approved, version-pinned CUDA/TensorRT C++ installation. Installing a
  Linux display driver in WSL, downloading unpinned packages, or silently
  selecting a different TensorRT/CUDA pair would violate the task boundary.
Exact Human Action Required: Approve a separate installation step for the
  proposed CUDA `12.9 Update 1` + TensorRT `10.13.3` C++ package, or provide an
  equivalent version-pinned local package. The Windows driver and WSL GPU path
  themselves are healthy.
Commands to Resume: after approved installation, rerun `nvidia-smi -q`,
  `nvcc --version`, `trtexec --version`, locate `NvInfer.h`,
  `libnvinfer.so` and `libnvonnxparser.so`, then build the project runner.
Git Status: Task 037 changes are intentionally uncommitted; no push or PR.

## Recovery and current execution record

- Recovery authorization: user approved CUDA Toolkit 12.9 Update 1 and
  TensorRT 10.13.3 C++ installation, with the explicit prohibition on Linux
  NVIDIA display-driver installation retained.
- Successful installation commands (run in Ubuntu WSL as root through the
  approved PowerShell/`wsl.exe` bridge): the pinned NVIDIA CUDA keyring was
  installed, `cuda-toolkit-12-9=12.9.1-1` was installed, the official NVIDIA
  Ubuntu 24.04 repository was added, and the exact TensorRT 10.13.3.9+cuda12.9
  C++ package closure was installed. The apt simulation was checked before
  each install and contained no driver package.
- Environment-gate commands and real results:
  - `/usr/local/cuda-12.9/bin/nvcc --version` -> CUDA 12.9, V12.9.86.
  - `/usr/lib/wsl/lib/nvidia-smi --query-gpu=name,driver_version,compute_cap,memory.total`
    -> RTX 4060 Ti, 591.86, 8.9, 8188 MiB.
  - `/usr/src/tensorrt/bin/trtexec --help` -> TensorRT v101303, exit 0.
  - Headers: `/usr/include/x86_64-linux-gnu/NvInfer.h` and
    `NvOnnxParser.h`; libraries: `libnvinfer.so.10.13.3` and
    `libnvonnxparser.so.10.13.3`.
  - `scripts/task037_cuda_probe.cu` compiled with nvcc and ran with exit 0;
    it reported one RTX 4060 Ti, compute capability 8.9 and
    `global_memory_bytes=8585216000` after a real CUDA allocation/memset/sync/free.
- Resume-point state (before the engine phase): environment gate PASS and Task
  037 resumed as In Progress; the remaining engine work was then executed as
  recorded below.

## Engine, runner, and benchmark execution record

- Rebuilt the Release project runner after correcting the pipeline sample's
  host inference interval. The exact CMake build completed with exit code 0;
  the external ELF SHA256 is recorded in
  `results/evidence/037/runner_build.json`.
- Built three engines from the frozen ONNX in the approved Ubuntu WSL2 GPU
  environment. The default TF32-enabled FP32 artifact is retained as a
  rejected intermediate. The `--noTF32` FP32 artifact is the accepted engine;
  the real `--fp16` artifact is retained as diagnostic evidence only. Exact
  commands, sizes and SHA256 values are in `engine_manifest.json`.
- The project-owned runner was built with TensorRT 10 APIs and the common
  project preprocess/decode/NMS path. It enforces one FP32 input and one FP32
  output with the frozen shapes, records CUDA H2D/inference/D2H events, and
  exits nonzero on a Golden failure.
- FP32 `--noTF32` runner command used 10 warmups and 100 repetitions. It
  exited 0 with `PASS_TARGET`, five detections, minimum IoU
  `0.9999971389770508`, maximum confidence delta
  `0.0000020265579223632812`, pipeline mean `9.28372747 ms`, CUDA inference
  mean `1.6742607927322388 ms`, and 107.71535498337931 FPS.
- FP16 runner command used the same input, configuration, Golden, warmups and
  repetitions. It exited 2 with five detections, minimum IoU
  `0.9935288429260254`, and maximum confidence delta
  `0.005570024251937866`. Its benchmark is retained only as diagnostic data;
  no threshold, tolerance, model, or postprocess was changed.
- `trtexec` loaded the accepted FP32 engine with 100 iterations, 200 ms
  warmup, one second duration, no data transfers and 50/95 percentiles. It
  exited 0 and reported 1.43621 ms mean GPU compute; this is a reference-only
  measurement and is not substituted for project end-to-end timing.
- `scripts/validate_task037_tensorrt.py` passed; the focused Task 037 Python
  tests passed; the complete Python suite passed with `PYTHONPATH=python`
  (156 tests); the Release TensorRT-enabled CMake build passed and CTest
  passed all three C++ tests. The first CTest invocation was a not-run result
  because only the runner target had been built; the complete build and exact
  CTest command were then run successfully.

## User-authorized accuracy-gate continuation and final execution

The user resumed the task after the historical single-image FP16 diagnostic
failure. Task status was changed to `In Progress`; the environment gate and
TensorRT FP32 result remained ready. The FP16 decision gate was frozen before
performance review: absolute COCO mAP50 and mAP50-95 degradation no greater
than 0.01, with no catastrophic zero-detection image. Deployment confidence
and NMS remain 0.25/0.45; COCO evaluation uses 0.001/0.6 and maxDet=100.

The exact Task035 independent split was reconstructed from the user-provided
val2017 archive: 500 calibration images and 4,500 evaluation images, overlap
zero. The evaluation ID SHA256 is
`3b3b23ec869f04009b704ab05a1c8552a81cdd6bd27e2b7b48519f0a990a21de` and the
annotation SHA256 is `e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f`.
The project-owned TensorRT COCO runner produced predictions for all 4,500
images for both precisions. `scripts/task037_evaluate_coco.py` verifies subset
IDs, COCO category IDs, original-pixel xywh boxes, finite values, and the fixed
evaluation protocol.

Measured COCO results:

| model | mAP50 | mAP50-95 | images | zero-detection images |
| --- | ---: | ---: | ---: | ---: |
| TensorRT FP32 | 0.448302671 | 0.274720465 | 4500 | 0 |
| TensorRT FP16 | 0.448105440 | 0.274786550 | 4500 | 0 |

Relative to TensorRT FP32, FP16 changes are -0.000197230 mAP50 and
 +0.000066085 mAP50-95, so the FP16 accuracy gate passes. The frozen Task035
ncnn FP32 reference is retained as a cross-backend secondary reference; the
TensorRT FP32 result is the precision baseline for the FP16 delta gate.

The formal FP16 runner was then executed with 10 warmups and 100 repetitions,
using `--golden-secondary true` so the known one-image Golden drift is recorded
without overriding the COCO gate. It exited 0. FP16 reports GPU inference
1.370379 ms mean and pipeline 9.408935 ms mean (106.281952 FPS); its strict
single-image diagnostic remains IoU 0.993528843 and maximum confidence delta
0.005570024.

TensorRT FP32 pipeline attribution is measured: GPU inference is 18.034% of
the 9.283727 ms pipeline mean, preprocessing 17.055%, postprocess 43.297%,
and CUDA H2D+D2H transfers 13.855%. The GPU shifts the dominant cost toward
the CPU postprocess and preprocessing path. FP16 GPU inference speedup is
1.221751x, while pipeline speedup is 0.986693x (a 1.3307% regression); FP16
is accuracy-ready but is not claimed as a pipeline-throughput improvement.

Final artifact identities are recorded in `results/evidence/037/` and remain
outside Git: FP32 no-TF32 engine SHA256
`a3ad9715f3560e46cae2cacfa06ca11d1468c42947eea9487a15c82d84b968d6`, FP16
engine SHA256 `7f99cc9f628613a71ec993898a9825c0c45f4c5129862f8350fea0161e653c8a`,
FP32 prediction SHA256
`19812cd92a07465d5880eb2fa7fa2bc1f6090a11815db4fb32b6b52d1e6d4e6d`, and
FP16 prediction SHA256
`c2d81cd6fd6f734eab7151a2434f295ecb310b195686f90f26242efe77548be1`.
No Polygraphy diagnosis was required because the real FP16 model passed the
pre-registered COCO gate. No model, threshold, engine, or display-driver
change was made.

## Historical Blocking Report (superseded by the approved COCO gate)

Current Task: Task 037 — TensorRT Deployment Baseline
Current Status at the time: Blocked
Last Successful Step: FP32 `--noTF32` project runner and all TensorRT-enabled C++ tests passed
Failed Command: `/tmp/task037-cmake/edgeai_tensorrt_image --engine /tmp/task037/yolov5n_fp16.engine ... --precision FP16 --warmup 10 --repeat 100`
Exit Code: 2
Relevant Error: `TensorRT correctness gate failed`; five detections remained, but minimum IoU was `0.9935288429260254` and maximum confidence delta was `0.005570024251937866`, exceeding the unchanged Golden confidence tolerance of `0.001`.
Files Changed: `TASKS.md`, `README.md`, `cpp/CMakeLists.txt`, `cpp/apps/tensorrt_image.cpp`, `cpp/include/edgeai/backends/tensorrt_detector.hpp`, `cpp/src/backends/tensorrt_detector.cpp`, `scripts/task037_cuda_probe.cu`, `scripts/task037_compare_raw.py`, `scripts/validate_task037_tensorrt.py`, `tests/python/test_task037_tensorrt.py`, `results/evidence/037/*`, `docs/benchmark/TENSORRT_DEPLOYMENT_BASELINE.md`, this task file
Attempts Made: Environment recovery and installation (approved) succeeded; runner build repair attempts for missing CUDA include paths and C++17 portability succeeded; FP32 default-TF32 and strict no-TF32 builds were both executed; FP16 was built and executed without changing the model or correctness gate.
Why Automatic Recovery Was Unsafe at that time: Accepting the measured FP16 numerical drift would have violated the then-current single-image correctness contract. The user subsequently authorized the separate COCO accuracy gate; no model, threshold, or Golden was changed.
Exact Human Action at that time: Decide whether to accept the strict FP32 TensorRT baseline while treating FP16 as rejected, or authorize a separately specified precision/tolerance investigation. This report is historical.
Commands to Resume: Reconstruct the approved Task035 COCO split, run the fixed COCO gate, then benchmark FP16 only after that gate passes.
Git Status: Task 037 changes are intentionally uncommitted; no push or PR was performed.

## Completion record

- Final state: `Completed`; FP32 `TENSORRT_FP32_READY`; FP16
  `TENSORRT_FP16_READY` after the user-approved COCO gate.
- `python3 scripts/validate_task037_tensorrt.py` passed; focused tests passed
  (3 tests); full Python suite passed (157 tests); Release CMake build and
  CTest passed (3/3); JSON/Python syntax and `git diff --check` passed.
- No Polygraphy diagnosis was run because the FP16 COCO gate passed. No Linux
  display driver, model, threshold, engine source, or prior-task evidence was
  modified.
