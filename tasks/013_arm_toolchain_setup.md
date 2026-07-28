# Task 013

## Title

Record and validate the Anlogic DR1 ARM CPU toolchain setup.

## Status

Completed

## Stage

Stage 2

## Dependencies

Task 012 (`Completed`) and human approval of Checkpoint C.

## Recommended Branch

`feature/arm-ncnn-aarch64`

## Recommended Commit

`build(arm): establish AArch64 ncnn baseline`

## Goal

Freeze and validate the host-side toolchain and build contract needed to produce
a CPU-only AArch64 ncnn runtime for the MLK-F3P-CZ02-DR1M90 board. Preserve
source, compiler, sysroot, options, outputs, and logs with reproducible
identities before Task 014 performs model inference or measurement.

## Scope

This task may:

- preserve the already verified board, userspace ABI, toolchain, and OpenCV
  baseline;
- install CMake from the existing SDK cache into the VM user's home directory;
- generate a clean ncnn source archive from the fixed Git object;
- create and validate an AArch64 CMake toolchain file;
- cross-build and install a CPU-only, FP32, static ncnn runtime;
- cross-build a model-free ncnn smoke ELF and inspect its AArch64 identity;
- record all commands, hashes, options, logs, and unresolved board-runtime work.

This task does not perform YOLO inference, model conversion, correctness
comparison, benchmark, video, camera, Vulkan, NPU, quantization, system
installation, SDK modification, or board access.

## Previously Verified Inputs

- Board: `MLK-F3P-CZ02-DR1M90`.
- Architecture: AArch64, two CPU cores, CPU part `0xd04`.
- OS: Buildroot `2022.02.6`.
- Kernel: `6.1.111-rt42`.
- Userspace: glibc `2.25`, loader `/lib/ld-linux-aarch64.so.1`.
- Cross compiler: Linaro GCC/G++ `7.5.0`, target
  `aarch64-linux-gnu`.
- Sysroot:
  `/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/aarch64-linux-gnu/libc`.
- Static C, dynamic C, dynamic C++, and OpenCV 4.7 board smokes: passed.
- ncnn: official tag `20240410`, commit
  `56775de50990ab7f16627efdcf5529b49541206f`.

These facts come from the tracked vendor/toolchain/board manifests and real
execution records. They do not prove that an AArch64 ncnn ELF has run on the
board.

## Allowed Files

```text
TASKS.md
tasks/013_arm_toolchain_setup.md
configs/toolchains/anlogic-dr1-aarch64.cmake
cpp/apps/anlogic_ncnn_smoke.cpp
scripts/vendor/build_anlogic_aarch64_ncnn.sh
scripts/vendor/validate_anlogic_aarch64_ncnn.sh
docs/vendor/ANLOGIC_AARCH64_NCNN_BUILD.md
.knowledge/manifests/anlogic_aarch64_ncnn_build.yaml
results/evidence/013/anlogic_ncnn_board_smoke.json
```

Repository-external generated work is allowed only under:

```text
/tmp/ncnn-20240410-56775de.tar.gz
/home/uisrc/.local/cmake-3.16.9
/home/uisrc/build-tools/cmake-3.16.9
/home/uisrc/build/ncnn-aarch64
/home/uisrc/vendor/anlogic/logs/arm_ncnn_build
```

## Forbidden Files and Actions

- Do not modify Tasks 001–012 or 016, PC benchmark evidence, PC golden results,
  frozen model artifacts, labels, thresholds, or model manifests.
- Do not commit CMake/ncnn source, archives, SDK files, build directories,
  libraries, ARM ELF files, or full external logs.
- Do not use `sudo`, install into system directories, modify the SDK, or change
  shell startup files.
- Do not access the development board in this task.
- Do not run YOLO, pnnx, model conversion, benchmark, video, camera, Vulkan, or
  NPU work.
- Do not download a replacement dependency while an approved local source is
  sufficient.

## Frozen Build Contract

### Source

- Remote: `https://github.com/Tencent/ncnn.git`.
- Tag: `20240410`.
- Commit: `56775de50990ab7f16627efdcf5529b49541206f`.
- License: BSD 3-Clause with the third-party notices in `LICENSE.txt`.
- Snapshot: `git archive` from the exact commit; do not copy the dirty working
  tree or initialize submodules.
