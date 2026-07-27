# SDK_2025_07 component inventory

This is a read-only inventory of `/home/uisrc/vendor/anlogic/sdk/sdk`. It does
not claim that every component is relocatable or build-ready.

## Identity

- Release marker: `buildroot/rel_ver` = `SDK_2025_07` (explicit).
- Source archive: `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz`.
- Archive SHA256: `c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`.
- Existing SDK tree and archive were not modified or re-extracted.

## Buildroot and target

`buildroot/configs/anlogic_dr1m90_defconfig` explicitly selects AArch64,
external glibc, GCC 7, Linux kernel headers 4.10, and an external toolchain at
`../toolchains/aarch64-linux` with `aarch64-linux-gnu-` prefix. The generated
`.config`, `output/host`, `output/staging`, `output/target`, and a generated
sysroot/rootfs were not found. Buildroot version and kernel release remain
unknown.

## Toolchains

| Archive | Intended use | Status |
| --- | --- | --- |
| `toolchains/dr1m_arm-gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu.tar` | Linux AArch64, `aarch64-linux-gnu-` | Archive present; not extracted or executed |
| `toolchains/dr1m_arm-gnu-toolchain-12.3.rel1-x86_64-aarch64-none-elf.tar.xz` | Bare-metal AArch64, `aarch64-none-elf-` | Archive present; not extracted or executed |

The expected compiler binaries under `toolchains/aarch64-linux/bin` and
`toolchains/aarch64-bm/bin` are absent. Compiler `--version`, target triplet,
sysroot, and libc runtime output therefore remain unknown.

## Arm NN bundle

Path: `app/npu/libs/armnn_lib`.
Status: **AARCH64_ARMNN_BUNDLE_CONFIRMED**.

Headers report Arm NN 32.1.0 and parser 24.6.0. Core, parser and base-pipe
libraries are ELF64 AArch64. The bundle has an Arm NN CMake package, but its
release target file references serializer/deserializer files not present in the
inspected library directory; `libprotoc.so.*` is also absent despite the build
script copy list. This needs a package-closure decision before building.

## OpenCV bundle

Path: `app/npu/libs/ffmpeg_opencv4.7.0_aarch64`.
Status: **AARCH64_OPENCV_4_7_CONFIRMED**.

Headers and CMake configuration report OpenCV 4.7.0. Inspected libraries are
ELF64 AArch64 and include core, imgproc, imgcodecs, dnn, videoio and highgui.
The package includes FFmpeg dependencies and build-host RPATH references, so a
runtime relocation check is still required.

## NPU and drivers

No standalone `libnpu_runtime` was found. Vendor Arm NN contains `Alnpu`
backend symbols and references to `/dev/hard_npu` and `/dev/soft_npu`; classify
this as an Arm NN custom backend, not as proof of an independent runtime.

Driver source files exist under `linux/drivers/npu/` for CMA, hard NPU and soft
NPU, but zero `.ko` binaries were found. Twenty-one HPF and twenty-five bitstream
files exist across SDK and Demo trees; their target/release provenance is
unknown.

## CMake and readiness

The NPU CMake sources require at least CMake 3.15. The Ubuntu 18.04 VM reports
no `cmake` command. No build was attempted. The SDK is suitable for a metadata
follow-up, not yet for a reproducible NPU build.

Evidence is preserved in the remote log directory
`/home/uisrc/vendor/anlogic/logs/npu_dependency_audit/` and summarized in
`.knowledge/manifests/sdk_2025_07_component_inventory.yaml`.
