# Task 025

## Title

MLK-F3P-CZ02 NPU SD image reproducible build and deployment preflight.

## Status

Completed

The current task state is authoritative here and in `TASKS.md`; earlier
`In Progress`/blocked dispositions in the execution record are retained as
historical evidence from before the formal Buildroot increment and user
approval.

## Stage and dependency

Stage 4 NPU SD-image preflight. Depends on Task 024 (`Completed`).

## Recommended branch

`feature/anlogic-npu-sd-image-preflight`

## Goal

Freeze clean, versioned SDK/toolchain and MLK DR1M90GEG400 NPU-project
inputs; reproduce as much of the matched kernel, Device Tree, driver,
Arm NN/demo and SD-boot artifact chain as the available official sources
permit; and stop before any real SD/eMMC write, module load, FPGA write or
NPU execution.

## Scope and invariants

- Target board: `MLK-F3P-CZ02-DR1M90`, device `DR1M90GEG400`, AArch64.
- Target userspace/kernel: Buildroot 2022.02.6, Linux 6.1.111-rt42, glibc
  2.25.
- Candidate workspaces must use clean exact commits/tags or explicitly record
  why a source is not reproducible. Dirty vendor trees are never treated as
  release snapshots.
- AD101V20/AD103V20/GEG484 assets are comparison inputs only unless an
  explicit MLK board mapping is proven.
- Vendor SDKs, modules, libraries, models, bitstreams, DTBs, images, ELF
  files and large logs remain outside Git; Git stores metadata, hashes and
  derived audit evidence only.

## Acceptance criteria

1. Official repository identities, exact source revisions and license status
   are frozen without modifying vendor trees.
2. The MLK board project, HPF, bitstream, Device Tree, SDK, kernel, toolchain,
   driver and Arm NN/demo relationships are mapped with evidence strength.
3. Clean isolated snapshots are used for any attempted build; build commands,
   outputs, hashes and failures are recorded from actual commands.
4. Generated Device Tree and module checks explicitly cover HardNPU, SoftNPU,
   CMA/reserved-memory, compatible/reg/interrupt/status, vermagic, undefined
   symbols, exported symbols and `CONFIG_MODVERSIONS` where available.
5. An SD-first write, verification, serial recovery and rollback plan is
   documented, but no physical medium or board system is changed.
6. A single verdict is selected from the task contract and is consistent with
   the evidence. The task remains `In Progress` until the automated preflight
   is complete; deployment approval is a separate human decision.
7. Offline JSON/YAML, shell, Python, build and repository-hygiene checks pass.

## Allowed files

- `tasks/025_mlk_f3p_cz02_npu_sd_image_preflight.md`
- `TASKS.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`
- `docs/vendor/ANLOGIC_NPU_SD_IMAGE_PREFLIGHT.md`
- `.knowledge/manifests/anlogic_npu_sd_image_preflight.yaml`
- `scripts/vendor/audit_task025_npu_sd_preflight.py`
- `scripts/vendor/audit_task025_demo_archives.py`
- `scripts/vendor/validate_task025_npu_sd_preflight.py`
- `results/evidence/025/*.json`
- Task 025 focused tests

## Forbidden changes

- Do not modify Task 017--024 task files, manifests, evidence, models or
  runtime profiles.
- Do not copy SDKs, modules, libraries, bitstreams, HPFs, DTBs, images,
  models, vendor executables or build directories into Git.
- Do not write an SD card/eMMC, load a module, write FPGA configuration,
  replace a kernel/DTB/rootfs, run a vendor NPU program, or convert the
  project YOLOv5n model.
- Do not use `sudo`, install packages, download dependencies, or alter VM,
  board or vendor repository state.
- Do not commit, push, create a PR, merge, rebase, reset or cherry-pick in
  the automatic phase.

## Execution record

