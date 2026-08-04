# Task 024

## Title

MLK-F3P-CZ02 NPU board mapping and controlled deployment plan.

## Status

Completed

## Stage and dependency

Stage 4 NPU board mapping. Depends on Task 023 (`Completed`).

## Goal

Identify the last-known boot chain and hardware description for the
`MLK-F3P-CZ02-DR1M90` board, compare it with the supplied official NPU
projects, and prepare a reversible, separately approved first deployment plan.
This task stops before loading a module, writing a bitstream or Device Tree,
flashing media, or running an NPU program.

## Target and invariants

- Board: `MLK-F3P-CZ02-DR1M90`, AArch64, Buildroot 2022.02.6,
  Linux 6.1.111-rt42, glibc 2.25.
- Preserve Tasks 017--023 and all frozen CPU/ncnn/YOLO evidence.
- Vendor binaries, modules, HPFs, bitstreams, DTBs, SDKs, images, models and
  board logs remain outside Git; this task stores metadata, hashes and derived
  observations only.
- Every statement is classified as a document fact, source-code fact,
  engineering inference, or real-device observation.

## Acceptance criteria

1. The current-read boot medium/partition, root, kernel and boot-file
   identities are recorded without presenting an opaque BOOT.bin artifact as
   an identified NPU image.
2. Historical Device Tree and CMA/NPU observations are compared with the
   candidate DR1M90GEG400 and other example assets.
3. Kernel source, defconfig, compiler and Module.symvers provenance are
   separated from the board's observed ABI; vermagic alone is not treated as
   loadability proof.
4. The MLK-F3P-CZ02, DR1M90GEG400, AD101V20, AD103V20 and GEG484 examples
   have an explicit mapping matrix and unresolved conflicts.
5. A read-only, SD-first backup/rollback and preflight plan is documented.
6. The board mapping verdict is consistent with the evidence. The audit is
   complete with primary verdict `BLOCKED_ACTIVE_BITSTREAM_IDENTITY`; current
   eMMC NPU readiness and controlled deployment remain blocked.
7. Offline JSON/YAML, shell, Python, repository-hygiene and immutability
   checks pass.

## Allowed files

- `tasks/024_mlk_f3p_cz02_npu_board_mapping.md`
- `TASKS.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`
- `docs/vendor/ANLOGIC_NPU_BOARD_MAPPING_AND_CONTROLLED_DEPLOYMENT.md`
- `.knowledge/manifests/anlogic_npu_board_mapping.yaml`
- `scripts/arm/audit_anlogic_npu_board_mapping.sh`
- `scripts/vendor/validate_task024_npu_mapping.py`
- `results/evidence/024/*.json`
- Task 024 focused tests

## Forbidden changes

- Do not modify Task 017--023 task files, manifests, evidence, models, or
  runtime profiles.
- Do not load `.ko` files, run vendor NPU ELFs, write an FPGA bitstream,
  replace a DTB/kernel/rootfs, flash SD/eMMC, or change boot arguments.
- Do not use `sudo`, install packages, download vendor assets, or modify the
  VM/board system.
- Do not push, create a PR, merge, rebase, reset, or cherry-pick. One local
  atomic Task 024 commit is permitted after all checks pass.

## Evidence classification

`results/evidence/024/*.json` labels observations as `document_fact`,
`source_code_fact`, `engineering_inference`, or `real_device_observation`.
Current board file hashes and Device Tree semantics are promoted only from the
successful read-only board collection. Candidate project assets remain
candidate-only unless their hash and source mapping match the active files.

## Execution record

- Started: `2026-08-04T15:58:34+08:00` Asia/Shanghai.
- Branch: `feature/anlogic-npu-board-mapping`.
- Starting worktree: clean; no Task 024 commit exists.
- Local vendor and read-only AlWiki sources were used. The VM read-only probe
  succeeded and confirmed Ubuntu 18.04.4/x86_64, user-local CMake 3.16.9,
  Linaro GCC 7.5.0, and SDK kernel Makefile 6.1.111 with no source-tree
  `Module.symvers`.
- A fresh read-only `/home/dministrator/bin/anlogic-board-ssh` collection was
  restored and completed. It captured current boot files, `/proc/device-tree`,
  FPGA-manager state, CMA, modules, devices and dmesg. No write operation was
  performed.
- The four local official repositories were inventoried read-only. Their
  remotes, HEAD/tag/branch, dirty counts, submodule SHAs and license status
  are in `official_repository_inventory.json`; all materialized trees are
  dirty and therefore not pristine release snapshots.

### Current boot and board facts

The current read records `root=/dev/mmcblk1p2`, `/dev/mmcblk1p1` as the vfat
boot partition, Buildroot 2022.02.6, Linux 6.1.111-rt42, AArch64, and glibc
2.25. The hardware manual identifies eMMC and TF media; calling `mmcblk1`
eMMC remains a qualified engineering inference because the U-Boot environment
was not exposed.

