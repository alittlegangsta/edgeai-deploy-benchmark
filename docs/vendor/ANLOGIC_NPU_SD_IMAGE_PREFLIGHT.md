# Anlogic DR1 NPU SD-image preflight

Task 025 is an automatic, pre-write audit for an independent MLK-F3P-CZ02
NPU SD boot candidate. It does not write an SD card or eMMC, load a kernel
module, configure the FPGA, replace the current system, execute a vendor NPU
program, or convert the project YOLOv5n model.

## Target and source lines

The target is `MLK-F3P-CZ02-DR1M90` / `DR1M90GEG400`, AArch64, Buildroot
2022.02.6, Linux 6.1.111-rt42 and glibc 2.25. The strongest board-level lead
is the Milianke project under the supplied `03_demo/05-5_NPU演示/demo` tree:
its TD project declares `DR1M90GEG400` and supplies an HPF, a bitstream, a
Device Tree and prebuilt boot files. Those files are candidate identities, not
the active eMMC files and are not copied into Git.

The official Linux SDK release line is `SDK_2025.07-linux6.1` at commit
`beaee2ce45161908403a92619e509f52220ac347`. A clean detached superproject
clone and checkout were reproducible, but recursive submodule materialization
failed because the local relative submodule repositories were not available in
the no-network WSL scope. The vendor release
`/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz` (SHA256
`c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`) contains
the fuller Linux/Buildroot/U-Boot/FSBL/toolchain payload and was extracted in
an isolated VM workspace, but it has no `.git` metadata and cannot prove exact
submodule commit provenance. Both source lines contain AD101V20/AD103V20
BoardConfig files and no MLK-F3P-CZ02 BoardConfig.

The local `dr1m90_npu` repository is on the separate `SDK_2026.01` release line.
The `boardimages` repository contains an AD101V20 payload only. Neither fact
closes the MLK mapping; an AD10x image must not be used as an MLK image.

See the structured source and dependency records in
`results/evidence/025/npu_sd_source_inventory.json` and
`results/evidence/025/npu_sd_build_chain.json`.

## `03_demo` and Milianke NPU package audit

The bounded inventory classified `03_demo/05-5_NPU演示` as the only direct
NPU target. `3-2_ex_fpsoc/03_boot_mode` and
`3-4_ex_soc_linux/Sourcecode/project` were retained as supporting HPF/FSBL,
boot-mode and generic `DR1M90GEG400` Linux references. The large general FPGA
and SDK archives were not expanded; they are not treated as MLK NPU sources.
The selection and skipped-directory reasons are recorded in
`results/evidence/025/npu_demo_directory_screening.json`.

The Milianke package is substantive rather than a filename-only lead:
`soc_prj.al` declares `DR1M90GEG400`, includes a SoftNPU IP design, supplies an
HPF, candidate bitstream, candidate DTB/BOOT files, an FSBL/platform project,
driver source and an Arm NN/ONNX application archive. Its guide documents an
external Linux SDK flow: export the HPF, create the platform/FSBL projects,
copy the DTS fragments into an external SDK, then build the kernel, rootfs and
image. It does not contain a complete MLK `BoardConfig`, the base
`anlogic-dr1m90.dts`, a Buildroot defconfig, or a scripted BOOT.bin generation
chain.

The package also contains unresolved identity conflicts. `board_cfg.mk` uses
the AD101-labelled `BOARD_DR1X90_AD101_V10` macro; generated IP XML contains
`DR1M90GEG484`/`DR1M90MEG484`; `design_0.info.xml` retains AD103V20 and MLKPAI
source paths; the two packaged bitstream copies have different SHA256 values;
and saved TD logs report `Unknown device name DR1M90GEG400`. These are facts
about the saved package, not proof that it is unusable, but they prevent
claiming a single reproducible MLK-F3P-CZ02 board identity.

The nested `face_detection.tar.gz` is an Arm NN/ONNX path. Its source calls
`libarmnnOnnxParser`, Arm NN `Optimize` with a default `Alnpu,CpuAcc,CpuRef`
preference, `CmaAllocator`/`CmaBuf`, and `EnqueueWorkload`; it does not link a
native `npu_runtime` target or read `rt.bin`/`weight.bin`. The supplied ONNX
model is the application input. The package's `build.sh` hard-codes an
external `/home/uisrc/uisrc-lab-anlogic` tree and a cross-toolchain path, so
its isolated AArch64 link closure is useful evidence but not a complete
deployable rootfs.

