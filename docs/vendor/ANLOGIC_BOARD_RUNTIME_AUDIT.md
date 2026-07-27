# Anlogic DR1M90 board runtime audit

This is the first read-only SSH audit of the physical Anlogic DR1M90 board. It
does not load modules, install packages, run a vendor demo, write eMMC, or
claim that NPU execution is ready.

## Access and evidence

The only access path was `/home/dministrator/bin/anlogic-board-ssh`. The initial
probe returned `board_ssh=PASS`, root identity, and an AArch64 Linux 6.1.111
kernel. Complete command output is preserved in
`results/logs/vendor/board_runtime/00_ssh_connectivity.log` and
`01_runtime_environment.log`; corrected supplementary checks are in
`03_modules_and_npu.log`, `03b_module_matches.log`,
`04_emmc_tree_corrected.log`, `05_npu_search.log`,
`06_smoke_execution.log`, and `07_smoke_location.log`.

The board clock reported `Thu Jan 1 00:36:09 UTC 1970`; timestamps in this
audit therefore come from the host evidence files rather than the board clock.

## System identity

| Field | Observation |
| --- | --- |
| Model | `Anlogic, DR1M90 FPSoc` |
| OS | Buildroot 2022.02.6 |
| Kernel | 6.1.111-rt42, PREEMPT, SMP |
| Architecture | AArch64 / Arm architecture 8 |
| CPU | 2 cores; implementer `0x41`; part `0xd04` |
| Memory | 988.7M reported by `free`; no swap |
| libc | glibc 2.25 |
| Network | eth1 UP with `192.168.50.2/24`; eth0 down/no carrier |
| SSH | OpenSSH 8.9p1 listening on TCP 22 |
| Current user | root |

`lscpu`, `getconf`, `file`, and `readelf` were not available on the board.
The loader and runtime library paths were nevertheless inspected with `ls`;
ELF-level board-side confirmation remains pending.

## eMMC versus external storage

The running command line says `root=/dev/mmcblk1p2`; `/dev/mmcblk1p2` is the
current ext4 root and `/dev/mmcblk1p1` is the current vfat boot partition. The
external `/dev/sda` disk was explicitly treated as a separate Xilinx PetaLinux
history disk and was not used as Anlogic evidence.

The eMMC boot partition contains `BOOT.bin`, `boot.scr`, and `system.dtb`.
The rootfs `image/` directory contains another set of those generic boot
artifacts plus `uImage.lz4` and `rootfs.tar.gz`. Their hashes are recorded in
`board_runtime_inventory.yaml` and the corrected eMMC log. These opaque binary
files were not opened or executed, so they do not prove an NPU bitstream.

The first eMMC inventory used unsupported BusyBox `find -printf` and did not
provide complete metadata. `04_emmc_tree_corrected.log` is the authoritative
follow-up using supported listing and count commands.

## Toolchain/runtime comparison

The kernel build string identifies `aarch64-linux-gnu-gcc (Linaro GCC
7.5-2019.12) 7.5.0`, matching the compiler identity recorded for the VM's
SDK_2025_07 toolchain. The board has `/lib/ld-linux-aarch64.so.1`,
`/lib/libc.so.6`, `/lib/libstdc++.so.6`, and `/lib/libgcc_s.so.1`, with glibc
2.25 reported by `ldd`. This is a compiler/libc identity match, not proof that
the complete SDK or Arm NN bundle is installed on the board.

The previous audit found `/tmp/board_smoke` absent. That attempt was
`previous_attempt: NOT_RUN` with `previous_blocker: INPUT_PACKAGE_MISSING`,
not a program execution failure.

An intermediate permission-only attempt after the package became available was
`execution_attempt: BLOCKED_BEFORE_EXEC` with `blocker: FILE_NOT_EXECUTABLE`
and shell exit code `126`. The shell rejected mode `0644` before entering the
ELF, so `elf_runtime_result` was `NOT_RUN`; this must not be described as an
ELF runtime failure. The authorized metadata-only correction changed the three
ELF files to mode `0755` without changing their contents or SHA256 values.

In the current approved attempt, the verified package was copied with Windows
OpenSSH `scp.exe` through `/tmp/board_smoke.new` and atomically renamed to
`/tmp/board_smoke`. The directory contains the seven expected package files.
Board-side `sha256sum -c SHA256SUMS` returned `OK` for all four covered files.
The files initially arrived mode `0644`; the explicitly authorized
`chmod 0755` changed only permission metadata, and all three ELF SHA256 values
remained unchanged.

The ordered execution then passed directly:

| Program | Exit code | stdout | stderr |
| --- | ---: | --- | --- |
| `hello_c_static` | 0 | `edgeai_arm_toolchain_hello_c`; `sizeof(void*)=8` | empty |
| `hello_c_dynamic` | 0 | `edgeai_arm_toolchain_hello_c`; `sizeof(void*)=8` | empty |
| `hello_cpp_dynamic` | 0 | literal `\\n`-separated output: `edgeai_arm_toolchain_hello_cpp\\nsizeof(void*)=8\\nvector_size=3` | empty |

`BOARD_TOOLCHAIN_RUNTIME` is now `PASS`. The NPU stage was not entered.

## NPU readiness

No `/dev/hard_npu`, `/dev/soft_npu`, or `/dev/cma_mem` node was present. The
loaded-module list contained only `aic_load_fw`; the installed module metadata
and a bounded current-root search found no NPU/CMA module, Arm NN library,
NPU runtime, HPF, bitstream, model, or demo marker. The absence of a matching
name in module metadata does not prove that a driver could not be built into
the kernel, but no board-side NPU interface is currently exposed.

The VM SDK audit remains the source of the separate package fact that SDK_2025_07
contains Arm NN 32.1.0 and an Alnpu custom-backend interface. That VM fact must
not be promoted to board runtime readiness.

## Decision gate

| Decision | Result | Basis |
| --- | --- | --- |
| BOARD_TOOLCHAIN_RUNTIME | **PASS** | All three direct executions returned exit code 0 |
| CHECKSUM_VALIDATION | **PASS** | Board `sha256sum -c SHA256SUMS` passed |
| EXECUTABLE_PERMISSION_VALIDATION | **PASS** | Only three ELF files changed from 0644 to 0755 |
| BOARD_TOOLCHAIN_FAMILY_MATCH | **CONFIRMED** | Linaro GCC 7.5.0 family |
| BOARD_USERSPACE_ABI_COMPATIBILITY | **CONFIRMED** | AArch64/glibc 2.25 paths observed |
| BOARD_FULL_SDK_MATCH | **UNKNOWN** | Full SDK files were not audited on the board |
| BOARD_NPU_RUNTIME_MATCH | **NOT_APPLICABLE** | NPU stage was not entered |
| BOARD_SDK_TOOLCHAIN_MATCH | **CONFIRMED** | Board kernel compiler and glibc identity match VM SDK toolchain scope |
| BOARD_NPU_DEVICE_READY | **NO** | Device nodes absent |
| BOARD_NPU_DRIVER_PRESENT_ON_DISK | **NO** | No NPU-specific module/runtime file found; built-in status remains caveated |
| BOARD_NPU_BOOT_ASSET_PRESENT | **UNKNOWN** | Generic boot files exist; BOOT.bin payload was not opened |
| CURRENT_EMMC_NPU_READY | **NO** | No device, module, runtime, or model interface observed |

All driver loading, NPU demo execution, model deployment, and benchmarking
remain HOLD and require separate approval. The user-space smoke gate is now
complete; any next step must be separately approved NPU or deployment work.
