# Milianke 05-5 NPU dependency audit

Audit date: 2026-07-24
Mode: read-only metadata, source text, and ELF inspection
Remote log root: `/home/uisrc/vendor/anlogic/logs/npu_dependency_audit/`

## Scope and safety boundary

This audit compares the already staged Milianke Demo with the already expanded
Anlogic SDK. It did not compile, run a vendor script or Demo, configure a model,
load a kernel module, install a package, extract a toolchain, or modify either
vendor tree. The original archive SHA256 was rechecked as
`c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`.

The authoritative machine evidence is in the remote logs, not in this summary.
The generated project manifest is
`.knowledge/manifests/npu_demo_dependency_inventory.yaml`.

## Inputs

| Input | Observed fact |
| --- | --- |
| SDK | `/home/uisrc/vendor/anlogic/sdk/sdk`, release marker `SDK_2025_07` |
| Archive | `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz`, SHA256 above |
| Demo | `/home/uisrc/vendor/anlogic/demos/milianke_npu_demo` |
| Demo tree | 1321 regular files, 460 directories, 0 symlinks |
| Tree evidence | `demo_tree.txt`, `demo_tree_summary.txt` |

The Demo is primarily an FPSoC/FSBL and hardware project tree. It contains a
large PDF and a `demo/sdk/face_detection.tar.gz`; neither was parsed or opened.
The SDK's `app/npu` source is the separate Linux Arm NN application entrypoint.
Its documented runtime scripts are under `app/npu/demo_scripts`, including
`run_yolo_pic.sh`; no script was executed. The Demo model archive remains
`present_not_opened`.

## Build and runtime references

The Demo source identifies `CHIP=dr1m90`, AArch64 settings, DR1M90GEG400
project settings, IDE metadata `2025.07`, and `SDK_VERSION=20250905`. These are
source facts, not an explicit `SDK_2025_07` tag. The SDK Linux build script
points CMake at `toolchains/aarch64-linux`,
`app/npu/libs/armnn_lib`, and
`app/npu/libs/ffmpeg_opencv4.7.0_aarch64`, and copies runtime libraries into a
rootfs staging directory. The Demo's `soc_sdk` Makefiles are not the Linux
Arm NN CMake application.

Build/reference evidence: `demo_build_references.txt`. Runtime/reference
evidence: `demo_runtime_references.txt`.

## Arm NN

Status: **AARCH64_ARMNN_BUNDLE_CONFIRMED**, with package-closure caveats.

The SDK contains Arm NN headers and CMake files. `Version.hpp` reports Arm NN
32.1.0 and the ONNX parser header reports 24.6.0. `file`/`readelf` confirm
ELF64 AArch64 for the core, parser, and base-pipe libraries. The inspected
bundle includes `libarmnn.so.32.1`, `libarmnnOnnxParser.so.24.6`,
`libarmnnBasePipeServer.so.32.1`, utilities, and protobuf.

This is not yet a build-ready claim: the release CMake target file references
serializer/deserializer libraries that are absent from the inspected `lib`
directory, and `libprotoc.so.*` listed by `build.sh` is absent. No runtime
load was attempted.

## OpenCV

Status: **AARCH64_OPENCV_4_7_CONFIRMED**, with relocation caveats.

The package `ffmpeg_opencv4.7.0_aarch64` contains headers,
`OpenCVConfig.cmake`, pkg-config metadata, and OpenCV 4.7.0 libraries.
Header/config macros report 4.7.0 and `file`/`readelf` report ELF64 AArch64
for the inspected libraries. Observed modules include core, imgproc, imgcodecs,
dnn, videoio, and highgui.

VideoIO has FFmpeg dependencies. The libraries also contain a build-host RPATH
under `/home/rtxiao/repos/ffmpeg/ffmpeg_opencv4.7.0_aarch64/lib`;
relocation and a successful target load remain unverified.

## NPU interface

No standalone `libnpu_runtime*` was found. The source and ELF evidence instead
classify the interface as **ARMNN_CUSTOM_BACKEND**: the Demo selects an Arm NN
`Alnpu` backend, and vendor Arm NN symbols reference `/dev/hard_npu`,
`/dev/soft_npu`, and CMA support. This classification does not prove that a
board image has the corresponding devices or drivers.

## Drivers and hardware artifacts

There are zero `.ko` binaries in the inspected SDK and Demo trees. Driver
sources exist for `cma_mem`, `hard_npu`, and `soft_npu`. The trees contain 21
`.hpf` and 25 `.bit` files plus boot artifacts, but their release provenance
and target compatibility are unknown. See `driver_inventory.txt` and
`hardware_artifact_inventory.txt`.

## Toolchain and CMake

Two unextracted archives are present: a Linaro 7.5.0 AArch64 Linux toolchain
with `aarch64-linux-gnu-` prefix, and a 12.3.rel1 bare-metal archive with
`aarch64-none-elf-` prefix. The documented extracted compiler paths are absent,
so compiler version and sysroot are unknown. CMake is not installed in the VM;
the inspected NPU CMakeLists require at least CMake 3.15.

## Compatibility judgement

Overall classification: **DEMO_LIKELY_MATCHES_SDK_2025_07**.

This is deliberately not an exact match. The SDK has an explicit release marker;
the Demo has 2025.07 IDE metadata, `SDK_VERSION=20250905`, the same DR1M90
target family, and compatible directory conventions. No Demo SDK tag or release
manifest was found, so the result remains a probable match. No SDK_2026.01
repository content was substituted.

## GO / HOLD / NOT_APPLICABLE

| Next action | Decision | Reason |
| --- | --- | --- |
| Extract the required toolchain archive | GO (next phase, explicit approval required) | Archive exists and prefix is plausible; extraction is prohibited in this audit. |
| Install CMake | HOLD | VM reports no CMake; installation is outside this read-only task. |
| Build AArch64 Hello World | HOLD | Compiler and sysroot are not yet validated. |
| Build minimal NPU Demo | HOLD | CMake, compiler/sysroot, package closure, drivers, HPF provenance, and runtime remain unvalidated. |
| NPU/board runtime test | HOLD | No board execution or kernel module evidence was authorized. |
| Video, camera, NPU accelerator tuning, benchmark | NOT_APPLICABLE | Explicitly outside this audit. |

## Evidence files

The remote log set contains `demo_tree.txt`, `demo_build_references.txt`,
`demo_runtime_references.txt`, `armnn_inventory.txt`, `armnn_elf.txt`,
`opencv_inventory.txt`, `opencv_elf.txt`, `npu_interface_inventory.txt`,
`driver_inventory.txt`, `hardware_artifact_inventory.txt`,
`toolchain_archive_inventory.txt`, `cmake_requirements.txt`,
`version_evidence.txt`, and `summary.md`.

## Evidence brief

- task: SDK_2025_07 and Milianke NPU dependency audit
- board: DR1M90GEG400 / Milianke 05-5 context
- SDK tag: SDK_2025_07
- repository tag/commit: not used; SDK_2026.01 was not substituted
- sources consulted: staged SDK, staged Demo, read-only source/ELF metadata
- documented facts: SDK release marker and SDK build paths
- source-code facts: Arm NN Alnpu backend selection, DR1M90/AArch64 build settings
- assumptions: none
- conflicts: Demo has date/version markers but no explicit SDK tag
- unresolved blockers: extracted compiler/sysroot, CMake, package closure, modules, and board runtime
- proposed action: obtain approval for controlled toolchain extraction and then validate a minimal AArch64 build