- Start: `2026-08-04` Asia/Shanghai (exact command timestamp to be recorded).
- Branch and starting worktree: recorded before the first mutation.
- Progress, attempted commands, artifacts and skipped steps are appended
  below during this run.

## Final disposition

To be completed only after the automatic preflight. If a required artifact or
source mapping cannot be reproduced, use the exact blocking report in the
repository execution protocol and keep the task `In Progress` or `Blocked`;
never infer a ready SD image from a candidate-only asset.

## Execution record

- `2026-08-04T17:59:17+08:00` WSL baseline: branch
  `feature/anlogic-npu-sd-image-preflight`; `HEAD=02c4aa5`, equal to `dev`;
  only `TASKS.md` and this new task file were changed before the preflight.
- Read-only source freeze used the official SDK release
  `SDK_2025.07-linux6.1` (`beaee2ce45161908403a92619e509f52220ac347`) and
  the Milianke project declaration `DR1M90GEG400`. The source archive hash and
  all selected repository/candidate hashes are in
  `results/evidence/025/npu_sd_source_inventory.json`.
- The clean WSL SDK archive contains empty submodule directories representing
  gitlinks. `bash ./build.sh info` was run against that snapshot and stopped
  with exit 1 at `please select board config first`; no output or vendor tree
  was changed.
- The first VM app attempt exposed two packaging/environment defects: the
  script could not find a system `cmake` and the copied workspace did not have
  the script's expected `aarch64-linux` toolchain path. A second isolated copy
  was discarded from consideration after the copy layout made `build.sh`
  unavailable. The final repair attempt used a fresh isolated copy,
  user-local CMake 3.16.9, and a read-only symlink to the verified Linaro
  toolchain; it configured and linked all AArch64 Arm NN demo targets.
- The final app build produced `yolo_demo_pic` and other AArch64 targets, but
  the vendor packaging phase reported missing `libprotoc.so`,
  `libprotoc.so.23`, and `libprotoc.so.23.0.0` while incorrectly returning
  zero. This is recorded as partial source/link closure, not a complete
  rootfs package. All build outputs remain in the VM user workspace outside
  Git and no target was executed.
- Full kernel/DTB/Buildroot/FSBL/U-Boot/bootgen/rootfs construction was not
  attempted with an AD101 BoardConfig: the official SDK has no MLK BoardConfig,
  and using an AD101 configuration would violate the board-identity boundary.
  The native runtime/converter path was not attempted because
  `npu_runtime`, `convert_tool`, `al_ai_flow`, `rt.bin`, and `weight.bin` are
  unavailable in the approved local scope.
- No SD card, eMMC, FPGA, Device Tree, kernel, rootfs, module or board system
  was changed. No module was loaded and no vendor NPU executable was run.

- `2026-08-04T18:51:46+08:00` focused closure update: an exact detached clone
  of `SDK_2025.07-linux6.1` was created in `/tmp/task025-preflight/` at
  `beaee2ce45161908403a92619e509f52220ac347`. Checkout and submodule sync
  passed; recursive submodule materialization failed because the local
  relative submodule repositories were unavailable without network access.
- `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz` was hashed
  (`c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`,
  1,368,135,226 bytes) and extracted into an isolated VM workspace. It is a
  fuller source payload, but contains no `.git` metadata and therefore only
  partial exact submodule provenance.
- The release tarball contains AD101/AD103 BoardConfig files and no
  MLK-F3P-CZ02 BoardConfig. The Milianke DR1M90GEG400 project remains the
  strongest board-level lead, but it supplies prebuilt FPGA/HPF/boot
  candidates rather than a matched Linux SDK BoardConfig/build entry.
- Recursive read-only `readelf` analysis of the isolated Arm NN package found
  no missing non-system `DT_NEEDED` library. `libprotoc.so*` is reported by the
  packaging script but is not `DT_NEEDED` by `yolo_demo_pic`, Arm NN,
  `libarmnnOnnxParser` or `libprotobuf`; it is recorded as a packaging-only
  defect. OpenCV objects retain an absolute build RPATH, so deployment
  relocation remains unverified.
