# Anlogic NPU package and build-chain intake (Task 023)

Status: **Completed audit**. This document is a read-only provenance and static
compatibility review. It does not approve module loading, FPGA configuration,
image flashing, vendor-program execution, or project-model conversion.

The audit was user-approved (`audit_review: PASS`, `candidate_approved: true`).
Deployment readiness remains `BLOCKED`; the vendor one-shot was not executed,
controlled board deployment was not approved, and project YOLOv5n conversion is
not ready.

## Target and source boundaries

The target is `MLK-F3P-CZ02-DR1M90`, AArch64, Buildroot 2022.02.6, Linux
`6.1.111-rt42`, glibc 2.25. The package root is the user-provided
`NPU_info` directory under `F3P_DR1M90GEG400_FPGA`; it contains 1,800 files
and 886,827,911 bytes. Vendor binaries, modules, HPFs, bitstreams, images,
models, and archives remain outside Git. The knowledge base is read-only.

The requested knowledge-base `.knowledge/manifests/versions.yaml` is absent.
Version statements therefore use the knowledge base `VERSION_MATRIX.md` and
its recorded repository manifests. This is a provenance limitation, not a
version guess.

## Source chain reconstructed

The approved AlWiki captures provide four relevant source roles:

| Source | What it explicitly says | What it does not prove |
| --- | --- | --- |
| D20.0 (`6Pb5TSd5`) | CMA APIs, quantization, preprocessing/postprocessing, `NPUExecutor`, and backend preference topics | A versioned runtime package or current-board ABI |
| D20.1 (`7ZcKp5Wg`) | AD101V20 SD/TD example names, HPF placement, three kernel menuconfig symbols, DR1M90 defconfig/rootfs/app flow | That the named attachments map to this eMMC image |
| D20.3 (`C3WjPRyU`) | DR1M90 application concept using an AD101V20 USB-camera/HDMI example and `dr1m90_npu` source | Current-board bitstream, driver, and runtime compatibility |
| APUG1205_0.1 | HardNPU/SoftNPU cooperation, `hard_npu.ko`, `soft_npu.ko`, `cma_mem.ko`, `npu_runtime`, `convert_tool`, `al_ai_flow`, `rt.bin`, and `weight.bin` flow | That any of those packages are locally complete |

The official Gitee mirror is `https://gitee.com/anlogic/dr1m90_npu.git`, fixed in
the knowledge base at SDK_2026.01. The local SDK matrix records SDK_2025_07.
Shared CMake files between the mirror and the extracted face-detection archive
show source lineage, but differing build scripts and application sources do
not establish one release.

## Hardware and board mapping

The package is a mixed collection:

- the Milianke `soc_prj.al` says `DR1M90GEG400` and contains a SoftNPU project,
  HPF, bitstream candidates, DT files, and a derived face-detection archive;
- D20.1 and D20.3 projects are named `AD101V20`;
- D20.2 is named `AD103V20`;
- IPUG166 documents `DR1M90GEG484-2` and TD 5.9.1 Beta1.0.

These are source/document facts. The current board name alone is not enough to
select an HPF or bitstream. The active board bitstream and its DT mapping were
not changed or inferred.

The supplied DT fragment contains `compatible = "anlogic,soft_npu"` and a
SoftNPU register/interrupt entry. It is a demo DT fragment, not evidence that
the current eMMC DT contains the same node. A bitstream, HPF, DT, driver and
runtime must be version-matched as one release.

## Linux SDK and drivers

D20.1 and the official README document selecting:

```text
hard_npu_driver
soft_npu_driver
cma_mem_driver
```

The derived package's CMake discovers the three driver Makefiles and builds
`obj-m` modules. Static inspection found:

| Module | Static identity | Device/compatibility fact |
| --- | --- | --- |
| `hard_npu.ko` | AArch64 relocatable; SHA256 `f06a2735…`; vermagic `6.1.111-rt42 SMP preempt mod_unload aarch64` | source matches `anlogic,hard_npu` |
| `soft_npu.ko` | AArch64 relocatable; SHA256 `e2c10bb6…`; same vermagic | source matches `anlogic,soft_npu` |
| `cma_mem.ko` | AArch64 relocatable; SHA256 `b2204e71…`; same vermagic | miscdevice named `cma_mem`, DMA/CMA allocation and sync |

The prebuilt vermagic happens to match the observed board kernel text. The
source Makefiles, however, default to Linux 5.10.142 and an
`aarch64-anlogic-11.3` prefix, while `build.sh` names an unprovided
`uisrc-lab-anlogic` kernel/toolchain. No current-kernel source/config build was
run. A vermagic match is necessary but not sufficient for a register map,
Device Tree, HPF, or SoftNPU operator match.

The current board observation remains the Task 022 result: 128 MiB CMA is
reserved and a hard-NPU DT/platform node is visible, but no NPU/CMA module is
loaded, no matching module was found under `/lib/modules`, and no NPU/CMA
device nodes were present.

## Two user-space execution paths

The evidence separates two paths that are often conflated:

1. **Native APUG `npu_runtime` path.** APUG1205 describes
   `convert_tool`/`al_ai_flow` producing `rt.bin` and `weight.bin`, then an
   application linking `-lnpu_runtime` and calling driver, interrupt, CMA and
   model-loading APIs. None of that standalone package, its host converters,
   or its model pair was found in the bounded intake.