- `python/pybind11` and `glslang` are excluded by disabling Python and Vulkan.

### Build Host and Target

- Host: Ubuntu 18.04.4 x86_64 VM, glibc 2.27.
- CMake: 3.16.9 installed under `/home/uisrc/.local`.
- Generator: Unix Makefiles with GNU Make.
- Target: AArch64 Linux, Buildroot 2022.02.6, glibc 2.25.
- Compiler and sysroot: the absolute paths in
  `configs/toolchains/anlogic-dr1-aarch64.cmake`.

### ncnn Options

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

These names were verified against the fixed revision. `NCNN_BF16=ON` retains
the revision's required conversion implementation when VFPV4 is compiled in;
the smoke still explicitly disables BF16 storage, FP16, INT8, and Vulkan at
runtime.

## Build Commands

The exact CMake bootstrap, source archive, transfer, configure, build, install,
and smoke commands must be preserved in the Execution Record and external logs.
The repository scripts provide the reviewed repeatable entry points after their
first real validation.

## Test Commands

```bash
bash -n scripts/vendor/build_anlogic_aarch64_ncnn.sh
bash -n scripts/vendor/validate_anlogic_aarch64_ncnn.sh
python3 -c 'import pathlib, yaml; yaml.safe_load(pathlib.Path(".knowledge/manifests/anlogic_aarch64_ncnn_build.yaml").read_text())'
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
git diff --check
```

The external validation must also inspect `libncnn.a` and the smoke ELF with
`file`, `readelf`, and SHA256. It must not execute the AArch64 ELF in the x86_64
VM.

## Acceptance Criteria

1. CMake 3.16.9 is built from the recorded local source hash and runs from the
   VM user's install prefix.
2. The clean ncnn archive is generated from the exact fixed commit and has a
   recorded SHA256.
3. The checked-in toolchain file configures with the real compiler, target
   triple, sysroot, loader, libc, libstdc++, libgcc, pthread, and startup
   objects.
4. The fixed ncnn options configure successfully without Python, glslang,
   Vulkan, OpenMP, tools, examples, tests, or benchmark targets.
5. Release build and install succeed and produce a nonempty static `libncnn.a`,
   headers, and CMake package metadata with recorded hashes.
6. The model-free smoke source cross-builds into an ELF64 AArch64 executable
   with no x86 object or unexpected Vulkan/Python dependency.
7. Source, CMake, toolchain, options, install tree, hashes, commands, and logs
   are recorded in the manifest and documentation.
8. The smoke ELF is transferred to and runs successfully on the real board in
   a separately authorized follow-up.
9. All repository syntax, manifest, whitespace, Allowed Files, and staged-diff
   checks pass.

Task 013 becomes `Completed` only after criterion 8 has passed on the real
board. Task 014 remains `Planned`.

## Repair Rules

At most three complete repair loops may address CMake bootstrap, cross-configure,
toolchain search, ncnn compilation, installation, or smoke linking errors. Each
loop must preserve the fixed source revision, target ABI, sysroot, feature
boundaries, and evidence. Never pass by weakening architecture checks, using a
host library, enabling a forbidden feature, or fabricating output.

## Human Stop Conditions

Stop if progress requires root/system changes, credentials, board access,
SDK mutation, user-data replacement, model/golden changes, a different ncnn
revision, or a technology-route change. Ordinary missing commands, initial
compile failures, path corrections, and fixed-option corrections are repairable
within the user-authorized workspace.

## Execution Record

Started: `2026-07-28T11:00:00+08:00`

Branch: `feature/arm-ncnn-aarch64`

Starting commit: `ff14c3303ad4cdd541254db67671de667dd22c2e`

Starting Git status: clean; HEAD equals local `dev`.

The detailed real commands, attempts, identities, results, and final status are
appended after the build and validation complete.

### Fixed Source and CMake

The ncnn source identity was reverified from Git objects:

```text
remote: https://github.com/Tencent/ncnn.git
tag: 20240410
commit: 56775de50990ab7f16627efdcf5529b49541206f
license SHA256: 6495f972a09ad7f64ccd953e79adba91a93d862edc7135e6d95210bbf4002a01
```

The WSL worktree has only the pre-existing `python/pybind11` submodule
difference. The task did not copy that worktree. Two independent `git archive`
invocations from the fixed commit produced the same archive:

