# Roadmap

## Stage 1: PC deployment baseline

The PC work is organized as three auditable batches:

- Batch A, Tasks 002–005, is completed and Checkpoint A is approved. It freezes
  YOLOv5n v7.0 and provides the tested Python ONNX Runtime reference.
- Batch B, Tasks 006–009, is completed and Checkpoint B is approved. It provides
  shared C++ processing, C++ ONNX Runtime image/video inference, and the unified
  benchmark method.
- Batch C, Tasks 010–012, is completed and Checkpoint C is approved. It contains
  the fixed TorchScript/pnnx ncnn conversion, C++ ncnn image/video/benchmark path,
  order-balanced three-backend benchmark, and final PC acceptance.

`tasks/000_pc_stage_execution_protocol.md` defines selection, state transitions,
evidence, retry limits, blocking reports, recovery, commits, and human checkpoints.
PC Stage 1 is complete. The approved WSL2 measurements must not be generalized
to ARM or other systems.

## Stage 2: Anlogic DR1 ARM CPU baseline

This stage is `Completed` for the correctness-first CPU single-image baseline:

- Task 013 freezes the user-local CMake, Linaro AArch64 toolchain, glibc 2.25
  sysroot, ncnn `20240410` CPU-only static build, and real-board runtime smoke.
- Task 014 reuses the frozen YOLOv5n ncnn model and common C++ pipeline on the
  MLK-F3P-CZ02-DR1M90, reaches the PC/ARM `PASS_TARGET` gate, returns a
  byte-identical annotated PNG, and receives user visual approval.
- Task 015 reconciles provenance, hashes, evidence, and the existing
  build/deploy/run/compare entry points into the Stage 2 closeout.

The correctness-first closeout itself did not add a formal ARM benchmark.
Tasks 017 and 018 subsequently add the preregistered single-thread baseline and
paired CPU-threading experiment. Video, camera, Vulkan, quantization, and NPU
remain outside Stage 2.

## Stage 2 benchmark

Task 017, `Anlogic DR1 ARM CPU benchmark`, is `Completed`. Its protocol was
frozen before measurement:

- unchanged ncnn `20240410`, frozen YOLOv5n param/bin, fixed input, CPU FP32,
  batch 1, `640x640`, and one thread;
- five independent processes, each with 10 warmups and 20 measured pipelines;
- exact preprocess/inference/postprocess sums, nearest-rank P50/P90, sample
  standard deviation, aggregate-mean FPS, model-load time, and Peak RSS;
- read-only governor/frequency/thermal/environment observation;
- correctness against the PC C++ ncnn golden before and after every process;
- all raw samples and invalid-attempt evidence retained.

The approved real-board baseline contains five independent processes and 100
retained formal samples. It passes before/after correctness, deterministic
validator recomputation, the frozen `10%` stability gate with `1.688017802%`
round-mean spread, and user review. The unoptimized one-thread pipeline mean is
`3513.992354 ms` and sequential batch-1 FPS is `0.284576601`; inference is the
dominant stage.

## Stage 2 CPU threading experiment

Task 018, `Anlogic DR1 ARM CPU threading experiment`, is `Completed`. Its
protocol compares `configured_threads=1` and `configured_threads=2` while
holding the corrected OpenMP-enabled runtime, model, input, thresholds,
executable, timing, and statistics constant. Five pairs alternate `1→2`,
`2→1`, `1→2`, `2→1`, and
`1→2`; each condition receives five independent processes and 100 retained
samples.

The initial complete real-board session remains preserved, but a fixed-revision
source, build-cache, symbol, and short board-runtime audit confirmed that it used
`NCNN_OPENMP=OFF`, `NCNN_THREADS=ON`, and `NCNN_SIMPLEOMP=OFF` with no
effective operator-parallel backend. It is therefore retained as configured
thread-parameter sensitivity evidence, not published as a multithread
performance comparison.

The corrected formal session uses one standard-libgomp OpenMP-enabled ncnn
build for both conditions. The user-approved `BENEFICIAL` result reduces mean
pipeline latency from `3634.205540 ms` to `1969.402190 ms`, a
`1.845334365x` speedup and `84.533437%` FPS gain. Both 100-sample conditions
pass correctness and stability; cross-thread detections have IoU `1.0` and
confidence delta `0.0`. Task 017 remains the immutable different-build
historical baseline.

