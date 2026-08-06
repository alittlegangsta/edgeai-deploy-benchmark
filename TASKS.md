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
| 006 | B | 005 + Checkpoint A approval | Completed | Add backend-neutral C++ detection, configuration, preprocessing, mapping, and visualization modules. |
| 007 | B | 006 | Completed | Add C++ ONNX Runtime single-image inference and compare it with Python. |
| 008 | B | 007 | Completed | Add C++ ONNX Runtime video-file inference with honest read/process/write timing boundaries. |
| 009 | B | 008 | Completed | Add the unified Release-only PC benchmark framework and real Python/C++ ORT measurements. |
| 010 | C | 009 + Checkpoint B approval | Completed | Export the frozen YOLOv5n weights to TorchScript, convert with same-revision pnnx, and verify ncnn loading. |
| 011 | C | 010 | Completed | Add C++ ncnn image/video inference, ORT alignment, and benchmark integration. |
| 012 | C | 011 | Completed | Generate the PC comparison, complete README, acceptance matrix, and Checkpoint C report. |
| 013 | Stage 2 | 012 + Checkpoint C approval | Completed | Record and validate the Anlogic DR1 ARM CPU toolchain setup; CMake 3.16.9, the fixed ncnn source snapshot, AArch64 toolchain, static ncnn library, and model-free smoke ELF are host-validated, and the hash-identical smoke ELF passes on the real board. Inference, benchmark, and NPU remain out of scope. |
| 014 | Stage 2 | 013 | Completed | Run and validate the frozen YOLOv5n ncnn single-image pipeline on the Anlogic DR1 ARM CPU; automated correctness reached PASS_TARGET and the user approved the returned output image. Benchmark, video, camera, Vulkan, quantization, and NPU remain out of scope. |
| 015 | Stage 2 | 014 | Completed | Consolidate Tasks 013–014 provenance, reproduction, deployment, and correctness evidence, then close the DR1 CPU single-image baseline without adding benchmark, video, camera, Vulkan, quantization, or NPU claims. |
| 016 | Vendor and board baseline | None | Completed | Inventory Anlogic DR1 sources and SDK 2025.07, validate the AArch64 toolchain and board C/C++/OpenCV userspace smoke, and record runtime/NPU readiness; ARM ncnn, ARM YOLO/benchmark, NPU deployment, and exact SDK/Demo tag matching remain out of scope. |
| 017 | Stage 2 benchmark | 013 + 014 + 015 | Completed | Measure the frozen MLK-F3P-CZ02-DR1M90 CPU/FP32 single-thread baseline under the preregistered protocol; five independent processes and 100 retained samples pass correctness, deterministic validation, stability, and user review. NPU remains on hold. |
| 018 | Stage 2 CPU experiment | 017 | Completed | Compare configured one- and two-thread execution using one corrected OpenMP-enabled ncnn build; the paired 10-process/200-sample session passes correctness, stability, independent validation, and user review with a `BENEFICIAL` classification. The original OpenMP-off session remains invalid for multithread performance comparison, and Task 017 remains unchanged. |
| 019 | Stage 2 ARM runtime profile | 018 | Completed | Freeze explicit historical single-thread and recommended OpenMP dual-thread DR1M90 runtime profiles, enforce build/runtime identity, and validate the recommended profile without adding benchmark data or changing PC defaults. |
| 020 | Stage 3 ARM video | 019 | Completed | Run the frozen YOLOv5n ncnn pipeline over a reproducible 30-frame video on the DR1M90 using the recommended dual-thread profile; all frames pass automated correctness, the annotated video decodes completely, and the user approved full playback and representative frames. No formal video benchmark, camera, Vulkan, quantization, or NPU claim is included. |
| 021 | Stage 3 ARM camera | 020 | Completed | Capture from a real UVC camera with a capacity-one latest-frame pipeline using the recommended dual-thread profile; ten processed frames pass offline replay equivalence and the user approved first/middle/last raw and annotated frames. This is bounded-latency functional validation, not a realtime benchmark; Vulkan, quantization, and NPU remain out of scope. |
| 022 | Stage 4 NPU audit | 016 + 021 | Completed | The local/VM/board feasibility audit and seven-page official AlWiki increment are user-approved. The primary result remains `BLOCKED_DRIVER_OR_DEVICE`; Wiki process/API documentation adds no verified current-board driver/runtime package, vendor one-shot was not executed, and project YOLOv5n conversion is not ready. |
| 023 | Stage 4 NPU package intake | 022 | Completed | User-approved static intake and isolated build-chain validation. Native runtime assets remain unavailable; the Arm NN/ONNX demo and SDK driver sources build only in isolated VM workspaces, while symbol-CRC provenance and active board FPGA/Device Tree mapping remain unresolved. Primary verdict: `BLOCKED_BOARD_HARDWARE_MAPPING`; no module load, bitstream write, vendor execution, board deployment, or project-model conversion was performed. |
| 024 | Stage 4 NPU board mapping | 023 | Completed | Complete the read-only MLK-F3P-CZ02 boot/DTB/FPGA mapping audit and SD-first rollback plan. Current boot-file hashes and DTB/NPU/CMA semantics are confirmed, while the BOOT.bin FPGA payload/source, SDK lineage, kernel symbols and rollback gate remain blocked; current eMMC NPU readiness is Not ready and controlled deployment is not approved. |
| 025 | Stage 4 NPU SD-image preflight | 024 | Completed | Reproduce a clean, version-matched MLK-F3P-CZ02/DR1M90GEG400 NPU SD-image build chain. The PDF-guided injection flow plus frozen Buildroot 2022.02.6 download cache produce a same-workspace BOOT.bin, DTB, kernel, three NPU modules and a formal rootfs, with a complete external 13-file candidate set. Primary verdict is READY_FOR_SD_WRITE_APPROVAL; candidate approval covers static audit only, while no partitioned image, physical SD/eMMC write, module load, FPGA write or NPU execution occurred. |

Batch A stops after Task 005, Batch B stops after Task 009, and Batch C stops
after Task 012. A checkpoint requires explicit human review before the next batch.
