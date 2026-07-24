# Local Linux SDK identity audit

Audit date: 2026-07-24 (Asia/Shanghai)

## Scope and exclusions

The read-only scan used the path in `.knowledge/local_paths.yaml`:

`/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA`

The scan inspected names, filesystem metadata, SHA256 values, and small text
files. It did not parse PDF bodies directly, extract archives, download Git LFS
objects, build or execute SDK/demo code, fetch Wiki/Gitee content, or modify the
source materials. Generated `build`, `output`, cache, log, `soc_prj`, kernel
object, image, video, and unrelated component trees were excluded from identity
claims.

## Candidate paths and archives

| Candidate | Observed identity | Status | Evidence strength |
| --- | --- | --- | --- |
| `01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk` | FPSoC firmware/FSBL example workspace; `CHIP=dr1m90`, `ARMv8_STATE=64`, `ARCH_ABI=aarch64` | Not a proven Linux SDK | explicit source-code facts |
| `03_demo/3-4_ex_soc_linux` | Linux course tree with ebook, source examples and generated outputs | Not a complete SDK | explicit outline/path facts |
| `03_demo/3-4_ex_soc_linux/01_ex_linux_base_F3P_DR1M90G.zip` | Linux basics example archive; not extracted | Candidate, identity unknown | filename/outline only |
| `03_demo/3-4_ex_soc_linux/02_ex_linux_drive_F3P_DR1M90G.zip` | Linux driver example archive; not extracted | Candidate, identity unknown | filename/outline only |
| `01_start/02_start_Linux/04_secondary_developmemt/demo.zip` | Secondary-development demo archive; not extracted | Candidate, identity unknown | filename only |

Archive metadata is preserved in `.knowledge/manifests/local_sdk_inventory.yaml`.
No archive was opened to inspect its internal tree.

## Most trustworthy local identity

No complete, versioned Linux SDK was identified in the scanned material. The
most useful source-code evidence is the small `soc_sdk` workspace:

- `soc_base/Makefile:11-13,23,76-88` sets `SDK_ROOT=.`, `CHIP=dr1m90`, leaves
  `COMPILE_PREFIX` empty by default, selects 64-bit ARM, and includes
  `tools/make/rules.mk`.
- `soc_base/tools/make/rules.mk:16-24` derives compiler tool names from
  `COMPILE_PREFIX`.
- `soc_base/tools/make/rules.mk:37-45` derives `armv8-a`, `aarch64`, and
  `MTUNE=cortex-a35` for the 64-bit configuration.
- `soc_base/tools/make/rules.mk:63-70` names HPF tool/path variables, but does
  not identify a Linux SDK release.
- `soc_base/tools/make/config.mk:22-25,57` repeats 64-bit ARM defaults and an
  empty compiler prefix.
- `soc_base/platform/board_cfg.mk:8-15` contains DR1M90/board configuration
  defines; it is not a Linux rootfs or SDK manifest.
- `soc_sdk/.metadata/version.ini:1-3` reports Eclipse platform
  `4.17.0.v20200902-1800`. This is IDE metadata, not a Linux SDK version.
- The small source Makefiles use generated examples and, in
  `Sourcecode/1.HelloWorld/Makefile:5,17`, document
  `/home/uisrc/uisrc-lab-anlogic/tools/aarch64-linux/bin/aarch64-linux-gnu-`.
  That path is absent on this host and is not proof of an installed compiler.

The local SDK tag, Buildroot revision, kernel revision, libc ABI, sysroot, and
host compiler version therefore remain `unknown`.

## Document and qmd evidence

The existing local keyword collection was queried without embedding or vector
search:

- `SDK 版本` found document revisions `REV2025` (SDK introduction, lines 7-9)
  and `REV2024` (Linux basics, lines 7-9). These are document revisions, not
  Linux SDK tags.
- `Linux SDK` found the Buildroot guide and Linux basics document, but no SDK
  release identifier.
- `SDK_2026.01`, `Buildroot 版本`, `sysroot`, and `OpenCV 4.7.0` returned no
  result.
- `交叉编译器` returned a Linux-basics table of contents for compiler naming
  and use, without a concrete installed toolchain version.
- `NPU Runtime` found generic NPU Runtime text in UG1214; it does not identify a
  local runtime package.
- `libnpu_runtime` found APUG1205 placeholder linker flags (`/path/to/...`),
  not a local library path.
- `HPF` and `bitstream` found general FPSoC/NPU generation instructions and
  generated-file references, not an SDK_2026.01 provenance record.

The collection remains keyword-only and has zero vectors. No qmd `embed`,
`query`, vector search, or model download was run.

## Local toolchain, Buildroot, and runtime checks

No `aarch64-linux-gnu-gcc`, `aarch64-none-linux-gnu-gcc`, or
`aarch64-buildroot-linux-gnu-gcc` was found in the current PATH. The documented
`/home/uisrc/.../aarch64-linux-gnu-*` path and the example `/opt/toolchain/...`
paths were also absent. Consequently no ARM compiler `--version` or
`-print-sysroot` output exists for this audit.