## Stage 2 ARM runtime profile

Task 019, `Anlogic DR1M90 dual-thread ARM runtime profile`, is `Completed`.
It preserves Task 017 as `baseline-single-thread` and makes the Task 018
OpenMP build `recommended-dual-thread` for explicit DR1 deployments. Profile
selection records thread/backend/build identity; the recommended profile fails
closed when OpenMP or its private hash-pinned libgomp is absent. Generic PC
defaults are unchanged.

The lightweight board gate reused the approved Task 018 ELF in a new isolated
directory and confirmed OpenMP, two observed process threads, `PASS_TARGET`
correctness, five detections, and exit zero. No benchmark session was rerun and
no new performance value was added.

## Future work: explicitly out of scope

Camera, Vulkan, quantization, affinity/NEON tuning, concurrent requests, and NPU
remain separate projects. Task 019 does not absorb those topics. NPU is `HOLD`.

## Stage 3 ARM video-file inference

Task 020 is `Completed`. Its real-board phase uses the Task 019
recommended OpenMP dual-thread profile and a 30-frame lossless FFV1/AVI
generated from the frozen reference image. The board decoded, processed,
annotated, wrote, and reopened all 30 frames; independent WSL validation reports
`PASS_TARGET` for every frame and decodes the returned MJPEG/AVI completely.
The user approved full playback and the representative first/middle/last
frames.

This is functional validation, not a formal video performance benchmark.
USB camera, streaming, async pipelines, dropped-frame policy, Vulkan,
quantization, and NPU remain outside Task 020.

## Stage 3 ARM UVC camera inference

Task 021 is `Completed` after automated validation and user representative-frame
review. The real DR1M90 camera
audit found two `uvcvideo` nodes and selected `/dev/video0` with V4L2 `YUYV`
`640x480` at negotiated `5 FPS`. A capacity-one latest-frame-wins slot keeps
capture bounded while the recommended Task 019 OpenMP dual-thread ncnn profile
processes ten retained frames. All retained frames replay through the approved
single-image path with `PASS_TARGET` equivalence; 101 overwritten frames are
recorded rather than hidden. This is functional camera validation, not a
realtime benchmark. Video streaming, camera performance benchmarking, Vulkan,
quantization, and NPU remain out of scope.

## Stage 4: Anlogic NPU runtime feasibility

The prior Task 022 local/VM/board audit and its incremental official AlWiki
scope are user-approved. Task 022 is complete as an audit, while NPU
deployment remains blocked; the primary result is still
`BLOCKED_DRIVER_OR_DEVICE`. APUG1205_0.1 and
IPUG166_1.0 document a cooperating PS HardNPU/PL SoftNPU path, required
SoftNPU bitstream, `hard_npu.ko`, `soft_npu.ko`, `cma_mem.ko`, CMA-backed
runtime APIs, and official `rt.bin`/`weight.bin` artifacts. On the current
DR1M90 eMMC image, CMA is reserved and a hard-NPU device-tree node is present,
but no matching modules or NPU/CMA device nodes are available. The VM SDK has
Arm NN/Alnpu candidate libraries and demo source but no identified standalone
`npu_runtime`, host converter executables, or official runtime model pair in
the searched paths. No bitstream, kernel, device tree, system library, or
vendor executable was changed or run. The project YOLOv5n NPU conversion is
not ready; a version-matched vendor runtime release and safe deployment plan
are required first. Secondary blockers are missing vendor assets, unverified
runtime ABI/identity, missing host tools, documentation gaps, and unknown
bitstream/Device Tree mapping. Task 023 should begin only after such a package
is received and its provenance is reviewed. The bounded public AlWiki audit
read seven selected pages through the official API (`7/7` HTTP 200), adding a
D20.1 DR1M90 Buildroot/HPF/module-selection flow and D20.0 NPU API evidence.
It exposed no downloadable, hashable current-board driver/runtime, bitstream,
one-shot, `rt.bin`/`weight.bin`, or host converter package; referenced example
assets remain access-pending and exact MLK-F3P-CZ02-DR1M90/Linux 6.1.111-rt42
mapping is unknown. No VM/board access or one-shot execution was performed in
the incremental pass. Task 023 remains a future vendor-package intake task.
