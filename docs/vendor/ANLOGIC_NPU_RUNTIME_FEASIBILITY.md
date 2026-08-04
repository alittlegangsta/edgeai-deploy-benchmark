# Anlogic DR1 NPU runtime and official YOLO one-shot feasibility

Task 022 is a read-only audit of the approved local Anlogic/Milianke material,
the VM vendor tree, and the real MLK-F3P-CZ02-DR1M90 board. It does not convert
the frozen project model, load a kernel module, modify the board, or run a
vendor executable.

## Result

```text
Task 022: Completed
automated_audit: COMPLETE
audit_review: PASS
audit_review_source: user
candidate_approved: true
NPU feasibility: BLOCKED_DRIVER_OR_DEVICE
vendor one-shot: NOT_EXECUTED
project YOLOv5n NPU conversion: NOT READY
```

The approval was recorded in WSL at `2026-08-04T10:21:18+08:00`. This is the
approval-record time, not the VM audit time, board audit time, or an NPU
program runtime. The approval covers the feasibility audit only; it does not
authorize driver loading, board changes, one-shot execution, or model
conversion.

The supplemental official AlWiki review was approved by the user at
`2026-08-04T11:04:19+08:00` in WSL. This is the Wiki review record time, not a
VM audit time, board audit time, or NPU program runtime. Task 022 is therefore
complete as an audit; NPU deployment readiness remains blocked.

The automatic result is a device/runtime readiness finding, not a claim that
DR1 has no NPU. The board exposes a `hard_npu` device-tree/platform node and
reserves 128 MiB CMA, but the current eMMC userspace has no bound NPU driver,
no NPU/CMA module loaded or present in `/lib/modules`, and no
`/dev/hard_npu`, `/dev/soft_npu`, or `/dev/cma_mem` nodes. A read-only rootfs
search found no board-side NPU runtime or model artifacts.

## Documented vendor contract

The approved local `APUG1205_0.1` document (SHA256
`54a25d9a5dc59b21e7f7253bc72adeeb2c8b3a4bc04c30bea81463026ef7c1f2`) describes
PS-side HardNPU and PL-side SoftNPU cooperation. It documents a SoftNPU
bitstream requirement, a runtime release package containing `include`, `lib`,
and `linux_driver`, and the drivers `hard_npu.ko`, `soft_npu.ko`, and
`cma_mem.ko`. The documented userspace link name is `npu_runtime`; the
documented model flow creates `rt.bin` and `weight.bin` using `convert_tool`
and `al_ai_flow`. Its runtime reference list includes a Yolo one-shot that
performs YUV-to-RGB, resize, graph execution, and output retrieval.

The approved local `IPUG166_1.0` document (SHA256
`d13f70fa563c9d43bb568bcd80edab32ad74a8b6e4a868339119eba6f1945fb7`) describes
the Video NPU as a PL-side SoftNPU/CSC/Resize IP and names DR1M90GEG484-2 as
the resource-example target. These are document facts; they do not prove the
current eMMC bitstream or kernel image satisfies the contract.

## What was found

The VM is Ubuntu 18.04.4 x86_64, glibc 2.27, GCC/G++ 7.5.0, with no CMake,
Ninja, Docker, `convert_tool`, or `al_ai_flow` in the bounded search. The
SDK_2025_07 tree contains AArch64 Arm NN/ONNX parser candidates:

```text
libarmnn.so.32.1       SHA256 5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce
Arm NN version marker  ed5ae24
libarmnnOnnxParser.so.24.6
```

`libarmnn.so` has `Alnpu`/`ALHardNPU` symbols, but this is not a standalone
`libnpu_runtime` release and cannot establish a usable board path without the
matching driver and device nodes. The SDK contains NPU driver source and
Arm-NN YOLO demo source, but no prebuilt `.ko`, no identified
`libnpu_runtime`, and no `rt.bin`/`weight.bin` pair in the searched tree.

The board is AArch64, Buildroot 2022.02.6, Linux 6.1.111-rt42, glibc 2.25,
and dual-core. `lsmod` showed only `aic_load_fw`; `modinfo` is unavailable.
The hard-NPU platform node is unbound. CMA is reserved (`CmaTotal=131072 KiB`,
`CmaFree=130128 KiB`), but CMA reservation alone is not the documented
allocator-driver readiness signal. The absent driver/device prerequisites are
the primary `BLOCKED_DRIVER_OR_DEVICE` verdict. Secondary blockers are
`BLOCKED_MISSING_VENDOR_ASSETS`, `BLOCKED_RUNTIME_ABI_OR_IDENTITY_UNVERIFIED`,
`BLOCKED_TOOLCHAIN`, `BLOCKED_DOCUMENTATION_GAP`, and
`UNKNOWN_BITSTREAM_DT_MAPPING`.

The AArch64 `libarmnn.so.32.1` candidate requires `GLIBC_2.17` and
`GLIBCXX_3.4.22`. That is only a surface ABI candidate; it is not the
documented `npu_runtime`, and it cannot replace the missing drivers, device
nodes, runtime API package, or model artifacts.

## Why no one-shot was run

The safety gate requires a version-matched official runtime, compatible loaded
drivers and device nodes, known SoftNPU bitstream provenance, complete official
model artifacts, and a documented isolated command. Multiple gates failed, so
running an Arm NN sample or guessing runtime arguments would not be an
official one-shot validation. No module was loaded, no bitstream or system
library was changed, and no project model was converted.

## Exact vendor request checklist