The detailed audit, including artifact hashes, device-tree fragments, address
map, package conflicts, direct dependencies and missing files, is in
`results/evidence/025/milianke_npu_demo_audit.json`. Native runtime assets
(`npu_runtime`, `convert_tool`, `al_ai_flow`, `rt.bin`, `weight.bin`) were not
found in the package and remain an independent blocked path.

### Follow-up archive and shared-BSP audit

The bounded archive inventory found 151 archive-like files totalling
4,263,567,836 bytes. `05-5_NPU演示/demo.zip` was listed (1,777 entries) and
selectively analyzed. The two largest potentially relevant FPSoc SDK archives,
`3-2_ex_fpsoc/3_2_01_sdk_base.rar` (900,414,885 bytes) and
`3-2_ex_fpsoc/3_2_02_sdk_adv.rar` (815,163,471 bytes), are RAR v5 files. No
local RAR reader is installed, so they were hashed and recorded but not
expanded; non-authoritative `strings` hints were not used as file listings.
The current `3-4_ex_soc_linux` tree contains no large SDK/project archive in
the directory scan and was audited directly. See
`results/evidence/025/npu_demo_archive_inventory.json`.

The deeper shared-tree audit confirms that `3-4_ex_soc_linux` is a generic
`DR1M90GEG400` Linux/FSBL reference: its `system.al` is TD 6.2.168116, its HPF
declares GEG400, and its boot files are real reference outputs. However its
kernel and U-Boot DTS both include the absent `anlogic-dr1m90.dts`, the
SoftNPU include is commented out in the kernel DTS, and its standalone
`board_cfg.mk` defines `BOARD_DR1X90_AD101_V10`. `3-2_ex_fpsoc/03_boot_mode`
similarly supplies a generic GEG400 HPF/FSBL process and an explicit BIF with
FSBL, generic `fpga_prj.bit` and `hello_world.elf`; it contains no 05-5 NPU
integration. Neither tree is an MLK BoardConfig or a complete Linux
Buildroot/bootgen source chain. Detailed records are in
`npu_mlk_linux_bsp_audit.json`.

The HPF/bitstream audit proves that the 05-5 HPF embeds the platform-copy bit
(`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`), while
the saved best-result bit has a different hash
(`0e7a6311ad7c0cc1b6d9eb228b8e5b74d63b52f598454dd6e4fc922bbced9912`). The
05-5 `BOOT.bin` has no packaged BIF or bootgen source, so its payload cannot be
mapped to either copy. The D21.1 prebuilt image is comparison evidence only;
its DTB strings show HardNPU, SoftNPU and CMA but do not establish MLK
provenance. This is recorded in `npu_hpf_bitstream_provenance.json`.

The pre-injection BoardConfig classification was `ASSET_IDENTITY_CONFLICT`,
not a complete or safely recoverable MLK configuration. The direct 05-5
project is a substantive GEG400 NPU lead, but its AD101/AD103/GEG484 metadata,
missing base DTS, differing bitstream copies and external SDK assumptions
remain provenance limitations. The later PDF-guided injection result is
described below; it generated a partial boot/kernel/module set but not a
complete candidate SD file set.

## Isolated build result

The official `app/npu/build.sh` was run in a copied VM user workspace with
user-local CMake 3.16.9 and Linaro GCC/G++ 7.5.0. CMake configured and linked
the AArch64 Arm NN/OpenCV demo targets, including `yolo_demo_pic`; the target
ELFs and Arm NN libraries are identified by hash in
`npu_sd_build_attempt.json`. The script's packaging phase reported missing
`libprotoc.so`, `libprotoc.so.23` and `libprotoc.so.23.0.0` even though its
final exit status was zero. Therefore this is source/link closure evidence,
not a complete rootfs package or an SD-image build.

Running `build.sh info` from the clean SDK archive stopped at “please select
board config first”. This is expected evidence: the archive has no selected
MLK BoardConfig and its submodule directories are gitlinks without contents.
The full kernel, DTB, Buildroot, FSBL, U-Boot, bootgen and rootfs chain was not
run with an AD101 configuration because doing so would cross the board-identity
boundary.

## Milianke development-package identity increment