The current boot files are `/mnt/mmcblk1p1/BOOT.bin`, `boot.scr`,
`system.dtb` and `uImage.lz4`; their current hashes are recorded in
`board_boot_chain.json` and `active_boot_static_parse.json`. `boot.scr` loads
the kernel and DTB from the same partition. The current BOOT.bin contains
ALGC/Release 5.9.1 Build 151508 and `board=evb_dr1m90` markers, but its FPGA
payload remains opaque and no bitstream name/hash was recovered.

The current read-only Device Tree parse found a hard-NPU platform node with
compatible `anlogic,hard_npu`, registers at `0x63f00000/0x100000`,
`0xf8800000/0x200` and `0xf8801000/0x100`, SPI112, and a 128 MiB default CMA
pool. The FPGA manager is operating, but no hard_npu driver is bound, no
soft-NPU node is present, no NPU/CMA module is loaded and the expected device
nodes are absent. These facts show an incomplete runtime substrate, not a
permanent statement about DR1M90 capability.

### Blocking report and resume

Primary verdict: `BLOCKED_ACTIVE_BITSTREAM_IDENTITY`.

Secondary blockers: `BLOCKED_ACTIVE_BITSTREAM_SOURCE_MAPPING`,
`BLOCKED_ACTIVE_DTB_SOURCE_MAPPING`, `BLOCKED_KERNEL_SYMBOL_PROVENANCE`,
`BLOCKED_SAFE_ROLLBACK_PLAN`, `CANDIDATE_ASSET_NOT_ACTIVE`,
`MLK_TO_OFFICIAL_SDK_MAPPING_PARTIAL`, and `OFFICIAL_REPOSITORY_TREES_DIRTY`.

The board route is restored for read-only collection. The next safe resume
step is to obtain the missing active payload/source and rollback evidence:

```text
/home/dministrator/bin/anlogic-board-ssh 'uname -a; cat /proc/cmdline; mount; find /sys/firmware -maxdepth 3 -type f -print'
```

Then capture the actual boot partition, active DTB/boot script, FPGA/firmware
identity, `/proc/device-tree`, `dmesg`, kernel config and module symbol data.
No deployment action is implied by this resume command.

## Commands run

- `git branch --show-current`, `git status --short --untracked-files=all`,
  `git log --oneline`.
- Read-only VM identity/toolchain/source probe through
  `/home/dministrator/bin/anlogic-vm-ssh`.
- Read-only board collection through `/home/dministrator/bin/anlogic-board-ssh`;
  it returned current boot, DT, FPGA-manager, CMA, module and dmesg evidence.
- Read-only inventory of the official `dr1m90_npu`, `toolchains`, `boardimages`
  and `sdk` repositories, including tag/HEAD/submodule/license metadata.
- Static ALGC/BOOT.bin parsing, VM `dtc` DTB decompilation, and comparison with
  Milianke, D21.1 and 20.Lock candidate assets.
- SDK defconfig/Kconfig and isolated module symbol audit; no module was loaded.
- Existing local Task 022/023 evidence, board-runtime manifests, hardware
  manuals, NPU demo PDF, candidate DTS/DTB/HPF/bitstream metadata and the
  official AlWiki knowledge records were reviewed.
- `bash -n` and the Task 024 validator are run after the evidence update.
- Offline JSON/YAML parsing passed; Task 024 focused tests passed (4 tests),
  full Python tests passed (122 tests), the existing Release build was clean,
  CTest passed 14/14, Markdown/link checks passed, sensitive-material and
  repository-hygiene scans passed, `git diff --check` passed, and Task
  017--023 immutability passed. These results are summarized in
  `results/evidence/024/validation.json`.

## Commands not run

No `insmod`, `modprobe`, vendor ELF, NPU demo, model conversion, bitstream
write, DTB/kernel/rootfs replacement, SD/eMMC write, or board system change
was run. No VM system change was made. No Task 017--023 evidence was rewritten.
No commit was created before finalization; the local Task 024 commit is created
only after the final offline checks below.

## Current disposition

Task 024 is `Completed` as an approved audit. The candidate Milianke NPU project targets
`DR1M90GEG400` and is a useful board-level lead, but it is not evidence of the
currently active FPGA payload/source. Active boot-file and DTB hashes are now
read-confirmed, while source/bitstream mapping, active kernel symbol
provenance, and a rollback-ready external backup remain open. Deployment
approval remains blocked and was not granted. The current eMMC is not ready for
complete NPU execution. `candidate_approved: true` means only that this audit
result is approved for repository entry; it does not authorize SD writes,
module loading or NPU execution.

## Final status

- Task 024 audit: `Completed`.
- Primary verdict: `BLOCKED_ACTIVE_BITSTREAM_IDENTITY`.
- Current eMMC NPU readiness: `Not ready`.
- Controlled deployment: `Not approved`.
- SD-first strategy: `Recommended` (not executed).
- Candidate approval: `true` (audit approval only).
- Next proposed task: `Task 025: MLK-F3P-CZ02 NPU SD image reproducible build and deployment preflight`.