Request a version-matched package for `MLK-F3P-CZ02-DR1M90`, AArch64,
Buildroot 2022.02.6, Linux 6.1.111-rt42, and glibc 2.25:

1. `hard_npu.ko`, `soft_npu.ko`, and `cma_mem.ko`, plus complete matching
   source, Makefile, kernel configuration/build instructions, vermagic,
   module order/parameters, expected dmesg/device nodes, and rollback steps.
2. AArch64 `npu_runtime` libraries, C/C++ headers, version/API/error-code
   documentation, link instructions, dependencies, license, and the
   glibc/libstdc++ and kernel compatibility matrix.
3. The matching SoftNPU bitstream, HPF/hardware-platform file, Device Tree or
   overlay, kernel configuration, version mapping, safe load method, affected
   system functions, and rollback procedure.
4. The official one-shot source or ELF, test image, model identity,
   `rt.bin`, `weight.bin`, configuration, run script, expected output, hashes,
   and version information.
5. `convert_tool`, `al_ai_flow`, quantization/model compiler tools, supported
   operators, version matrix, host OS/Python requirements, format and YOLO
   limitations, and license/dongle requirements.

Only after that package is reviewed should the project consider a separate
official one-shot test. The frozen ncnn YOLOv5n model must not be substituted
for a missing vendor model.

## Evidence and safety

Structured evidence is under [`results/evidence/022/`](../../results/evidence/022/):

- `npu_asset_inventory.json` — bounded local asset identities;
- `npu_document_requirements.json` — document facts and requirements;
- `npu_vm_audit.json` — VM tools and SDK candidate identities;
- `npu_board_audit.json` — real board modules, nodes, DT, and CMA observations;
- `npu_dependency_matrix.json` — requirement-by-requirement gap matrix;
- `npu_feasibility_verdict.json` — verdict and precise next request.

No `npu_vendor_one_shot_run.json` exists because no one-shot was executed;
the formal evidence is `executed: false`, `status: NOT_EXECUTED`.
Task 017–021 evidence and the frozen CPU/ncnn contracts were not modified.

The audit does not claim that DR1M90 permanently lacks NPU support. It records
that the currently available vendor materials, VM, and eMMC image do not yet
provide the complete safe execution contract. Project YOLOv5n conversion,
NPU performance benchmarking, and UVC-camera NPU inference must remain blocked
until the requested version-matched package and deployment plan are reviewed.

## Incremental official AlWiki audit

Task 022 is `Completed` as an audit after user approval of this supplemental
public-source review; the prior local/VM/board audit approval remains
preserved. Seven
explicitly selected pages in organization `AzZaqNHH` / source `SdAMW8ED` were
read serially through the anonymous official API, all returning HTTP 200. The
page tree reported 526 pages, but no full crawl or search-result expansion was
performed. Responses were parsed in memory with a field whitelist; raw
responses, cookies, authorization values, and token values were not saved or
hashed. No VM or board was accessed in this pass.

The most actionable page is `D20.1 NPU 简单示例集合` (`7ZcKp5Wg`). Its explicit
content names a DR1M90 Buildroot defconfig, an HPF assignment, enabling
`hard_npu_driver`, `soft_npu_driver`, and `cma_mem_driver`, increasing the
rootfs size from 128M to 300M for the example, building `app/npu` and the SDK
image, and SD booting an NPU demo. It references
`D21.1_NPU_Simple_demo_sd_image.zip` and `TD_D20.1_AD101V20_2025.7.zip`, but
the public API exposed no download URL, size, SHA256, license, or permission
state for those assets. The page therefore documents a flow, not possession
of a deployable package for the current eMMC image.

`D20.0 NPU接口文档` (`6Pb5TSd5`) documents `NPUExecutor`, quantization, and
CMA buffer API symbols (`cma_mem_*`, `npu_input_quant_param_init`) and a
backend/load/inference/postprocess flow. It does not identify a standalone
runtime filename, version, ABI matrix, or headers package. The D20.3 UVC/HDMI
page mentions DR1M90 but uses AD101V20 examples and supplies no current kernel
or runtime mapping. `IPUG166_Video_NPU_IP用户手册` names DR1M90GEG484-2 and TD
5.9.1 Beta1.0, which differs from the current MLK-F3P-CZ02-DR1M90,
Buildroot 2022.02.6, Linux 6.1.111-rt42 contract. `APUG1205_NPU参考设计文档`
and the D20 index add HardNPU/SoftNPU context but no downloadable package.

No `.ko`, HPF/bitstream, runtime library/header package, one-shot ELF,
`rt.bin`, `weight.bin`, converter, or other vendor file was obtained. A
file-list embed exists on D20.1, but its filename/URL/size/permission metadata
was not exposed. The auxiliary status is therefore
`OFFICIAL_ASSETS_IDENTIFIED_ACCESS_PENDING`, while the primary verdict remains
`BLOCKED_DRIVER_OR_DEVICE`. `vendor_one_shot.executed` remains `false` and no
`npu_vendor_one_shot_run.json` exists. Browser-rendered/PDF export is optional
and remains `PENDING`; it is not needed to establish the API audit result
because the API content itself was readable.

Evidence: [`npu_official_wiki_audit.json`](../../results/evidence/022/npu_official_wiki_audit.json).
The next safe action is to request a version-matched vendor package and, if
needed, a manual browser export of the referenced file-list assets. Do not
convert the project YOLOv5n model or load a driver on the basis of this Wiki
flow alone.
