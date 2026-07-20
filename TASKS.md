# Tasks

The authoritative execution rules are in
`tasks/000_pc_stage_execution_protocol.md`. A task state is exactly `Planned`,
`In Progress`, `Blocked`, or `Completed`.

| Task | Batch | Dependency | Status | Description |
| --- | --- | --- | --- | --- |
| 001 | Bootstrap | None | Completed | Bootstrap the repository and validate C++17, CMake, and OpenCV with a native smoke test. |
| 002 | A | 001 | Completed | Freeze YOLOv5n v7.0 provenance, export constraints, manifest, and observed ONNX contract. |
| 003 | A | 002 | Completed | Validate the existing Python/ORT environment, model loading, model I/O, and raw tensor statistics. |
| 004 | A | 003 | Completed | Implement the Python ORT single-image detection reference with structured results and stage timings. |
| 005 | A | 004 | Completed | Add focused Python tests, fixed inputs, and a tolerance-based semantic golden result. |
| 006 | B | 005 + Checkpoint A approval | Planned | Add backend-neutral C++ detection, configuration, preprocessing, mapping, and visualization modules. |
| 007 | B | 006 | Planned | Add C++ ONNX Runtime single-image inference and compare it with Python. |
| 008 | B | 007 | Planned | Add C++ ONNX Runtime video-file inference with honest read/process/write timing boundaries. |
| 009 | B | 008 | Planned | Add the unified Release-only PC benchmark framework and real Python/C++ ORT measurements. |
| 010 | C | 009 + Checkpoint B approval | Planned | Convert the frozen ONNX model with pinned ncnn tools and verify param/bin loading. |
| 011 | C | 010 | Planned | Add C++ ncnn image/video inference, ORT alignment, and benchmark integration. |
| 012 | C | 011 | Planned | Generate the PC comparison, complete README, acceptance matrix, and Checkpoint C report. |
| 013 | Stage 2 | 012 + Checkpoint C approval | Planned | Record and validate the Anlogic DR1 ARM CPU toolchain setup. |
| 014 | Stage 2 | 013 | Planned | Run and measure the Anlogic DR1 ARM CPU functional baseline. |
| 015 | Stage 2 | 014 | Planned | Consolidate reproducibility notes and close the two-stage baseline. |

Batch A stops after Task 005, Batch B stops after Task 009, and Batch C stops
after Task 012. A checkpoint requires explicit human review before the next batch.
