# Anlogic DR1 AArch64 ncnn host-build baseline

## Outcome

Task 013 now has a reproducible host-side AArch64 ncnn baseline. CMake 3.16.9
was built in the Anlogic VM user's home directory, a clean archive was generated
from the fixed ncnn Git object, the checked-in toolchain file configured the real
Linaro compiler/sysroot, and a CPU-only static ncnn library plus a model-free
AArch64 smoke ELF were built successfully.

The smoke ELF was inspected but not executed. The VM is x86_64 and the
development board was not accessed. Task 013 therefore remains `In Progress`
until a separately approved board run passes.

## Source identity

| Field | Frozen value |
| --- | --- |
| Official remote | `https://github.com/Tencent/ncnn.git` |
| Tag | `20240410` |
| Commit | `56775de50990ab7f16627efdcf5529b49541206f` |
| License | BSD 3-Clause plus the third-party notices in `LICENSE.txt` |
| License SHA256 | `6495f972a09ad7f64ccd953e79adba91a93d862edc7135e6d95210bbf4002a01` |
| Clean archive SHA256 | `81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45` |
| Archive size | 12,840,688 bytes |
| Archive member count | 3,446 |

The WSL checkout still reports the pre-existing `python/pybind11` submodule
difference. It was not copied. The archive was generated from the exact commit
object, and a second archive invocation produced the same SHA256.

At this revision, `python/pybind11` is reached only when `NCNN_PYTHON=ON`, and
the `glslang` submodule is reached only when `NCNN_VULKAN=ON`. Both features are
off, so neither submodule is required by this build.

## User-local CMake

The VM had no system `cmake` or `cmake3`. The existing SDK Buildroot download
cache provided:

```text
/home/uisrc/vendor/anlogic/sdk/sdk/buildroot/dl/cmake/cmake-3.16.9.tar.gz
```

Its size is 9,113,695 bytes and its SHA256 is:

```text
1708361827a5a0de37d55f5c9698004c035abb1de6120a376d5d59a81630191f
```

It was extracted and built only under
`/home/uisrc/build-tools/cmake-3.16.9`, then installed with:

```text
bootstrap --prefix=/home/uisrc/.local/cmake-3.16.9
make -j2
make install
```

The installed CMake reports version 3.16.9. Its executable SHA256 is:

```text
fa6d96ed54cbb20be01e16a275e6f86e97ed76953c113c8fffa2de18123f42b5
```

No package manager, `sudo`, network source, or system directory was used.

## Toolchain and target

The checked-in toolchain file is
`configs/toolchains/anlogic-dr1-aarch64.cmake`, SHA256
`8ba63b21a1fa6bb2d3ddb391c686e460ea08d39a521592540997e76edb5359b0`.
It freezes:

- Linaro GCC/G++ 7.5.0;
- target `aarch64-linux-gnu`;
- the SDK glibc 2.25 sysroot;
- the AArch64 archiver, ranlib, and strip tools;
- sysroot-only library, include, and package lookup.

CMake's real C and C++ compiler/ABI/link checks passed, and ncnn reported target
`arm 64bit`. The sysroot contains the loader, libc, libm, libpthread, libdl,
librt, libstdc++, libgcc_s, and `crt1/crti/crtn`.

The SDK OpenCV 4.7 headers, CMake config, and core/imgproc/imgcodecs AArch64
libraries were rechecked. The currently observed package does not contain
`lib/pkgconfig/opencv4.pc`, contrary to an older tracked inventory. OpenCV is
not consumed by this minimal ncnn build because examples and tools are disabled.

## Frozen ncnn options

```text
CMAKE_BUILD_TYPE=Release
NCNN_VERSION=20240410
NCNN_SHARED_LIB=OFF
NCNN_VULKAN=OFF
NCNN_PYTHON=OFF
NCNN_BUILD_TOOLS=OFF
NCNN_BUILD_EXAMPLES=OFF
NCNN_BUILD_BENCHMARK=OFF
NCNN_BUILD_TESTS=OFF
NCNN_OPENMP=OFF
NCNN_RUNTIME_CPU=ON
NCNN_INT8=OFF
NCNN_BF16=ON
NCNN_VFPV4=ON
NCNN_ARM82=OFF
```