- The candidate source/config cannot yet produce a same-source kernel, DTB and
  three-module set because the MLK BoardConfig and exact board build mapping
  are absent. The generic release defconfig enables modules and CMA but does
  not select the NPU driver symbols. `CONFIG_MODVERSIONS` is not enabled in
  the inspected defconfig; missing `__versions` is therefore not by itself a
  candidate blocker, but no candidate same-source module compatibility proof
  exists.
- Current eMMC identity remains a read-only Task 024 reference and is not used
  as the candidate-SD build identity. Native `npu_runtime` assets remain an
  independent blocked path and do not invalidate the Arm NN static closure.

## Historical automatic disposition before the formal Buildroot increment

- `status`: historical `In Progress`.
- `automated_preflight`: historical `COMPLETE`; this disposition predates the
  formal Buildroot rootfs and complete candidate-file-set increment below.
- Primary verdict: `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`.
- Candidate path status: `candidate_boot_chain_reproducibility` is blocked by
  the absent MLK BoardConfig and board-source mapping;
  `candidate_kernel_module_compatibility` is blocked because a same-source
  candidate kernel/config/module set was not established;
  `candidate_armnn_runtime_closure` is
  `PASS_STATIC_CLOSURE_NOT_DEPLOYMENT_READY`.
- Secondary blockers: clean Git submodule reconstruction, boot-asset
  generation, module symbol provenance, Arm NN relocation/deployment closure,
  missing native runtime assets, package release identity and
  provenance/license gaps. Current-eMMC active bitstream/DT identity is
  retained only as Task 024 context and is not the candidate-SD core blocker.
- No generated SD image or complete matched SD file set exists. The Milianke
  BOOT/DTB/HPF/bitstream files remain external candidate references only.
- The documented SD-first backup/write/serial-recovery/rollback plan is
  preparatory only; physical write approval is not requested in this task
  record.

## Offline validation record

- Task 025 validator: `PASS` with primary
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`.
- Task 025 focused tests: `3/3 PASS`; complete repository Python suite:
  `124 PASS`.
- Existing model-independent Release build: `PASS` (no work required);
  CTest: `14/14 PASS`.
- JSON/YAML parsing, Python compilation, Bash syntax, sensitive-material scan,
  changed-file size/repository hygiene and `git diff --check`: `PASS`.
- Task 017--024 immutability check: `PASS`; no earlier task file or evidence
  was modified. No vendor SDK, library, module, bitstream, image, model or
  ELF was added to Git.
- Final offline rerun at `2026-08-04T19:02:04+08:00`: Task 025 validator
  `PASS`; focused tests `3/3 PASS`; full Python suite `125 PASS`; existing
  Release build required no work; CTest `14/14 PASS`; JSON/YAML parsing,
  Python compilation, Markdown local-link checking, Task 017--024
  immutability, changed-file sensitive-material scan, repository hygiene and
  `git diff --check` all passed. The broad repository scan still contains
  pre-existing redaction-pattern strings in older scripts; the changed-file
  scan passed and no Task 025 sensitive material was found.

- `2026-08-05T11:59:27+08:00` bounded `03_demo` screening classified the
  top-level directories A/B/C/D without copying vendor material. The direct
  target `05-5_NPU演示` was deep-audited; generic FPSoc and Linux trees were
  used only as supporting process references. The selected-directory inventory
  and skip reasons are in
  `results/evidence/025/npu_demo_directory_screening.json`.
- `2026-08-05T11:59:27+08:00` deep `05-5_NPU演示` audit found a real
  Milianke DR1M90GEG400-declared TD project, HPF, SoftNPU IP metadata,
  candidate bitstream/BOOT/DTB files, FSBL/platform sources, Linux driver
  sources and an Arm NN/ONNX demo package. The checked assets are
  byte-identical to the duplicate under `NPU_info`; this establishes package
  provenance only.
- The same audit found unresolved board/source conflicts: the software board
  macro is `BOARD_DR1X90_AD101_V10`, generated IP metadata includes
  DR1M90GEG484/DR1M90MEG484, saved design paths include AD103V20/MLKPAI, the
  base `anlogic-dr1m90.dts` is absent, the platform bitstream hash differs
  from the best-result bitstream hash, and saved TD logs contain
  `Unknown device name DR1M90GEG400`. These facts strengthen the direct lead
  but do not close MLK-F3P-CZ02 identity.
- The nested `face_detection` package is statically confirmed as the Arm
  NN/ONNX route: it uses `libarmnnOnnxParser`, `Optimize` with Alnpu/CpuAcc/
  CpuRef preferences, CMA allocators and an ONNX input. It does not use a
  native `npu_runtime` target or `rt.bin`/`weight.bin`; the package build
  script depends on an external SDK tree. Detailed results are in
  `results/evidence/025/milianke_npu_demo_audit.json`.
- No vendor script, ELF, kernel module or NPU program was executed. No VM,
  board, SD/eMMC, FPGA, Device Tree or vendor source was modified.

## Incremental 03_demo disposition

- `mlk_board_project_identity`: `PARTIAL_DIRECT_LEAD_NOT_CLOSED`.
- `mlk_board_config`: `NOT_FOUND`.
- `candidate_boot_chain_reproducibility`:
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`.
- `candidate_kernel_module_buildability`:
  `BLOCKED_CANDIDATE_KERNEL_MODULE_BUILD`.
