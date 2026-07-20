# EdgeAI Deploy Benchmark

EdgeAI Deploy Benchmark is a staged learning project for building reproducible
native deployment and measurement baselines for edge inference. The repository
currently contains only the first C++ toolchain and OpenCV integration check.

## Current Status

Task 001 is completed. Its C++17/CMake target has been configured, compiled, and
run successfully with OpenCV; both supported invocation forms created, read
back, and validated a 640 x 360 image. No model inference has been implemented
yet.

## Scope

- Stage 1: establish a PC deployment baseline, beginning with the native build
  and OpenCV smoke test in Task 001. Later Stage 1 tasks remain planned.
- Stage 2: establish an Anlogic DR1 ARM CPU baseline after the PC baseline is
  complete. Stage 2 remains planned.

For Task 001, model inference, ONNX Runtime, ncnn, model assets, Python inference,
ARM deployment, board-specific code, and performance benchmarking are explicit
non-goals.

## Task 001 Requirements

The local environment needs a C++ compiler with C++17 support, CMake 3.16 or
newer, Ninja, pkg-config, and OpenCV 4 development packages providing `core`,
`imgproc`, and `imgcodecs`. On Ubuntu these are commonly supplied by
`build-essential`, `cmake`, `ninja-build`, `pkg-config`, and `libopencv-dev`.

From the repository root, configure and build the smoke target with:

```bash
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build/pc-release --parallel
```

Run it with the default output path:

```bash
./build/pc-release/edgeai_opencv_smoke
```

Or provide one output path:

```bash
./build/pc-release/edgeai_opencv_smoke results/images/opencv_smoke.png
```

The program prints its application name, the `__cplusplus` value, the OpenCV
version, and the verified output path and dimensions. It creates a 640 x 360 BGR
image, writes it as a PNG, reads it back, and returns zero only after validating
the decoded dimensions. With no argument, it writes to
`results/images/opencv_smoke.png` and creates the parent directories when needed.
