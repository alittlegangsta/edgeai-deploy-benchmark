# Anlogic DR1M90 NPU readiness audit

## Read-only result

The board identifies as `Anlogic, DR1M90 FPSoc`, but the current eMMC Linux
runtime does not expose the NPU interface required by the SDK's Alnpu backend.

Observed absence:

- `/dev/hard_npu` — not present;
- `/dev/soft_npu` — not present;
- `/dev/cma_mem` and matching CMA device names — not present;
- NPU-specific loaded module — not present (`aic_load_fw` was the only loaded
  module);
- NPU/CMA module names in `/lib/modules/6.1.111-rt42` metadata — not found;
- `libarmnn*`, NPU runtime names, HPF/bitstream names, model names, and demo
  markers in the bounded current-root search — not found.

Evidence is preserved in `03_modules_and_npu.log`,
`03b_module_matches.log`, and `05_npu_search.log`. No module was loaded and no
vendor program was run.

## Boot assets

The active eMMC has generic `BOOT.bin`, `boot.scr`, and `system.dtb` files on
the vfat boot partition, and another generic image set under the rootfs
`image/` directory. The audit deliberately did not open opaque boot binaries.
Therefore an NPU-specific HPF/bitstream payload cannot be inferred:
`BOARD_NPU_BOOT_ASSET_PRESENT: UNKNOWN`.

The external `/dev/sda` disk is a separate Xilinx PetaLinux history disk and is
not evidence for this Anlogic board.

## SDK comparison boundary

The VM-side SDK_2025_07 inventory found Arm NN 32.1.0 and an Alnpu custom
backend interface with `/dev/hard_npu` strings. Those are package/source facts
from the VM SDK, not a successful board observation. The board audit found no
corresponding runtime files or device nodes, so:

| Decision | Result |
| --- | --- |
| BOARD_NPU_DEVICE_READY | **NO** |
| BOARD_NPU_DRIVER_PRESENT_ON_DISK | **NO** for observable loadable/module/runtime files; built-in status remains unproven |
| BOARD_NPU_BOOT_ASSET_PRESENT | **UNKNOWN** |
| CURRENT_EMMC_NPU_READY | **NO** |

## Required next approvals

Driver loading, firmware/HPF deployment, NPU demo execution, model staging,
and any benchmark are all **HOLD**. A future task must first establish the
board-specific boot assets and driver package, then load nothing until an
explicit human-approved procedure is recorded. No claim of NPU readiness may
be made from the VM SDK inventory alone.