```text
path: /tmp/ncnn-20240410-56775de.tar.gz
size: 12,840,688 bytes
members: 3,446
SHA256: 81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45
```

Source inspection proved that pybind11 is gated by `NCNN_PYTHON` and glslang
is gated by `NCNN_VULKAN`. Both options are off, and neither submodule content
exists in or is required by the clean snapshot.

The VM had no system CMake. The existing SDK cache source archive was used:

```text
source: /home/uisrc/vendor/anlogic/sdk/sdk/buildroot/dl/cmake/cmake-3.16.9.tar.gz
size: 9,113,695 bytes
SHA256: 1708361827a5a0de37d55f5c9698004c035abb1de6120a376d5d59a81630191f
workspace: /home/uisrc/build-tools/cmake-3.16.9
prefix: /home/uisrc/.local/cmake-3.16.9
commands: bootstrap --prefix=<prefix>; make -j2; make install
installed version: 3.16.9
installed executable SHA256: fa6d96ed54cbb20be01e16a275e6f86e97ed76953c113c8fffa2de18123f42b5
```

All CMake files stayed in the VM user's home. No system package, `sudo`,
network source, or system directory was used.

### Toolchain and Configure

The compiler again reported Linaro GCC/G++ 7.5.0, target
`aarch64-linux-gnu`, and the recorded glibc 2.25 sysroot. The loader, libc,
libm, libpthread, libdl, librt, libstdc++, libgcc_s, and startup objects were
present. The checked-in toolchain file SHA256 is:

```text
8ba63b21a1fa6bb2d3ddb391c686e460ea08d39a521592540997e76edb5359b0
```

Real CMake C/C++ compiler and ABI checks passed, pthread was found with
`-pthread`, and ncnn reported target `arm 64bit`. The final cache has:

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

The SDK OpenCV 4.7 headers, CMake config, and core/imgproc/imgcodecs libraries
again reported AArch64. The current package does not contain the previously
recorded `lib/pkgconfig/opencv4.pc`; this conflict is recorded but does not
affect the ncnn build, which consumes no OpenCV.

### Build, Install, and Smoke

Configure, the repaired build, install, and smoke link exited zero. The install
tree has 33 entries and includes headers, `lib/libncnn.a`,
`lib/cmake/ncnn/`, and `lib/pkgconfig/ncnn.pc`.

```text
libncnn.a size: 4,087,846 bytes
libncnn.a SHA256: 5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a
archive members: 180
AArch64 members: 180
```

The model-free C++17 smoke creates `ncnn::Net`, forces one thread, disables
Vulkan and low-precision runtime options, allocates an FP32 `ncnn::Mat`, and
checks a fixed sum. It does not load a model.

```text
artifact: /home/uisrc/build/ncnn-aarch64/anlogic_ncnn_smoke
size: 2,553,816 bytes
SHA256: cad23a736f86b0d1ae6f9cfd938dce55732a3fc983a5baaa5a31fde0e393b8f7
class/machine: ELF64 / AArch64
interpreter: /lib/ld-linux-aarch64.so.1
maximum GLIBC requirement: GLIBC_2.17
maximum GLIBCXX requirement: GLIBCXX_3.4.21
prohibited Vulkan/Python/libgomp dependency: absent
```

The AArch64 ELF was not executed in the x86_64 VM.

### Repair Attempt 1: CMake Session Orchestration

```text
Failure: a shell-logging quoting error and local SSH interruption left one
  task-owned bootstrap process running; a second bootstrap collided with it
  and reported "Text file busy"
Diagnosis: process inspection showed the first bootstrap still configuring in
  the dedicated workspace
Recovery: allowed the surviving bootstrap to complete, verified its Makefile,
  then ran make -j2 and make install once
Result: CMake 3.16.9 build and user-local install PASS
```

### Repair Attempt 2: Fixed-Revision BF16 Compile Combination

```text
Failure: with NCNN_VFPV4=ON and NCNN_BF16=OFF, net.cpp failed in two empty
  compile-time conditional chains
Diagnosis: fixed-revision source inspection showed dangling VFPV4 "else" paths
  when the BF16 conversion branch was compiled out
Recovery: restored NCNN_BF16=ON without patching source; smoke runtime keeps
  BF16 storage, FP16, INT8, and Vulkan explicitly disabled
Result: complete static ncnn build, install, and smoke link PASS
```

