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

Video, camera, Vulkan, quantization, affinity/NEON tuning, concurrent requests,
and NPU remain separate projects. Task 019 does not absorb those topics. NPU
is `HOLD`. The next proposed task is Task 020, ARM video-file inference, with a
separate contract and acceptance boundary.
