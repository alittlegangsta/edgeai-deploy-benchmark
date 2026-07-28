# Anlogic board toolchain/runtime validation

## Scope

This record compares the real board's observed user-space ABI and kernel build
identity with the VM-side SDK_2025_07 toolchain record. It does not rebuild the
compiler or enter the NPU stage.

## Observed board ABI

- `uname -m`: `aarch64`.
- Buildroot: `2022.02.6`.
- Kernel: `6.1.111-rt42`.
- Kernel compiler: `aarch64-linux-gnu-gcc (Linaro GCC 7.5-2019.12) 7.5.0`.
- `ldd --version`: GNU libc 2.25.
- Loader symlink: `/lib/ld-linux-aarch64.so.1 -> ld-2.25.so`.
- Runtime files present: `/lib/libc.so.6`, `/lib/libstdc++.so.6`, and
  `/lib/libgcc_s.so.1`.

The board did not provide `file`, `readelf`, or `getconf`, so the audit does
not invent board-side ELF headers or a GNU libc query. The exact shell output
is in `results/logs/vendor/board_runtime/01_runtime_environment.log`.

## VM SDK comparison

The VM toolchain manifest records the same Linaro GCC 7.5.0 family and
`aarch64-linux-gnu` target. The board kernel string independently reports that
compiler family, and the board's glibc 2.25 runtime is consistent with the
validated SDK sysroot identity.

The scoped conclusions are:

- `BOARD_TOOLCHAIN_FAMILY_MATCH: CONFIRMED`.
- `BOARD_USERSPACE_ABI_COMPATIBILITY: CONFIRMED`.
- `BOARD_FULL_SDK_MATCH: UNKNOWN`.
- `BOARD_NPU_RUNTIME_MATCH: NOT_APPLICABLE` for this user-space smoke task.

It does not prove matching SDK files, dynamic loader search paths for every
program, or NPU runtime compatibility.

## Smoke gate history and current attempt

The previous audit checked the required input location exactly and found no
package:

```text
/tmp/board_smoke/hello_c_static
/tmp/board_smoke/hello_c_dynamic
/tmp/board_smoke/hello_cpp_dynamic
```

That previous attempt was `NOT_RUN` with blocker `INPUT_PACKAGE_MISSING`; it was
not a program execution failure.

The intermediate permission-only attempt was explicitly recorded as
`execution_attempt: BLOCKED_BEFORE_EXEC`, `blocker: FILE_NOT_EXECUTABLE`, shell
exit code `126`, and `elf_runtime_result: NOT_RUN`. Mode `0644` prevented the
shell from entering the ELF; it was not an ELF runtime failure. An authorized
`chmod 0755` changed only metadata, preserved every SHA256 value, and enabled
the direct runtime checks below.

In the current approved attempt, the package was copied from the Windows
OpenSSH source directory with `scp.exe` into `/tmp/board_smoke.new`, then
renamed to `/tmp/board_smoke`. The board-side `SHA256SUMS` check passed for all
four covered files. The copied directory contained the seven expected package
files.

The files initially arrived mode `0644`. The explicitly authorized
`chmod 0755` changed only metadata; all three ELF SHA256 values remained
unchanged and a second `SHA256SUMS` check passed.

The ordered direct execution then passed:

| Program | Board result |
| --- | --- |
| C static | PASS — exit code 0 |
| C dynamic | PASS — exit code 0 |
| C++ dynamic | PASS — exit code 0 |

Evidence: `board_smoke_permissions.log`,
`board_smoke_checksum_after_chmod.log`, and the three
`hello_*_runtime.log` files. The earlier absence is recorded in
`06_smoke_execution.log` and `07_smoke_location.log`.

## Decisions

| Item | Decision |
| --- | --- |
| BOARD_TOOLCHAIN_FAMILY_MATCH | **CONFIRMED** — Linaro GCC 7.5.0 family |
| BOARD_USERSPACE_ABI_COMPATIBILITY | **CONFIRMED** — AArch64/glibc 2.25 paths observed |
| BOARD_FULL_SDK_MATCH | **UNKNOWN** |
| BOARD_NPU_RUNTIME_MATCH | **NOT_APPLICABLE** |
| Board toolchain runtime | **PASS** — all three direct executions returned zero |
| Checksum validation | **PASS** |
| Executable permission validation | **PASS** — only three ELF mode bits changed |
| Transfer/execute ELF package | **PASS** for this user-space smoke package |
| Install CMake | **HOLD**; not needed for this read-only runtime audit |
| Build NPU demo | **HOLD**; NPU device/runtime prerequisites are absent |