- `armnn_deployment_package`:
  `PASS_STATIC_SOURCE_LINK_CLOSURE_NOT_DEPLOYMENT_READY`.
- `native_runtime_asset_availability`: `BLOCKED_NATIVE_RUNTIME_ASSETS`.
- `candidate_sd_generation_readiness`: `NOT_READY`.

The primary Task 025 verdict remains `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`.
Additional evidence records `BLOCKED_ASSET_VERSION_MISMATCH` and
`BLOCKED_BOOT_CHAIN_SOURCE_MISSING` as secondary conditions. The package is
not promoted to a reproducible MLK SD source and no SD-write approval is
requested.

- `2026-08-05T12:10:46+08:00` offline revalidation incorporated the bounded
  `03_demo` screening and `05-5_NPU演示` deep-audit evidence. The Task 025
  validator passed all nine required evidence documents; the focused suite
  passed 4/4, the complete Python suite passed 126 tests, Release/CTest passed
  (14/14), and JSON/YAML, Python/Bash syntax, Markdown links, prior-task
  immutability, sensitive-material/repository hygiene and `git diff --check`
  passed. No VM, board, vendor binary, driver, storage media or NPU program
  was accessed or executed.

- `2026-08-05T16:01:43+08:00` follow-up archive audit was performed from the
  WSL copy of `03_demo` without modifying the source tree. The snapshot
  contains 151 archive-like files totaling 4,263,567,836 bytes. The direct
  `05-5_NPU演示/demo.zip` was listed at 1,777 entries and the nested
  `face_detection.tar.gz` was already statically audited. The two high-value
  FPSoc SDK RAR v5 archives were hashed and recorded, but no local RAR reader
  exists; no contents were inferred from `strings` hints and no extraction was
  attempted. The current 3-4 tree contains no large SDK/project archive in the
  directory scan and was audited directly. Reproducible inventory metadata is
  in `results/evidence/025/npu_demo_archive_inventory.json`, generated by
  `scripts/vendor/audit_task025_demo_archives.py`.

