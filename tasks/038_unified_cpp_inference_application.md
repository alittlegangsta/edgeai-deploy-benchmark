# Task 038 — Unified C++ Inference Application

Status: Completed
Dependency: Task 037
Recommended branch: `dev`
Recommended commit: `feat(cpp): add unified inference application`

## Objective

Provide one explicit C++ image-inference CLI over the existing ORT, TensorRT and
ncnn adapters. The common preprocessing, raw-output contract, YOLOv5 decode/NMS,
visualization and timing boundaries remain backend-independent. DR1 face NPU is
not part of this YOLOv5n interface.

## Acceptance criteria

1. `InferenceBackend` and concrete ORT, TensorRT and ncnn adapters compile
   without duplicating inference or postprocessing logic.
2. `edgeai_demo --backend ort|tensorrt|ncnn` accepts the documented model/source
   contract, rejects unavailable or incompatible backends explicitly, and never
   falls back silently.
3. JSON and annotated-image output identify backend, model, precision, tensor
   contract, stage timings, benchmark statistics and detections.
4. ORT FP32, TensorRT FP32/FP16 and ncnn FP32 paths run with the existing Golden
   contract; ncnn INT8 is accepted only when a matching external INT8 manifest
   is supplied and is never confused with FP32.
5. Release CMake, CTest, focused tests, full Python tests, syntax, links and
   `git diff --check` pass.

## Allowed files

`TASKS.md`, `README.md`, `cpp/CMakeLists.txt`, `cpp/apps/edgeai_demo.cpp`,
`cpp/include/edgeai/inference_backend.hpp`, `cpp/src/inference_backend.cpp`,
`scripts/validate_task038_unified.py`, `tests/python/test_task038_unified.py`,
`results/evidence/038/`, this task file.

## Forbidden changes

Do not change the frozen YOLOv5n model, preprocessing, decoder, NMS, thresholds,
Golden evidence or Task 001–037 evidence. Do not alter TensorRT engines,
ncnn model assets, ORT SDKs or DR1 NPU code. Do not add implicit backend
fallbacks, new performance experiments, or network/download behavior.

## Execution record

Start: 2026-08-12 Asia/Shanghai

- Branch: `dev`; Task 037 commit `889173500f28e5ea29658856b7ce728d8edd0037`;
  starting worktree clean.
- Existing backend adapters and common preprocess/postprocess modules were read
  before implementation. The implementation is an adapter/factory layer only;
  all tensor transforms remain in `edgeai_common`.

## Execution Record

- Completed: 2026-08-12 Asia/Shanghai; branch `dev`.
- Added `InferenceBackend`, explicit ORT/TensorRT/ncnn adapters, and the
  `edgeai_demo` image CLI. The CLI uses the existing shared preprocessing,
  YOLOv5 decoder/NMS and visualization modules; no backend fallback is present.
- Release configure/build succeeded in `/tmp/task038-cmake` with ORT+ncnn and
  in `/tmp/task038-trt-cmake` with ORT+ncnn+TensorRT. The unified binaries are
  external build artifacts; their hashes are frozen in
  `results/evidence/038/backend_runs.json`.
- Real unified runs used the frozen `pc_reference.jpg` and the existing Golden:
  ORT FP32, ncnn FP32 (threads=2, packing=on), and TensorRT FP32 each exited 0
  with five detections and `PASS_TARGET`. TensorRT FP16 exited 0 without a
  fallback; its Task037 COCO gate is accepted while the strict single-image
  confidence diagnostic remains recorded as a secondary difference. The
  strict FP16 Golden probe intentionally exited 2 and was not relabeled PASS.
- CTest passed 11/11 in both Release configurations. The focused Task038
  unittest passed 3/3. The first full-suite attempt with system Python had six
  import errors (`cv2`/`onnx` absent); that environment result is retained in
  `python_tests_system_python.json`. The project `.venv` rerun passed 160/160.
- The disabled TensorRT probe returned the explicit unavailable-backend error
  with exit code 1. No alternative backend was selected.
- Repair attempt 1: the initial unified compile failed because OpenCV JSON
  serialization received an `int64` RSS value; the implementation was repaired
  with an explicit integer cast. The same attempt also moved the Task038 CMake
  block after backend target definitions and removed feature-macro redefinition
  warnings. Reconfigure, rebuild, CTest and backend runs then passed.
- Evidence: `results/evidence/038/backend_runs.json`,
  `results/evidence/038/validation.json`, Python test summaries, and four small
  annotated images. TensorRT engines, ncnn/ORT SDKs, and build directories
  remain outside Git.
- Final checks: Task038 validator PASS, focused unittest PASS, full `.venv`
  unittest PASS, both Release CTest matrices PASS, JSON/syntax/link/hygiene
  checks PASS, and `git diff --check` PASS. No Task 001–037 evidence was
  modified and no NPU work was reopened.
