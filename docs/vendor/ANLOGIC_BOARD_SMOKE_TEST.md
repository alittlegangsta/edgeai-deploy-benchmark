# Anlogic DR1 board smoke package

This package was prepared from existing AArch64 ELF artifacts and was later
used for the approved Anlogic DR1M90 user-space smoke test. No NPU, driver,
eMMC, or vendor demo operation was performed.

## Locations

The source artifacts were found (rather than assumed) under:

```text
/home/uisrc/vendor/anlogic/builds/toolchain_smoke/
```

The VM deployment package is:

```text
/home/uisrc/vendor/anlogic/builds/board_smoke_package/
```

The VMware shared copy is:

```text
/mnt/hgfs/fpga_info/_generated/board_smoke_package/
```

Its Windows-equivalent location is:

```text
C:\Users\Administrator\Desktop\fpga_info\_generated\board_smoke_package
```

Each location contains seven regular files: three ELF files, `SHA256SUMS`,
`board_probe.sh`, `README.txt`, and the previously generated
`BOARD_RUN_ORDER.txt`. Both copies contain exactly three ELF64 AArch64 files,
and `sha256sum -c SHA256SUMS` passed in both locations.

## Package contents

| Package name | Source artifact | SHA256 | Linkage | Interpreter | NEEDED |
| --- | --- | --- | --- | --- | --- |
| `hello_c_static` | `toolchain_smoke/hello_c_static` | `10f41dd84947e8774f6a00199188bfaf0921ac187cd61be3e8c85d484d9cae02` | static | none | none |
| `hello_c_dynamic` | `toolchain_smoke/hello_c` | `2fd2e5adb6a112109fe29fa7f1ab43248df0a928af48ecf42d8e64c0c8741005` | dynamic | `/lib/ld-linux-aarch64.so.1` | `libc.so.6` |
| `hello_cpp_dynamic` | `toolchain_smoke/hello_cpp` | `605ebeab229cd6abc14f61432019ad997f4209ffb71cfad10527535458df4464` | dynamic | `/lib/ld-linux-aarch64.so.1` | `libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6` |

The package total is 4,981,926 bytes. The original `toolchain_smoke` artifacts
were not modified; package names are copies only.

`SHA256SUMS` contains exactly four entries: the three ELF files and
`board_probe.sh`. It intentionally does not list the two text instructions.

## Required manual run order

The order is intentionally conservative:

1. Run `hello_c_static` first and collect its exit code.
2. Before any dynamic run, inspect the board's dynamic loader and required
  libc.
3. Run `hello_c_dynamic` second and collect its exit code.
4. Run `hello_cpp_dynamic` last and collect its exit code.
5. Stop immediately if any step fails; do not continue to later programs.

`BOARD_RUN_ORDER.txt` in the package is the short copy of these instructions.
The previous audit had NOT_RUN status because /tmp/board_smoke was absent.
After the package was transferred, the three ELF files initially arrived as
mode 0644. An explicitly authorized chmod 0755 on only those three files
preserved their SHA256 values and enabled the direct smoke run. This metadata
correction does not modify ELF contents.

The intermediate mode-0644 execution attempt is recorded as
`execution_attempt: BLOCKED_BEFORE_EXEC`, `blocker: FILE_NOT_EXECUTABLE`, shell
exit code `126`, and `elf_runtime_result: NOT_RUN`. Exit code 126 here is the
shell's refusal to execute a non-executable file, not an ELF runtime failure.

The current board run passed in the required order:

| Program | Exit code | stdout | stderr |
| --- | ---: | --- | --- |
| hello_c_static | 0 | edgeai_arm_toolchain_hello_c; sizeof(void*)=8 | empty |
| hello_c_dynamic | 0 | edgeai_arm_toolchain_hello_c; sizeof(void*)=8 | empty |
| hello_cpp_dynamic | 0 | edgeai_arm_toolchain_hello_cpp\\nsizeof(void*)=8\\nvector_size=3 | empty |

The literal \\n sequences in the C++ row are recorded exactly as observed in
the captured stdout. Evidence is under
results/logs/vendor/board_runtime/hello_*_runtime.log,
board_smoke_permissions.log, and board_smoke_checksum_after_chmod.log.

## Board-side probe

[`scripts/vendor/probe_anlogic_board.sh`](../../scripts/vendor/probe_anlogic_board.sh)
is a read-only probe for a later board session. It uses `set -u`, tolerates
missing BusyBox commands, and reports only identity, kernel/OS, limited CPU,
libc/loader, memory/storage, network/SSH, NPU device nodes, and module-file
presence. It does not install software, modify the system, load modules, or
run NPU code.

The probe remains a read-only optional provenance helper. It was not used to
enter the NPU stage, and it does not load modules or run NPU code.

## Reproducibility

Use the VM wrapper when regenerating the package:

```bash
./scripts/vendor/prepare_board_smoke_package.sh
```

The script locates executable AArch64 ELF files only in the existing
`/home/uisrc/vendor/anlogic/builds/toolchain_smoke` source directory,
classifies static C, dynamic C, and dynamic C++ using `file` and `readelf`,
checks each source hash, and performs idempotent copies. It rejects unexpected
files or hash mismatches rather than deleting or overwriting them.

No host compiler was used in this preparation, and no target ELF was executed.

## Current boundary

- Board connection: completed through the authorized SSH wrapper.
- User-space toolchain smoke: PASS for all three programs after the
  permission-only correction.
- Board OS, loader, libc, and SSH service: recorded in the board runtime audit.
- NPU device/runtime validation: not performed and remains outside this task.
- CMake installation: not requested or performed.
- NPU runtime and driver validation: not part of this smoke package.
- The earlier package hash check alone did not prove that the board could
  execute the dynamic binaries; the current direct execution logs now provide
  that evidence for this fixed smoke package.
