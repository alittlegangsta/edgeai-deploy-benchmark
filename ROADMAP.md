# Roadmap

## Stage 1: PC deployment baseline

Task 001 completed the native C++17, CMake, and OpenCV starting point. The
remaining PC work is planned as three auditable batches:

- Batch A, Tasks 002–005: freeze the YOLOv5n v7.0 contract, establish the Python
  ONNX Runtime reference, and approve a tested golden result. Stop at Checkpoint A.
- Batch B, Tasks 006–009: align common C++ preprocessing, add C++ ONNX Runtime
  image/video paths, and approve a unified benchmark. Stop at Checkpoint B.
- Batch C, Tasks 010–012: freeze ncnn conversion, add ncnn image/video/benchmark
  integration, and complete PC-stage acceptance. Stop at Checkpoint C.

`tasks/000_pc_stage_execution_protocol.md` defines selection, state transitions,
evidence, retry limits, blocking reports, recovery, commits, and human checkpoints.
Tasks 002–012 remain `Planned`; no model inference has been implemented yet.

## Stage 2: Anlogic DR1 ARM CPU baseline

Begin the ARM CPU baseline only after the PC baseline is established. This stage
is planned and has not been implemented. Checkpoint C approval is required before
any Stage 2 task begins.

## Future work: explicitly out of scope

Work beyond the two stages above is outside the current roadmap.
