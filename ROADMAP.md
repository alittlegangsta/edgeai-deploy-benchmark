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

Stage 2 does not contain a formal ARM benchmark, video, camera, Vulkan,
quantization, or NPU result.

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

## Future work: explicitly out of scope

Video, camera, Vulkan, quantization, multi-thread/affinity optimization, and NPU
remain separate projects. None is part of the Task 017 unoptimized CPU
baseline; NPU is `HOLD`.