### Evidence and Acceptance Status

External logs are preserved at:

```text
/home/uisrc/vendor/anlogic/logs/arm_ncnn_build
/home/uisrc/build/ncnn-aarch64/logs
```

The structured record is
`.knowledge/manifests/anlogic_aarch64_ncnn_build.yaml`.

| Criterion | Status |
| --- | --- |
| 1. User-local CMake | PASS |
| 2. Clean fixed ncnn archive | PASS |
| 3. Toolchain/sysroot configure | PASS |
| 4. Frozen feature options | PASS |
| 5. Static ncnn build/install | PASS |
| 6. AArch64 model-free smoke build/inspection | PASS |
| 7. Provenance record | PASS |
| 8. Real board smoke execution | PASS |
| 9. Repository final checks | PASS |

Final repository validation completed:

```text
build script bash syntax: PASS
validation script bash syntax: PASS
build entry point --check: PASS
external artifact validator: PASS
manifest YAML parse: PASS
toolchain CMake static parse: PASS
model-independent Release configure/build: PASS
model-independent CTest: 4/4 PASS
Python unittest: 64/64 PASS
Markdown internal links: PASS
sensitive information scan: PASS
git diff --check: PASS
Allowed Files audit: PASS
```

### Real Board Runtime Completion

Resumed: `2026-07-28T15:00:00+08:00`

Starting commit: `64b898db84de0287f4f2b81b693951e77accbca3`

The frozen ELF was absent from WSL and was therefore revalidated at its VM
build path, copied byte-for-byte to `/tmp/edgeai-anlogic-deploy/`, and checked
again before deployment:

```text
VM source: /home/uisrc/build/ncnn-aarch64/anlogic_ncnn_smoke
WSL staging: /tmp/edgeai-anlogic-deploy/anlogic_ncnn_smoke
VM/WSL SHA256: cad23a736f86b0d1ae6f9cfd938dce55732a3fc983a5baaa5a31fde0e393b8f7
identity: ELF64 AArch64
interpreter: /lib/ld-linux-aarch64.so.1
```

The board wrapper connected as `root` to the real Buildroot target. The task
created only `/root/edgeai/ncnn-smoke-20240410`, transferred the ELF through
SSH stdin, verified its SHA256, and changed only that file's mode from `0600`
to `0700`. The hash remained unchanged.

The board reported:

```text
hostname: buildroot
architecture: aarch64
OS: Buildroot 2022.02.6
kernel: 6.1.111-rt42
libc: glibc 2.25
memory: 988.7 MiB
getconf/file/readelf/timeout: NOT_AVAILABLE
board clock: not synchronized (1970-01-01)
```

The absence of board-side `file` and `readelf` did not weaken the gate because
the exact same SHA256 had already passed host-side `file` and `readelf`
inspection. Board-side `ldd` exited zero, contained no `not found`, and resolved
the loader plus `libdl`, `libstdc++`, `libm`, `libgcc_s`, `libpthread`, and
`libc` from `/lib`.

The ELF was executed directly without `LD_LIBRARY_PATH`, loader overrides, or
system-library changes:

```text
program=edgeai_anlogic_ncnn_smoke
ncnn_version=1.0.20240410
reported_cpu_count=2
configured_threads=1
vulkan_enabled=0
fp16_storage_enabled=0
fp16_arithmetic_enabled=0
bf16_storage_enabled=0
int8_inference_enabled=0
mat_sum=10
runtime_contract=PASS
stderr: empty
exit code: 0
```

The normalized evidence is
`results/evidence/013/anlogic_ncnn_board_smoke.json`, SHA256
`dd7ba7d247d7cf459cffe2662130e1af7ea6b57a04056bdaad861610c377021c`.
Nine remote text records were copied to WSL `/tmp`, and every local copy passed
the board-generated SHA256 list.

Completed: `2026-07-28T15:21:23+08:00`

Task 013 is `Completed`. This completion covers the toolchain, static ncnn
host build, model-free AArch64 smoke build, dependency closure, and real board
runtime only. Task 014 remains `Planned`; no model, inference, correctness
comparison, benchmark, video, camera, Vulkan, or NPU work occurred.
