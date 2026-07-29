# Changelog

## Unreleased

- Added the minimal repository documentation for the two-stage baseline.
- Added a C++17/CMake OpenCV smoke-test target that writes and verifies a
  640 x 360 image.
- Added an explicit Git line-ending policy.
- Removed legacy empty-directory placeholder files.
- Froze the YOLOv5n v7.0 source weights and ONNX contract and added the Python
  ONNX Runtime tensor, single-image, and golden-test baseline.
- Added backend-neutral C++ preprocessing/postprocessing, C++ ONNX Runtime image
  and video inference, and the unified Release-only PC benchmark framework.
- Added the fixed same-weight TorchScript-to-pnnx ncnn conversion contract and
  C++ ncnn image, video, correctness, and benchmark paths.
- Added the Task 012 six-round order-balanced Python ORT, C++ ORT, and C++ ncnn
  campaign with 1,800 retained samples, generated summaries, and validation.
- Added the generated PC acceptance README/report with correctness, stage timing,
  stability, position-effect, process CPU, Peak RSS, and limitation analysis.
- Completed PC Stage 1 and received Checkpoint C approval while keeping the
  Anlogic DR1 ARM CPU stage explicitly `Not implemented / Planned`.
- Completed the Anlogic DR1 ARM CPU single-image baseline with a frozen
  AArch64 ncnn build, real-board runtime smoke, frozen YOLOv5n deployment,
  PC/ARM `PASS_TARGET` correctness, byte-identical annotated output, and user
  visual approval.
- Added the preregistered DR1 ARM CPU benchmark with five independent
  processes, 100 retained samples, before/after correctness, independent
  statistic recomputation, stability validation, and user approval. The
  published result is the unoptimized CPU-only FP32 one-thread baseline; NPU
  remains out of scope and `HOLD`.
- Completed the paired DR1 CPU threading experiment with a shared
  OpenMP-enabled ncnn build and private libgomp. The user-approved
  `BENEFICIAL` result records `1.845334x` pipeline speedup and preserves the
  original OpenMP-off session as invalid-for-comparison sensitivity evidence.
- Added explicit DR1 ARM runtime profiles: a historical Task 017
  `baseline-single-thread` profile and a recommended Task 018
  `recommended-dual-thread` profile with fail-closed OpenMP, ncnn, thread, and
  private-libgomp identity validation. Generic PC defaults remain unchanged.
