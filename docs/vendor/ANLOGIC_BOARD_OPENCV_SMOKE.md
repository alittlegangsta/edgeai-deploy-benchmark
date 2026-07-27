# Anlogic DR1M90 AArch64 OpenCV user-space smoke

## Scope

This Stage 1A check validates only a small OpenCV user-space program on the
real Anlogic DR1M90 board. It does not build ncnn, run YOLO, access NPU or Arm
NN, install CMake, modify system libraries, or change eMMC.

## Input package and build

The package was built in the Ubuntu 18.04 Anlogic VM using the recorded Linaro
GCC 7.5.0 toolchain:

- compiler: `/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++`
- target: `aarch64-linux-gnu`
- sysroot: the compiler-reported SDK sysroot
- SDK OpenCV root: `/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64`
- OpenCV version: `4.7.0`
- C++ standard: C++17
- flags: `-O2 -g -Wall -Wextra -Werror`

The program uses only `opencv_core`, `opencv_imgproc`, and
`opencv_imgcodecs`. It creates a 320x240 `CV_8UC3` image, draws a rectangle,
circle, and text, writes `opencv_smoke.png`, and prints the version and image
shape. It does not include highgui, videoio, dnn, FFmpeg, camera, GUI, ncnn, or
NPU code.

The three selected libraries are AArch64 ELF64 with SONAMEs:

```text
libopencv_core.so.407
libopencv_imgproc.so.407
libopencv_imgcodecs.so.407
```

Their direct NEEDED closure contains only the three selected OpenCV libraries
and board-provided system libraries. The vendor RPATH
`/home/rtxiao/repos/ffmpeg/ffmpeg_opencv4.7.0_aarch64/lib` is preserved in the
libraries; the executable also uses `$ORIGIN/lib`, and the board run succeeded
with the packaged SONAME files. No RPATH rewriting was performed.

## Package and deployment

The VM package is under
`/home/uisrc/vendor/anlogic/builds/opencv_board_smoke/package` and was mirrored
to the Windows shared path
`C:\Users\Administrator\Desktop\fpga_info\_generated\board_opencv_smoke`.
It contains the executable, `run.sh`, `README.txt`, `SHA256SUMS`, and only the
three required OpenCV shared libraries. It does not contain glibc, the dynamic
loader, board libstdc++, or board libgcc_s.

The package was transferred with Windows OpenSSH scp to
`/tmp/edgeai_opencv_smoke.new`, then atomically renamed to
`/tmp/edgeai_opencv_smoke`. The board-side sequence was:

```text
sha256sum -c SHA256SUMS
chmod 0755 opencv_board_smoke run.sh
sha256sum -c SHA256SUMS
sh run.sh
```

The first deployment invocation stopped before transfer because `/mnt/hgfs`
was not visible in the WSL process. The default local package path was then
corrected to the actual `/mnt/c/Users/Administrator/Desktop/...` mount and the
same deployment was rerun successfully. No board state was changed by the
failed invocation.

## Real board result

The board returned exit code `0`, with empty stderr and stdout:

```text
opencv_version=4.7.0
width=320
height=240
channels=3
```

The board generated `opencv_smoke.png`. It was copied to
`results/images/anlogic_opencv_smoke.png` and decoded by local Python OpenCV:

```text
dimensions: 320x240x3
size_bytes: 8205
sha256: bb460edbcf75e07f96d1a09bad2d6d44d5be6d2e2f9cf2098d6f3e3e6a208898
decode: PASS
```

## Decision

```text
OPENCV_AARCH64_LIBRARY_IDENTITY: PASS
OPENCV_LINK: PASS
OPENCV_DEPENDENCY_CLOSURE: PASS
OPENCV_BOARD_RUNTIME: PASS
OPENCV_IMAGE_OUTPUT: PASS
BOARD_CPU_BASELINE_READINESS: GO for a separately approved user-space CPU baseline step
```

This result does not establish ncnn, Arm NN, NPU-driver, NPU-runtime, camera,
video, or benchmark readiness. Those remain outside Stage 1A and require their
own approval and evidence.

## Reproduction commands

```bash
bash scripts/vendor/build_board_opencv_smoke.sh
bash scripts/vendor/deploy_board_opencv_smoke.sh
```

Both scripts use the approved VM/board wrappers, do not install dependencies,
and do not modify task state. The deploy script refuses to overwrite an
existing board target directory.