- `2026-08-05T16:01:43+08:00` deep supporting-tree audit confirmed that
  `3-4_ex_soc_linux` is a generic GEG400 Linux/FSBL reference with an
  AD101-labelled `board_cfg.mk`, a missing `anlogic-dr1m90.dts` base include,
  and no MLK BoardConfig, Buildroot defconfig or scripted BOOT.bin entry.
  `3-2_ex_fpsoc/03_boot_mode` provides a generic GEG400 HPF/FSBL/BIF chain
  (`FSBL.elf`, `fpga_prj.bit`, `hello_world.elf`) but no 05-5 NPU integration.
  These trees improve process context but do not make a recoverable MLK BSP.

- `2026-08-05T16:01:43+08:00` HPF provenance comparison established that the
  05-5 HPF embeds the platform-copy bit (`e40536cd...483b57fb5`) while the
  saved best-result bit is different (`0e7a6311...bbced9912`). The 05-5
  `BOOT.bin` has no packaged BIF/bootgen source, so its payload mapping remains
  unresolved. The follow-up BoardConfig classification is
  `ASSET_IDENTITY_CONFLICT`; primary verdict remains
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY` and candidate SD generation is not
  ready. New evidence is in `npu_mlk_linux_bsp_audit.json`,
  `npu_hpf_bitstream_provenance.json` and
  `npu_boardconfig_recovery_assessment.json`.

- `2026-08-05T17:12:57+08:00` WSL-only package identity increment located the
  exact expected ARM Milianke package
  `uisrc-lab-anlogicM-V4.0.1.tar.gz` (MD5
  `9ba0d5c69e1e127709a3c33958470688`, SHA256
  `7214035eea18e0df67a1aaa401ad9d024c4a5560cb5843af50e5f75e9c81d292`).
  Its version file says `milianke version: 4.0.1`, `Anlogic version:
  SDK_2025.1`, and `build target: ARM64`. The package contains generic DR1M
  source trees, an AArch64 GCC 7.5 toolchain, NPU driver source and generic
  image scripts, but no MLK-F3P-CZ02/GEG400 BoardConfig, board HPF/bitstream,
  Arm NN userspace package, native runtime assets or model files. Its generic
  `drcfg.sh`/`create_dr1m_image.sh` flow is structural evidence only and does
  not close the MLK board identity or the 2025.07 NPU-demo provenance.
- The separate V4.0.1 package was recorded as a non-matching RISC-V/V-series
  comparison asset (MD5 `47b41afa3ccae35df0b72be32bce1604`). The expected
  `uisrc-ubuntu18x64` installer was found with its exact MD5
  `a07728013c0d117e3793c8d1ad4d4fd2`; it was not executed. No local file
  matching the expected `anlogic-linuxsdk` MD5
  `eacb0d2428b9177407e4feeb42747001` was found in the bounded vendor scope.
  The known `sdk.2025.7.tar.gz` identity (MD5
  `a85e6f1f52782a0a9b7e7444d7f8e968`, SHA256
  `c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`) was
  reused without re-extraction or rehashing and remains distinct from the
  expected `anlogic-linuxsdk` download.
- This increment classifies the ARM package as
  `RECOVERABLE_STRUCTURE_VERSION_MISMATCH`, not as a complete MLK package.
  It improves generic BSP/source availability but leaves the primary verdict
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`, candidate SD generation `NOT_READY`,
  and any physical SD-write approval unavailable. The complete package
  identity and bounded-search results are in
  `results/evidence/025/uisrc_package_inventory.json`. No VM, board, vendor
  script, installer, binary, module, storage medium or NPU program was
  accessed or executed.

## Latest offline validation record