`NCNN_BF16=ON` means the revision's BF16 conversion implementation is compiled;
it does not enable BF16 in the smoke. The initial attempt with VFPV4 enabled and
BF16 compiled out exposed two dangling conditional chains in the fixed
`net.cpp`. Restoring the upstream-compatible BF16 compile option resolved that
source-level combination without patching ncnn. The smoke explicitly disables
BF16 storage, FP16 packed/storage/arithmetic, INT8, and Vulkan, so its intended
runtime contract remains CPU FP32.

OpenMP is disabled to avoid a board-side `libgomp` dependency. ARMv8.2 FP16 and
higher architecture paths are disabled for the Cortex-A35 baseline.

## Build and install outputs

The repository-external workspace is:

```text
/home/uisrc/build/ncnn-aarch64/
├── source/
├── build/
├── install/
└── logs/
```

Configure, build, and install all exited zero. The install tree contains 33
files or symlinks, including:

```text
include/ncnn/
lib/libncnn.a
lib/cmake/ncnn/
lib/pkgconfig/ncnn.pc
```

`libncnn.a` is 4,087,846 bytes with SHA256:

```text
5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a
```

The archive contains 180 object members; all 180 report machine `AArch64`.

## Model-free smoke ELF

`cpp/apps/anlogic_ncnn_smoke.cpp` creates an `ncnn::Net`, forces one CPU thread,
disables Vulkan and low-precision runtime options, allocates an FP32
`ncnn::Mat`, and verifies a fixed sum. It does not load a model or run
inference.

The cross-linked output is:

```text
/home/uisrc/build/ncnn-aarch64/anlogic_ncnn_smoke
```

| Property | Observed value |
| --- | --- |
| Size | 2,553,816 bytes |
| SHA256 | `cad23a736f86b0d1ae6f9cfd938dce55732a3fc983a5baaa5a31fde0e393b8f7` |
| ELF class | ELF64 |
| Machine | AArch64 |
| Interpreter | `/lib/ld-linux-aarch64.so.1` |
| Maximum GLIBC requirement | `GLIBC_2.17` |
| Maximum GLIBCXX requirement | `GLIBCXX_3.4.21` |

Its NEEDED entries are `libdl.so.2`, `libstdc++.so.6`, `libm.so.6`,
`libgcc_s.so.1`, `libpthread.so.0`, and `libc.so.6`. There is no Vulkan,
Python, or OpenMP runtime dependency.

Successful cross-compilation and ELF inspection do not prove board runtime
success. The file was not executed in the x86_64 VM.

## Attempts and recovery

1. A shell quoting error while recording the CMake commands left a task-owned
   bootstrap process running after the local SSH session was interrupted. A
   second bootstrap collided with it and reported `Text file busy`. The
   surviving bootstrap completed normally; its Makefile was verified, then
   `make -j2` and `make install` passed.
2. The first ncnn compilation used `NCNN_BF16=OFF` and failed in two
   `net.cpp` conditional chains. Source inspection identified the fixed-option
   interaction. Reconfiguring with `NCNN_BF16=ON`, while preserving runtime
   FP32 settings, passed the complete build and install.

No source patch, SDK change, warning suppression, host library substitution, or
architecture relaxation was used.

## Evidence and next gate

External logs are under:

```text
/home/uisrc/vendor/anlogic/logs/arm_ncnn_build
/home/uisrc/build/ncnn-aarch64/logs
```

The tracked manifest
`.knowledge/manifests/anlogic_aarch64_ncnn_build.yaml` records the command,
artifact, cache, and log identities.

Task 013 remains `In Progress`. The next gate is a separately approved transfer
to a temporary board directory, checksum validation, and direct execution of
the smoke ELF. Task 014 inference, model deployment, correctness comparison,
benchmarking, video, camera, Vulkan, and NPU remain out of scope.