No Buildroot tree, `envsetup.sh`, `setenv.sh`, `build.sh`, sysroot, target
rootfs, or CMake toolchain file was found in the bounded SDK/course scan. The
Buildroot PDF is a guide, not a versioned SDK installation.

No local AArch64 Arm NN, OpenCV 4.7.0 package, `libnpu_runtime`, target kernel
module set, or SDK pkg-config/CMake package was found. The official repository's
expected libraries remain Git LFS pointers outside the downloaded content.

HPF and bitstream files do exist under example workspaces, for example
`04_secondary_developmemt/demo/soc_hw/system.hpf` and
`04_secondary_developmemt/demo/soc_sdk/soc_base/platform/system.bit`. They are
generated project artifacts; their SDK/revision and NPU compatibility are not
known.

## Compatibility with `dr1m90_npu` `SDK_2026.01`

The official local repository contains the annotated tag `SDK_2026.01` (tag
object `05c0672ab564405248af2e7d09845960b6c389d3`, peeling to commit
`a06f09a23582900e2b8843d564ea28db679649a5`). The checked-out `release` branch
is currently at a later commit (`199ef4d71f453bb9a000102ff39def09c4cf73f9`),
so it is not an exact tag checkout. Its README states that the repository tag
must match the SDK tag. The following matrix deliberately does not promote
probable matches to matches:

The separate `dr1_demo_prjs` repository has a `2026.1` branch but no matching
SDK tag. The shared `2026.1` text is therefore not treated as evidence that it
is equivalent to `SDK_2026.01`.

| Item | Official repository requirement | Local material | Status | Evidence |
| --- | --- | --- | --- | --- |
| SDK tag | `SDK_2026.01` | No explicit local Linux SDK tag | `unknown` | `dr1m90_npu/README.md:21` and local version scan |
| Chip/source family | DR1M90 NPU source | `CHIP=dr1m90` in FPSoC Makefile | `probable_match` | `soc_base/Makefile:13` |
| AArch64 target | `toolchains/aarch64-linux` | Rules derive `armv8-a`/`aarch64`/`cortex-a35` | `probable_match` | `rules.mk:37-42` |
| AArch64 compiler | SDK `aarch64-linux-gnu-gcc/g++` | No executable at documented or PATH locations | `missing` | host path checks, no compiler run |
| sysroot/libc | SDK target environment | No sysroot or libc identity | `missing` | bounded path scan |
| Buildroot | SDK `envsetup.sh`, `build.sh`, defconfig | Only a Buildroot guide; no tree/scripts | `missing` | qmd and filename scan |
| Arm NN | `npu_demo/libs/armnn_lib` | No local Arm NN directory | `missing` | official path check |
| AArch64 OpenCV | `ffmpeg_opencv4.7.0_aarch64` | No local package/CMake config | `missing` | `npu_demo/build.sh:22-23` and path scan |
| NPU runtime | SDK runtime plus kernel support | No local runtime path; only APUG1205 placeholders | `unknown` | qmd/source evidence |
| HPF/bitstream | SDK-selected NPU-compatible HPF | Generated examples without provenance | `unknown` | metadata-only scan |

Overall compatibility is `unknown`, not `matched`. The local material is not
yet sufficient to check out or use `SDK_2026.01` safely, and it is not sufficient
to build the official NPU demos.

## Can the SDK be used now?

- **Checkout/use `SDK_2026.01`: No.** The official tag is known, but the local
  SDK identity, toolchain, sysroot, libc, and runtime are not.
- **Build the official NPU demo: No.** The required AArch64 compiler, Arm NN,
  AArch64 OpenCV 4.7.0, SDK Buildroot environment, runtime, kernel/module
  support, and matching HPF/bitstream are not validated.
- **Download Git LFS now: No recommendation.** LFS objects in the official
  repository are not needed to answer this metadata audit. Download only after
  a matching SDK and a human-approved model/demo scope are identified.

## Next evidence needed

Request a small, explicit SDK manifest or top-level version record (without
automatically downloading anything), plus the toolchain and sysroot identity:

1. SDK release/tag and checksum;
2. Buildroot revision/defconfig and kernel revision;
3. `aarch64-linux-gnu-gcc --version`, `-dumpmachine`, and `-print-sysroot`;
4. libc/glibc or musl identity;
5. Arm NN, OpenCV 4.7.0 AArch64, NPU runtime, kernel modules, and pkg-config/
   CMake paths;
6. provenance for the HPF/bitstream used by the target image;
7. board/rootfs evidence showing which SDK image is actually booted.

Until those facts are supplied and matched to `SDK_2026.01`, the official NPU
demo build remains blocked. No inference or benchmark work is authorized by
this audit.
