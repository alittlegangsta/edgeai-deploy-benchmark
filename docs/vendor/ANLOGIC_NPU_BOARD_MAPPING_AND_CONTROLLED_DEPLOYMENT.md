# Anlogic NPU board mapping and controlled deployment plan

This document records Task 024's read-only mapping work for
`MLK-F3P-CZ02-DR1M90`. It is a deployment gate, not approval to load a
driver, configure the FPGA, or run a vendor NPU program.

## Evidence vocabulary

- **Document fact**: stated by the approved hardware manual, NPU guide, or
  official Wiki record.
- **Source-code fact**: observed in the supplied SDK/demo source or a matching
  local source snapshot.
- **Engineering inference**: derived from several facts and explicitly marked
  as such.
- **Real-device observation**: captured by a reproducible board command. The
  latest Task 024 read-only probe reached the board and captured current boot
  files, Device Tree semantics, FPGA-manager state, CMA and module/device
  state. It did not write or execute anything.

## Current boot chain

The current read records `root=/dev/mmcblk1p2` and a vfat
`/dev/mmcblk1p1` boot partition, with Buildroot 2022.02.6, Linux 6.1.111-rt42,
AArch64 and glibc 2.25. The hardware manual identifies both eMMC and TF boot
media. Therefore `mmcblk1` is recorded as **likely eMMC (engineering
inference)** because the U-Boot environment is not exposed. Current hashes are
`BOOT.bin` `858cf78c...980706`, `boot.scr` `685f9f8c...ad59d1`,
`system.dtb` `aba027ea...0d646f`, and `uImage.lz4`
`12cd2ccb...bd7be`; the complete values are in the JSON evidence.

`boot.scr` loads `uImage.lz4` and `system.dtb` from the same boot partition.
The current BOOT.bin is an ALGC container with Release 5.9.1 Build 151508 and
`board=evb_dr1m90` markers. Static tools did not expose a bitstream name or
payload hash, so the active FPGA identity remains blocked. Candidate files are
never promoted to active status merely because their filenames match.

## Candidate board and hardware relationships

The official MLK-F3P-CZ02 hardware manual and the supplied Milianke NPU
project both identify the board/core as `MLK-CZ02-DR1M90` with device
`DR1M90GEG400`. The Milianke project contains a SoftNPU-capable HPF, bitstream,
boot files and `anlogic-dr1m90-softip.dts`, so it is the strongest local
candidate. Its 2025.07/20250905 metadata is not an exact Git tag mapping, and
its BOOT/DTB/bitstream hashes do not match the active files.

The D21.1 NPU SD image contains DR1M90 HardNPU/SoftNPU DT strings, but its
board/image correspondence and active use are not established. The official
BoardImages repository contains an AD101V20 image archive only. The D20.1
`AD101V20`/`DR1M90GEG484` and TD projects, the `AD103V20` source-path metadata,
and the `DR1M90GEG484-2` documentation are different example identities;
they must not be substituted for the MLK-F3P-CZ02 or treated as MLK-flashable
images.

## Official repository and SDK relationship

The four local official repositories are recorded in
`results/evidence/024/official_repository_inventory.json` without copying
their contents into Git. `dr1m90_npu` is on `release` at
`199ef4d...` (SDK_2026.01 lineage), `sdk` is on `anlogic-linuxsdk` at
`5a693be...` with SDK_2025.07-linux6.1 commit `beaee2c...` retained for
comparison, `toolchains` is on `master` at `d1bc5fb...`, and `boardimages` is
on `master` at `9964582...`. All four trees are dirty. The SDK BoardConfig
line contains AD101V20/AD103V20 variants but no MLK-specific BoardConfig; the
BoardImages payload contains no MLK-F3P-CZ02 image. These facts establish a
version line and candidate relationships, not a closed MLK mapping.

See `board_device_tree.json` and `board_mapping_matrix.json` for addresses,
compatible strings, hashes and conflicts. Candidate DTBs/HPFs/bitstreams are
metadata-only; none was written.

## Current Device Tree and kernel substrate