- `2026-08-05T17:12:57+08:00` package identity evidence was parsed and the
  Task 025 validator passed 14 evidence files with the primary
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY` verdict. The focused Task 025 suite
  passed 6/6 and the complete Python suite passed 128 tests. JSON/YAML parsing,
  Python compilation, Bash syntax for shell files, Markdown local-link
  checking, Task 017--024 immutability, changed-file sensitive-material scan
  and `git diff --check` passed. A first ad-hoc validation invocation passed
  Python files to `bash -n` and produced the expected syntax error; it was
  corrected by running `bash -n` only over shell files, which passed. No VM,
  board, network, installer, vendor binary or physical medium was accessed.

- `2026-08-05T17:34:41+08:00` read-only VM increment: the Ubuntu 18.04.4
  x86_64 VM was reachable through the approved wrapper. It contains a generic
  SDK_2025.07 marker tree at `/home/uisrc/vendor/anlogic/sdk/sdk`, including
  generic `anlogic-dr1m90.dts`/`.dtsi` files, but only AD-series BoardConfigs;
  the SDK superproject and submodule object stores are absent. The installed
  `/home/uisrc/uisrc-lab-anlogic` tree is the generic Milianke V4.0.1 /
  SDK_2025.1 package already recorded in the local evidence. No separate
  historical 2025.07 uisrc package, MLK BoardConfig, or original 05-5
  workspace was found in the bounded VM scope.
- The VM's `milianke_npu_demo` archive and tree are byte/tree-identical to the
  local 05-5 copy, as recorded by the VM staging log; this establishes copy
  provenance, not an independently retained historical build workspace. The
  VM increment therefore improves generic source context but does not close
  the MLK board mapping or candidate boot-chain reproducibility.
- No VM file was modified and no vendor script, installer, build, ELF, driver
  or NPU demo was executed. Task 025 remains `In Progress`, the primary
  verdict remains `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`, and candidate SD
  generation remains `NOT_READY`.

- `2026-08-05T18:36:25+08:00` PDF-guided injection increment: the supplied PDF
  itself was not readable at `/mnt/data` in this session, so its workflow was
  recorded as user-summary evidence rather than fabricated page extraction.
  The named 05-5 inputs were independently located and hashed. The tutorial's
  `soc_prj.bit` platform copy is
  `e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`, while
  the saved best-result bit differs
  (`0e7a6311ad7c0cc1b6d9eb228b8e5b74d63b52f598454dd6e4fc922bbced9912`); only
  the platform copy was injected as `system.bit`.
- A fresh VM copy of `uisrc-lab-anlogicM-V4.0.1` was used exclusively at
  `<vm-task025>/uisrc-lab-anlogic-pdf-20260805`. `move_files.sh` completed
  successfully. The unmodified `make_kernel.sh` and `make_rootfs.sh` were not
  run because they invoke `sudo`/potential downloads; equivalent no-sudo
  kernel and module build commands were used, and the rootfs was staged only
  from the existing generic archive plus the isolated overlay.
- Kernel repair attempts were recorded in order: missing base DTS, unresolved
  framebuffer/VDMA symbols, two unresolved `VIDEOMODE_HELPERS` link attempts,
  then an isolated Kconfig `select VIDEOMODE_HELPERS` repair. The final
  `6.1.111-rt42` build passed and produced an AArch64 Image, DTB, System.map,
  Module.symvers and `hard_npu.ko`, `soft_npu.ko`, `cma_mem.ko`.
- The isolated U-Boot `anlogic_dr1_uboot_defconfig`/`DEVICE_TREE=anlogic-dr1`
  build passed. `create_dr1m_image.sh` then passed with the injected FSBL,
  platform bitstream and U-Boot and generated an isolated `BOOT.bin`, boot.scr,
  uImage and system.dtb. No physical media or board was touched.
- The PDF face-detection source was compiled in a second isolated copy after
  moving its stale packaged CMake cache aside; the AArch64
  `yolo_demo_hdmi_camera` target and install tree passed. The resulting Arm
  NN/ONNX files were injected into an isolated rootfs staging tree together
  with the same-source kernel modules. The derived rootfs tar/cpio/initrd is
  not a Buildroot output: the local Buildroot `dl` cache contains zero files,
  so `make_rootfs.sh` was deliberately not run and no network fetch was
  attempted.
- Candidate artifact hashes, DTB semantics, module export-name checks and the
  full-candidate-rootfs static DT_NEEDED closure are recorded in
  `npu_pdf_candidate_artifact_validation.json`. The kernel/DTB/module and boot
  portions are now statically reproducible within the injected workspace, but
  the overall candidate remains `BLOCKED_CANDIDATE_IMAGE_BUILD` because a
  clean Buildroot rootfs was not generated. Task 025 remains `In Progress`;
  SD-write approval is not requested.

## Historical PDF-only disposition before formal Buildroot increment

- `candidate_boot_chain_reproducibility`:
  `PASS_BOOT_GENERATED_FROM_PDF_INJECTED_INPUTS_NOT_FULL_SD`.
- `candidate_kernel_module_compatibility`:
  `PASS_SAME_SOURCE_STATIC_BUILD_NOT_DEPLOYMENT_READY`.
- `candidate_armnn_runtime_closure`:
  `PASS_STATIC_CLOSURE_NOT_DEPLOYMENT_READY`.
- `candidate_sd_generation_readiness`:
  `READY_FOR_SD_WRITE_APPROVAL`; the formal Buildroot rootfs and complete
  external candidate file set are static-validated, but no partitioned image
  has been written or booted.
- Primary verdict is `READY_FOR_SD_WRITE_APPROVAL`; Task 025 remains
  `In Progress`, `candidate_approved=false`, and `SD write=NOT_PERFORMED`.
  `make_parted.sh`, `deploy_image.sh`, module loading, FPGA writes, board
  access and NPU execution were not performed.

## Historical offline validation after PDF increment and before formal rootfs

- `2026-08-05T18:52:50+08:00` WSL-only validation: the Task 025 validator
  passed 22 required evidence files with primary
  `BLOCKED_CANDIDATE_IMAGE_BUILD`; focused tests passed 8/8 and the complete
  Python suite passed 130 tests. JSON/YAML parsing, Python compilation, Bash
  syntax, Markdown local-link checking, Task 017--024 immutability,
  changed-file sensitive-material/repository hygiene and `git diff --check`
  all passed. The existing model-independent Release build required no work;
  CTest passed 14/14. Task 022/023/024 validators and the Task 019 runtime
  profile validator also passed.
- No further VM, board, network, media, driver, vendor binary or NPU access
  was performed during this offline validation pass. No commit was created.

## Formal Buildroot rootfs increment

- `2026-08-06T11:19:05+08:00` through `2026-08-06T11:59:31+08:00` VM
  isolated build: the frozen Buildroot `2022.02.6` configuration and
  Linaro AArch64/glibc 2.25 toolchain were recorded in
  `npu_buildroot_config_identity.json`. The controlled `make source` download
  used `https://sources.buildroot.net` with Buildroot hash verification and
  produced 70 archives plus 70 lock files and one local source entry (141
  entries, 268,798,198 bytes). A second `make source` run with a file-only
  primary site completed with zero new download requests.
