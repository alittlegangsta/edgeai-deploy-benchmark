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