The current Device Tree has a hard-NPU platform node with compatible
`anlogic,hard_npu`, registers `0x63f00000/0x100000`, `0xf8800000/0x200` and
`0xf8801000/0x100`, SPI112, and a 128 MiB default CMA reservation. The FPGA
manager is operating, but no hard_npu driver is bound, no soft-NPU node is
present, no NPU/CMA module is loaded and no NPU device node exists. This is an
incomplete runtime substrate, not a permanent capability claim.

The VM SDK kernel source Makefile is 6.1.111 and the `anlogic_dr1m90_defconfig`
is available, but no matching source-tree `.config`, `Module.symvers` or
`System.map` was found. The candidate defconfig does not set
`CONFIG_MODVERSIONS`; the active kernel value is unknown. The three isolated
driver modules have matching text vermagic, and all 51 undefined symbol names
were found in board kallsyms, but export/CRC provenance and active config are
not proven. Vermagic and name presence are not loadability proof.

## Controlled deployment plan (not executed)

1. **Preflight**: retain the successful read-only board route; capture boot
   media, U-Boot environment (if exposed), kernel/DTB/bitstream identities,
   `/proc/device-tree`, `dmesg`, `/proc/iomem`, CMA, kernel config,
   `Module.symvers` and module provenance. Stop while the active FPGA payload
   or source identity is unknown.
2. **Use an isolated SD card first**: keep the current eMMC untouched. Record
   source-media serial/identity, every file hash, and a byte-level backup made
   outside Git. Do not format or write media until a separate human approval.
3. **Prepare a matched package**: exact MLK-F3P-CZ02/DR1M90GEG400 HPF,
   bitstream, DTB, kernel source/config/Module.symvers, drivers, Arm NN
   libraries and demo must form one versioned release. Verify module
   architecture, vermagic, symbol CRCs and DT/FPGA compatible strings.
4. **Recovery**: capture serial/U-Boot output and retain the original SD/eMMC
   boot selection. If the SD candidate fails, power down, remove the SD card
   and boot the untouched eMMC; use the documented switch position and serial
   console. Stop on boot loops, kernel panic, unexpected storage writes,
   missing CMA or mismatched NPU probe.
5. **Module preflight**: only after approval, use the vendor-documented order
   (normally CMA allocator before NPU drivers; exact order must be confirmed
   from the matched release). Expect `/dev/cma_mem` plus the applicable
   `/dev/hard_npu` and/or `/dev/soft_npu`, and matching `dmesg` probe lines.
   Missing nodes, unresolved symbols, or an unexpected compatible string is a
   hard stop; never force-load a module.
6. **Demo gate**: verify all runtime libraries, headers, model/config files,
   loader paths, device nodes, CMA, and driver/bitstream versions in an
   isolated directory. Run at most one vendor one-shot after a separate
   approval. Do not convert the project YOLOv5n model in this task.
7. **Rollback**: retain the original boot files and hashes, power off before
   changing media, return the boot switch to the untouched eMMC path, and
   confirm the original kernel, DTB, rootfs and services before any further
   work. No recovery action is performed by Task 024.

## Current verdict

Primary: `BLOCKED_ACTIVE_BITSTREAM_IDENTITY`.

Secondary: `BLOCKED_ACTIVE_BITSTREAM_SOURCE_MAPPING`,
`BLOCKED_ACTIVE_DTB_SOURCE_MAPPING`, `BLOCKED_KERNEL_SYMBOL_PROVENANCE`,
`BLOCKED_SAFE_ROLLBACK_PLAN`, `CANDIDATE_ASSET_NOT_ACTIVE`,
`MLK_TO_OFFICIAL_SDK_MAPPING_PARTIAL`, `OFFICIAL_REPOSITORY_TREES_DIRTY`.

The current board is not approved for controlled deployment. Active boot-file
and DTB file identity are read-confirmed, but the FPGA payload/source mapping,
exact SDK/BoardConfig lineage, kernel symbol provenance and an external
rollback backup remain open. The next task must close these gates before any
load or write operation.