- The formal Buildroot command was run in the isolated VM output directory
  with `BR2_PRIMARY_SITE=file:///__task025_no_network__`, primary-site-only
  mode and an empty backup site. It exited 0 at `2026-08-06T11:59:31+08:00`.
  The generated `rootfs.tar.gz` SHA256 is
  `ae64bbd125a47f54df445a084485466336f1df60f5137ad61b44b8eb22c64f39`,
  `rootfs.cpio.lz4` is
  `1fdfd264d49e4d7cdc95d68952e9b332525efb493917fdbdbbc26e0de914848a`,
  and the generated `uInitrd.lz4` is
  `c736bb9af24e644407ee0ee467c37f771f07b314b779879ac203d02b28159268`.
- Static extraction found 353 AArch64 ELF files, zero x86_64 files, the
  AArch64 dynamic loader and 78 DT_NEEDED names with no missing names. The
  formal rootfs contains the same-source NPU modules under
  `lib/modules/6.1.111-rt42/extra`, the Arm NN/ONNX application, model and
  required libraries. No AArch64 target was executed.
- The external candidate fileset contains 13 hashed entries, including the
  previously generated BOOT/kernel/DTB/module artifacts and the formal rootfs
  outputs. Its checksum manifest SHA256 is
  `65e4d98db58e20c407b7e65e443bfe1774b692ccb49a0fd1b6f7062ebcf73ddd`.
  No partitioned SD image was generated and no SD/eMMC/board operation was
  performed. Evidence is in the five new `results/evidence/025/` Buildroot and
  candidate-manifest files.