The bounded local download search found the exact expected ARM package
`uisrc-lab-anlogicM-V4.0.1.tar.gz` (MD5
`9ba0d5c69e1e127709a3c33958470688`; SHA256
`7214035eea18e0df67a1aaa401ad9d024c4a5560cb5843af50e5f75e9c81d292`). Its
embedded version file identifies `Milianke 4.0.1`, `Anlogic SDK_2025.1` and
`ARM64`. This is a substantial generic DR1M source/toolchain package: it has
Linux, Buildroot, U-Boot and OpenSBI snapshots, an AArch64 Linaro 7.5
toolchain, generic `DR1M` defconfigs, `drcfg.sh`, `make_all.sh` and a
`create_dr1m_image.sh` bootgen flow. It also has source for the three NPU
drivers. The package does not contain an MLK-F3P-CZ02/DR1M90GEG400
BoardConfig, board HPF/bitstream, Arm NN/Alnpu userspace libraries,
`npu_runtime`, `rt.bin`, `weight.bin`, converter, or model assets. The source
trees contain `.git` pointer files but no packaged object database, so they do
not provide exact commit provenance.

The package is therefore classified as
`RECOVERABLE_STRUCTURE_VERSION_MISMATCH`, not as a complete MLK BSP. Its
`SDK_2025.1` identity does not prove that it generated the 05-5 demo's
2025.07/20250905 artifacts. The known `sdk.2025.7.tar.gz` was not re-extracted
or rehashed in this increment; its user-confirmed MD5 is
`a85e6f1f52782a0a9b7e7444d7f8e968` and prior SHA256 is
`c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`. It is
distinct from the expected `anlogic-linuxsdk` download (MD5
`eacb0d2428b9177407e4feeb42747001`), which was not found in the bounded local
scope. The exact expected `uisrc-ubuntu18x64.exe` installer was found and
identified, but not executed. Full package facts and normalized paths are in
`results/evidence/025/uisrc_package_inventory.json`.

The ARM package improves generic source/BSP structure evidence, but it does
not clear `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`, does not make candidate SD
generation ready, and does not authorize any SD write, module load, FPGA
write, or NPU execution. An exact historical Milianke package or board mapping
for the 05-5 2025.07 chain is still required.

## Driver and Device Tree gates

The SDK Kconfig exposes `CONFIG_NPU_MODULE`, `CONFIG_HARD_NPU_DRIVER`,
`CONFIG_SOFT_NPU_DRIVER` and `CONFIG_CMA_MEM_DRIVER`; the prior isolated source
build produced AArch64 modules with text vermagic `6.1.111-rt42 SMP preempt
mod_unload aarch64`. The outputs had no complete `Module.symvers`/symbol-CRC
provenance, so vermagic is not treated as load approval. A candidate DT must
contain matching HardNPU and SoftNPU `compatible`, `reg` and `interrupts`, plus
reserved-memory/CMA. The current eMMC DT and candidate Milianke DT are not
interchangeable evidence.

## Verdict

The current primary automatic result is:

```text
READY_FOR_SD_WRITE_APPROVAL
```

The PDF workflow generated `BOOT.bin`, `system.dtb`, kernel and same-source
NPU modules in an isolated copy, and the Arm NN demo compiled as AArch64. A
141-entry Buildroot 2022.02.6 download cache was then verified and reused with
a file-only network guard to produce a formal rootfs. Static inspection found
353 AArch64 ELF files, zero x86_64 files and no missing DT_NEEDED names. The
Git snapshot's submodule reconstruction remains separately incomplete and the
release tarball provides only partial provenance. OpenCV relocation and actual
board-rootfs use remain unverified. Current eMMC identity is retained from
Task 024 as separate read-only context and is not used as the candidate-SD
identity.

Path summary:

- `current_emmc_identity`: known from Task 024, not a candidate build blocker.
- `candidate_sd_identity`: Milianke DR1M90GEG400 prebuilt lead plus official
  SDK source line; no matched generated file set.
- `candidate_boot_chain_reproducibility`:
  `PASS_BOOT_AND_FORMAL_ROOTFS_FILE_SET_NOT_PARTITIONED`.
- `candidate_kernel_module_compatibility`:
  `PASS_SAME_SOURCE_STATIC_COMPATIBILITY`; `CONFIG_MODVERSIONS`
  is unset in the candidate build, and same-build exported symbol names resolve
  all module imports. This is not runtime load approval.
- `candidate_armnn_runtime_closure`:
  `PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY`.

Task 025 is `Completed` after user approval of the static candidate evidence.
`candidate_approved: true` admits the complete external 13-file set to a
controlled deployment workflow only; it does not authorize formatting,
partitioning or writing real media. `deployment_approval` remains `PENDING`,
`candidate_sd_image` is `NOT_PARTITIONED_IMAGE`, and no physical media or board
state was changed.

