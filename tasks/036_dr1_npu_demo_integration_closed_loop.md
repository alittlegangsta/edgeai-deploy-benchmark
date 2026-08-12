# Task 036 — DR1 NPU Demo Integration Closed Loop

Status: Completed
Dependency: Task 026 + Task 029 + Task 032
Recommended branch: `dev`
Recommended commit: `feat(npu): integrate DR1 face demo closed loop`

## Objective

Turn the already validated DR1 vendor face `Alnpu | ALHardNPU` control into a
small project-owned C++ image runner. The YOLOv5n NPU investigation remains
frozen at `WAITING_FOR_VENDOR_INPUT`; this task does not change that model or
its evidence.

## Scope and safety

- Reuse the audited face ONNX model, ArmNN 32.1/OnnxParser and Alnpu runtime.
- The runner must force `Alnpu` only and reject CPU fallback.
- Board execution may use an isolated temporary directory and existing runtime
  assets; do not modify eMMC, boot files, DTB, kernel, bitstream or SD media.
- Do not commit vendor binaries, models, SDKs, credentials or large logs.

## Acceptance criteria

1. Vendor face input/output, preprocessing, runtime, backend assignment and
   postprocess are documented from existing source/evidence.
2. A project-owned C++17 image runner supports image input, inference, face
   detections/JSON, annotated output and explicit Alnpu-only configuration.
3. The runner is built against the existing AArch64 ArmNN/Alnpu deployment
   without duplicating the runtime backend implementation.
4. A real board run proves `Alnpu | ALHardNPU`, rejects CPU fallback, and exits
   successfully on one image.
5. A bounded warmup/repeat diagnostic reports mean, P50, P95, FPS and available
   resource data. It is a functional control measurement, not a YOLOv5n
   comparison or published NPU performance benchmark.
6. Evidence, validator/tests, README-ready documentation and this execution
   record are complete; Task 028/029/032 evidence remains unchanged.

## Allowed files

`TASKS.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`, this task file,
`docs/vendor/ANLOGIC_DR1_NPU_DEMO_INTEGRATION.md`,
`cpp/include/edgeai/backends/armnn_detector.hpp`,
`cpp/src/backends/armnn_detector.cpp`, `cpp/apps/armnn_face_image.cpp`,
`cpp/CMakeLists.txt`, `configs/task036/`, `scripts/vendor/`,
`results/evidence/036/`, `tests/` files specifically named for Task 036.

## Forbidden changes

Do not modify frozen model contracts, Task 017–035 evidence, NPU/YOLOv5n
models, boot/DTB/kernel/eMMC/SD/bitstream, or vendor source trees. Do not run
benchmark comparisons against YOLOv5n and do not push or create a PR.

## Execution record

Start: 2026-08-12 Asia/Shanghai

- Branch/status at start: `dev`, clean before Task 036 changes.
- Actual commands, build/run results, hashes and validation outcomes are added
  below as the task progresses.

## Final state

### Execution record

- Branch: `dev`; it was clean before Task 036 changes. No board, VM, SD, eMMC,
  boot, DTB, kernel or bitstream file was modified by this task; board
  execution used only `/tmp/task036`.
- Vendor source audit used the existing `dr1m90_npu` face source at
  `199ef4d71f453bb9a000102ff39def09c4cf73f9`; model SHA256 is
  `5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668`.
  The flow, tensor contract, anchors, thresholds and source hashes are in
  `results/evidence/036/vendor_face_flow_audit.json`.
- Project changes add the `edgeai_armnn_face_image` C++17 target and extend the
  shared ArmNN adapter to use parser-provided tensor shapes and quantization
  metadata. The runner uses direct 416x416 resize, RGB/NCHW `/255`, one Alnpu
  backend preference, CMA buffers, dequantized YOLO-face decode/NMS, JSON and
  annotated PNG output.
- AArch64 Release cross-build (VM CMake/Ninja, Linaro GCC 7.5.0) completed
  successfully. The ELF SHA256 is
  `9306d119e556ca15f166d993356590e155ce537f8898aa6af85c51f6d95b184e`.
- Repair attempt 1: the initial cross-build failed because OpenCV
  `FileStorage` rejected a `long long` value in the new JSON writer. The value
  was explicitly cast to `double`; the same configure/build command was rerun
  and succeeded. No further repair was needed.
- The real AArch64 board run in temporary `/tmp/task036` completed with exit
  code 0 for one image, first with one warmup/three repeats and then with two
  warmups/ten repeats. Captured stdout contains 13 `Alnpu | ALHardNPU`
  assignments; stderr records `backend_request=Alnpu fallback_allowed=false`,
  successful parser/network, Optimize, Load and Enqueue stages, and
  `PASS_ALNPU_ONLY`. CPU fallback was not permitted or observed.
- The ten-repeat functional control measured inference mean `50.3471437 ms`,
  P50 `50.362290 ms`, P95 `50.421541 ms`; end-to-end mean `65.9801407 ms`,
  P50 `65.824171 ms`, P95 `66.289740 ms`; FPS `15.15607559`; Peak RSS
  `38056 KiB`; two observed process threads. These values are face-control
  diagnostics only and are not compared with YOLOv5n.
- Read-only board state captured `cma_mem`, `hard_npu`, `soft_npu`, all three
  device nodes, platform bindings and `CmaTotal=131072 KiB` in
  `results/evidence/036/board_runtime_state.json`.
- Offline validation: `python3 scripts/vendor/validate_task036_npu_face.py
  --output results/evidence/036/validation.json` — PASS; focused Task 036
  unittest — 2 PASS; `PYTHONPATH=python .venv/bin/python -m unittest discover
  -s tests/python -p 'test_*.py'` — 154 PASS; Release host build — PASS;
  CTest — 5/5 PASS; Python compilation, JSON parsing and `bash -n` — PASS.
- The first system-Python unittest invocation was not used as a result because
  its environment lacked project dependencies (`cv2`, `onnx`, and
  `edgeai_benchmark`). The repository `.venv` with `PYTHONPATH=python` was
  used for the passing full suite; no dependency was installed.
- Task 017–035 evidence paths were not changed. Final `git diff --check` and
  explicit-path staging are recorded with the local commit.

Final state: `Completed`. The face NPU closed loop is functional and Alnpu-only;
custom YOLOv5n NPU compatibility remains outside this task and continues to
wait for vendor input.
