#!/usr/bin/env bash
# Read-only validation of the already-installed Linux AArch64 toolchain in the VM.
# This script does not extract archives, install packages, run target ELF files,
# invoke SDK scripts, or connect to a board.
set -euo pipefail

WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: VM wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi

"$WRAPPER" 'bash -s' <<'REMOTE'
set -euo pipefail

ROOT=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
PREFIX="$ROOT/bin/aarch64-linux-gnu-"
SYSROOT="$ROOT/aarch64-linux-gnu/libc"
LOG=/home/uisrc/vendor/anlogic/logs/toolchain_setup

LIBC_SO="$("${PREFIX}gcc" -print-file-name=libc.so)"
LIBSTDCXX_SO="$("${PREFIX}gcc" -print-file-name=libstdc++.so)"
CRT1="$("${PREFIX}gcc" -print-file-name=crt1.o)"
CRTI="$("${PREFIX}gcc" -print-file-name=crti.o)"
CRTN="$("${PREFIX}gcc" -print-file-name=crtn.o)"
LOADER="$("${PREFIX}gcc" -print-file-name=ld-linux-aarch64.so.1)"
LIBGCC="$("${PREFIX}gcc" -print-file-name=libgcc_s.so.1)"
CPP_INCLUDE="$ROOT/aarch64-linux-gnu/include/c++"

test -d "$ROOT"
test -x "${PREFIX}gcc"
test -x "${PREFIX}g++"
test -x "${PREFIX}ld"
test -x "${PREFIX}readelf"
test -x "${PREFIX}strip"
test -d "$SYSROOT"

{
  printf 'toolchain_root=%s\n' "$ROOT"
  printf 'cross_prefix=%s\n' "$PREFIX"
  printf 'sysroot=%s\n' "$SYSROOT"
  printf 'gcc_path=%s\n' "${PREFIX}gcc"
  printf 'gxx_path=%s\n' "${PREFIX}g++"
  printf 'ld_path=%s\n' "${PREFIX}ld"
  printf 'readelf_path=%s\n' "${PREFIX}readelf"
  printf 'strip_path=%s\n' "${PREFIX}strip"
  printf 'cpp_include=%s\n' "$CPP_INCLUDE"
  printf 'compiler_reported_libc=%s\n' "$LIBC_SO"
  printf 'compiler_reported_libstdcxx=%s\n' "$LIBSTDCXX_SO"
  printf 'compiler_reported_crt1=%s\n' "$CRT1"
  printf 'compiler_reported_crti=%s\n' "$CRTI"
  printf 'compiler_reported_crtn=%s\n' "$CRTN"
  printf 'compiler_reported_loader=%s\n' "$LOADER"
  printf 'compiler_reported_libgcc=%s\n' "$LIBGCC"
  printf 'gcc_version:\n'; "${PREFIX}gcc" --version
  printf 'gxx_version:\n'; "${PREFIX}g++" --version
  printf 'dumpmachine='; "${PREFIX}gcc" -dumpmachine
  printf 'dumpversion='; "${PREFIX}gcc" -dumpversion
  printf 'print_sysroot='; "${PREFIX}gcc" -print-sysroot
  printf 'print_file_libc='; "${PREFIX}gcc" -print-file-name=libc.so
  printf 'print_file_libstdcxx='; "${PREFIX}gcc" -print-file-name=libstdc++.so
  printf 'print_file_crt1='; "${PREFIX}gcc" -print-file-name=crt1.o
  printf 'print_file_loader='; "${PREFIX}gcc" -print-file-name=ld-linux-aarch64.so.1
  printf 'gcc_search_dirs:\n'; "${PREFIX}gcc" -print-search-dirs
  printf 'gcc_verbose:\n'; "${PREFIX}gcc" -v </dev/null
  printf 'gxx_verbose:\n'; "${PREFIX}g++" -v </dev/null
} > "$LOG/compiler_versions.txt"

for path in \
  "$SYSROOT/usr/include/stdio.h" \
  "$SYSROOT/usr/include/stdlib.h" \
  "$CPP_INCLUDE" \
  "$LIBC_SO" \
  "$LIBSTDCXX_SO" \
  "$SYSROOT/lib/libgcc_s.so.1" \
  "$SYSROOT/lib/ld-linux-aarch64.so.1" \
  "$SYSROOT/lib/libstdc++.so" \
  "$SYSROOT/lib/libstdc++.so.6" \
  "$SYSROOT/usr/lib/crt1.o" \
  "$SYSROOT/usr/lib/crti.o" \
  "$SYSROOT/usr/lib/crtn.o"
do
  test -e "$path"
done

{
  printf 'sysroot=%s\n' "$SYSROOT"
  for path in \
    "$SYSROOT/usr/include/stdio.h" \
    "$SYSROOT/usr/include/stdlib.h" \
    "$CPP_INCLUDE" \
    "$LIBC_SO" \
    "$LIBSTDCXX_SO" \
    "$SYSROOT/lib/libgcc_s.so.1" \
    "$SYSROOT/lib/ld-linux-aarch64.so.1" \
    "$SYSROOT/lib/libstdc++.so" \
    "$SYSROOT/lib/libstdc++.so.6" \
    "$SYSROOT/usr/lib/crt1.o" \
    "$SYSROOT/usr/lib/crti.o" \
    "$SYSROOT/usr/lib/crtn.o"
  do
    kind="$(file -b "$path")"
    printf '%s: %s\n' "$path" "$kind"
    case "$kind" in
      *ELF*) readelf -h "$path" | grep -E 'Class:|Machine:|Type:' ;;
      *) printf 'readelf=SKIPPED_NOT_ELF\n' ;;
    esac
  done
} > "$LOG/sysroot_inventory.txt"

{
  for path in "$SYSROOT/lib/libc.so.6" "$SYSROOT/lib/libstdc++.so.6" "$SYSROOT/lib/ld-linux-aarch64.so.1"; do
    printf '\n=== %s ===\n' "$path"
    file "$path"
    readelf -h "$path" | grep -E 'Class:|Machine:|Type:|Entry point'
    readelf -d "$path" | grep -E 'SONAME|NEEDED|RPATH|RUNPATH' || true
  done
} > "$LOG/runtime_elf.txt"

printf 'toolchain_validation=PASS\n'
printf 'toolchain_root=%s\n' "$ROOT"
printf 'sysroot=%s\n' "$SYSROOT"
REMOTE