### VM historical-environment increment

The approved read-only VM audit found a generic SDK_2025.07 marker tree at
`/home/uisrc/vendor/anlogic/sdk/sdk`. Its generic
`linux/arch/arm64/boot/dts/anlogic/anlogic-dr1m90.dts` and `.dtsi` are present,
but its BoardConfig inventory is AD101/AD102/AD103/AD104 only. The
superproject and referenced submodule object stores are absent, so the tree
does not provide exact commit provenance or an MLK board mapping.

The VM also contains `/home/uisrc/uisrc-lab-anlogic`, which is the already
identified Milianke V4.0.1 / SDK_2025.1 generic tree, not a 2025.07 MLK
package. Its `vendor/anlogic/demos/milianke_npu_demo` archive and tree match the
local `05-5_NPU演示` copy byte-for-byte and by tree digest; the staging log
identifies the local source path. This is copy provenance, not recovery of an
original 2025.07 build workspace. No separate historical uisrc package,
original 05-5 workspace, or MLK BoardConfig was found.

The VM increment predates the PDF-guided reproduction; it left the then-current
source-only result at `BLOCKED_MLK_BOARD_PROJECT_IDENTITY` and candidate SD
generation `NOT_READY`. The latest result is recorded in the next section.
The current eMMC identity remains separate historical context, and no VM
source, vendor script, installer, binary, driver, board or media was modified
or executed.

## PDF-guided injection reproduction (historical PDF-only increment)

The supplied PDF was not readable as a local file in this session; its steps
are recorded as a user-provided workflow summary and checked against the
isolated scripts and named `05-5_NPU演示` inputs. The tutorial selects the
platform copy `soc_base/platform/soc_prj.bit` for
`boards/files/system.bit` (SHA256
`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`), not
the distinct saved best-result bitstream. A fresh copy of
`uisrc-lab-anlogicM-V4.0.1` received the FSBL, bitstream, kernel/U-Boot DTS
fragments, SoftIP DTS and framebuffer sources; the source tree and original VM
package were not modified.

The isolated workflow completed `move_files.sh`, a repaired no-sudo
kernel/DTB/module build, U-Boot, bootgen image creation and the Arm NN
face-detection source build. The resulting `BOOT.bin`, `system.dtb`, kernel,
three modules and compiled AArch64 demo are identified in
`results/evidence/025/npu_pdf_candidate_artifact_validation.json`. The final
kernel has `CONFIG_MODULES=y`, `CONFIG_MODVERSIONS` unset, CMA/DMA-CMA
enabled, HardNPU/SoftNPU/CMA modules enabled, and the framebuffer/VDMA
dependencies resolved in the third isolated repair attempt. Same-build
export-name checks resolved all module imports; this is static evidence, not
permission to load the modules.

The earlier PDF-only pass found an empty Buildroot `dl` cache and retained the
derived rootfs as historical smoke evidence. In the formal follow-up, the
required 141-entry cache was populated through Buildroot's verified HTTPS
source path, rechecked offline, and used with a file-only network guard. The
formal rootfs and a complete external candidate file set were generated. The
candidate is therefore `READY_FOR_SD_WRITE_APPROVAL` without a partitioned SD
image or board runtime claim. `make_parted.sh`, `deploy_image.sh`, all media
operations, board access, module loading, FPGA writes and NPU execution remain
forbidden and were not run. Formal build and closure details are in
`results/evidence/025/npu_buildroot_config_identity.json`,
`npu_buildroot_dl_manifest.json`, `npu_formal_rootfs_build.json`,
`npu_formal_rootfs_runtime_closure.json` and
`npu_final_candidate_artifact_manifest.json`.

## SD-first plan (not executed)

After a version-matched chain is obtained, use an independently identified SD
card and leave eMMC untouched. Hash and archive the current eMMC boot files,
DTB semantics, kernel identity, mounts, CMA and module state before writing.
Hash the candidate partitions after writing, attach serial recovery, verify the
kernel/DTB/FPGA/driver identities before loading anything, and stop on any
hash, vermagic, symbol, DT resource, probe or dmesg mismatch. Only after a
separate human approval may a vendor-approved one-shot be attempted. On any
failure, remove the SD and boot the previously hashed eMMC path; do not
overwrite eMMC automatically. The full plan and stop conditions are in
`results/evidence/025/npu_sd_deployment_plan.json`.