2. **Arm NN/ONNX path.** The face-detection source loads
   `yolo_face_uint8_15.onnx` through `libarmnnOnnxParser`, optimizes with
   backend preferences `Alnpu,CpuAcc,CpuRef`, and calls Arm NN workload APIs.
   Its CMake links `libarmnn`, `libarmnnOnnxParser`, protobuf and OpenCV; it
   does **not** link `npu_runtime` and its source does not read `rt.bin` or
   `weight.bin`.

The paths are distinct at the model/API layer, so missing native-runtime
assets do not by themselves disprove the Arm NN path. They share the board
substrate: matching HardNPU/SoftNPU drivers, CMA allocator, Device Tree,
active HPF/FPGA bitstream and board ABI. The Arm NN library itself contains
Alnpu/driver/CMA symbols and references `/dev/hard_npu`, `/dev/soft_npu`,
`/dev/cma_mem` and `/dev/mem`; a successful link is not a running NPU runtime.

## Runtime and demo boundary

The nested archive contains AArch64 Arm NN and ONNX parser libraries, Arm NN
headers including CMA helpers, an ONNX face model, and a prebuilt
`yolo_demo_hdmi_camera`. The ELF is AArch64 and uses an embedded build-host
RPATH; it links OpenCV, Arm NN/Alnpu-facing libraries, protobuf, libdrm, and
system C/C++ libraries. It was not executed.

This is an Arm NN/Alnpu demo candidate, not proof of the standalone
`npu_runtime` package named by APUG1205. The direct bounded search found no
`rt.bin`, `weight.bin`, `convert_tool`, `al_ai_flow`, or standalone
`libnpu_runtime`. An ONNX example model is not the frozen project YOLOv5n
model and was not substituted.

The Arm NN library's observed maximum requirements (GLIBC 2.17 and GLIBCXX
3.4.22 for `libarmnn.so.32.1`) are only a surface ABI check. They do not prove
that Alnpu can open a current-board device or that the matching SoftNPU
hardware exists.

The demo `main.cpp` requires an ONNX model, server and user configuration,
defaults to `/dev/video0`, creates a CMA resource zone, and uses an HDMI/DRM
path. Its `scripts/run_usbcam.sh` sets private library paths but omits the
required `-s` server argument, so it is not a complete deployment command.
The bundled ONNX model is an example face model, not the frozen project
YOLOv5n asset. No demo or vendor ELF was executed.

## Static module and source-build review

The SDK kernel source available in the VM is
`/home/uisrc/vendor/anlogic/sdk/sdk/linux`, with a 6.1.111 Makefile,
`anlogic_dr1m90_defconfig`, NPU Kconfig symbols, and candidate hard/soft NPU
Device Tree files. The isolated build enabled the three symbols as modules
and generated AArch64 objects with the board-kernel vermagic. However,
`Module.symvers` was absent and modpost reported unresolved-symbol warnings;
the objects have no symbol-CRC proof. The prebuilt modules likewise have empty
`depends` fields and no `__versions` section. Vermagic is positive evidence,
not a loadability proof.

The VM wrapper's first sandboxed invocation failed with
`UtilBindVsockAnyPort: socket failed 1`; an escalated read-only invocation
reached the VM, so this was a WSL/vsock access issue rather than a build
failure. With user-local CMake 3.16.9, Linaro GCC/G++ 7.5.0 and the SDK
sources, the driver-source build completed with the limitation above. The
Arm NN face demo also configured, built and linked in an isolated workspace;
its AArch64 output SHA256 is recorded in
`results/evidence/023/npu_build_attempt.json`. Neither build touched the
board or copied artifacts into Git.

## Build decision

Source/link closure is now partially verified, but a reproducible,
deployment-ready package is not. The exact package release identity, active
board bitstream and DT mapping, Module.symvers/symbol CRC provenance, native
runtime assets, and current-board device binding remain unresolved.

## Verdict and next gate

Primary verdict: **`BLOCKED_BOARD_HARDWARE_MAPPING`**.

Secondary blockers:

- `BLOCKED_NATIVE_RUNTIME_ASSETS`;
- `BLOCKED_ARMNN_BACKEND_INCOMPLETE`;
- `MODULE_SYMBOL_CRC_UNVERIFIED`;
- `BLOCKED_BUILD_REPRODUCIBILITY`;
- `BLOCKED_PREBUILT_DEMO_DEPLOYMENT`;
- `BLOCKED_MODEL_ASSET_INCOMPLETE`;
- `BLOCKED_PROVENANCE_OR_LICENSE`;
- `BLOCKED_PACKAGE_RELEASE_IDENTITY`;
- `BLOCKED_RUNTIME_INCOMPLETE`;
- `BLOCKED_TOOLCHAIN`;
- `ACTIVE_BITSTREAM_UNKNOWN`;
- `ACTIVE_DEVICE_TREE_MAPPING_UNKNOWN`.

This is a current package/readiness block, not a claim that DR1M90 hardware
permanently lacks NPU support. Before a controlled build, obtain a single
versioned package for the exact board and kernel containing matching driver
source/modules, kernel source/config, HPF/bitstream/DT mapping, runtime
headers/libraries, official model assets, host converters, and license terms.
Only then should a separate deployment approval consider loading modules or
writing an image.

Evidence: `results/evidence/023/npu_package_inventory.json`,
`npu_wiki_source_map.json`, `npu_project_dependency_graph.json`,
`npu_driver_build_analysis.json`, `npu_runtime_demo_analysis.json`,
`npu_static_compatibility.json`, `npu_build_attempt.json`, and
`npu_package_verdict.json`.
