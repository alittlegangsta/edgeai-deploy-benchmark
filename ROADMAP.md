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

## Future work: explicitly out of scope

The next unused task number is 017. A future `Anlogic DR1 ARM CPU benchmark`
task may be proposed under separate authorization using the unchanged
YOLOv5n/ncnn CPU FP32 single-thread contract. It must preregister warmup,
formal repetitions, independent process rounds, timing boundaries, P50/P90/FPS,
Peak RSS, governor, frequency, temperature, and raw-sample retention before
measurement. Video, camera, Vulkan, quantization, and NPU remain separate
projects; NPU is `HOLD`.