## Current automatic disposition after formal rootfs build

- `mlk_documented_workflow`: `PASS_REPRODUCED`.
- `candidate_boot_chain`: `PASS_BOOT_AND_FORMAL_ROOTFS_FILE_SET_NOT_PARTITIONED`.
- `candidate_dtb`: `PASS_STATIC_VALIDATION`.
- `candidate_kernel_modules`: `PASS_SAME_SOURCE_STATIC_COMPATIBILITY`.
- `candidate_formal_rootfs`: `PASS_FORMAL_BUILDROOT_ROOTFS`.
- `candidate_armnn_runtime_closure`:
  `PASS_STATIC_FORMAL_ROOTFS_CLOSURE_NOT_DEPLOYMENT_READY`.
- `candidate_sd_generation`: `READY_FOR_SD_WRITE_APPROVAL`.
- Primary verdict is `READY_FOR_SD_WRITE_APPROVAL`; Task 025 is now
  `Completed` after the user approved the static candidate evidence. The
  approval covers the 13-file candidate set only; it does not authorize
  formatting, partitioning or writing real media. The current eMMC, board
  boot, driver probe, NPU runtime and project-model conversion remain
  untested.

## Latest WSL-only validation after formal rootfs evidence

- `2026-08-06T12:23:09+08:00`: the Task 025 validator passed 27 evidence
  documents with primary `READY_FOR_SD_WRITE_APPROVAL`. The focused suite
  passed 9/9 and the complete Python suite passed 131 tests. JSON/YAML parsing,
  Python compilation, Bash syntax, Markdown local-link checking,
  Task 017--024 immutability, changed-file sensitive-material/repository
  hygiene and `git diff --check` passed.
- The model-independent Release build required no work and CTest passed 14/14.
  Task 022, Task 023, Task 024 and Task 019 validators passed. No VM, board,
  network, storage medium, module, vendor binary or NPU program was accessed
  during this WSL-only validation pass. At that capture time no commit had
  yet been created; the final local commit is created by the completion record
  below.
- One initial focused-test invocation incorrectly supplied the Python module
  name with a `.py` suffix and failed with the standard unittest
  `AttributeError`; the corrected module invocation immediately passed 9/9.
  This was a command spelling error, not a test or evidence failure.

## Final approval and completion record

- Task 025 final state: `Completed`.
- `primary_verdict`: `READY_FOR_SD_WRITE_APPROVAL`.
- `candidate_approved`: `true`; this records user approval for the static
  13-file candidate set to enter a controlled SD deployment workflow only.
- `deployment_approval`: `PENDING`; `sd_write`: `NOT_PERFORMED`;
  `candidate_sd_image`: `NOT_PARTITIONED_IMAGE`.
- No partitioning, formatting, SD/eMMC write, board access, module load,
  FPGA write or NPU execution was performed. The next action is Task 026's
  device-identification and dry-run gate, which must stop before any write
  until the user explicitly approves a target medium.
- The final external checksum manifest contains 13 entries and has SHA256
  `65e4d98db58e20c407b7e65e443bfe1774b692ccb49a0fd1b6f7062ebcf73ddd`.
