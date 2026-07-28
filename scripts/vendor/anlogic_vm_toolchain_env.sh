#!/usr/bin/env bash
# Reference environment for the Anlogic Ubuntu VM only.
# Source this file inside that VM; it does not connect remotely or modify shell rc files.
set -euo pipefail

export ANLOGIC_VM_TOOLCHAIN_ROOT="${ANLOGIC_VM_TOOLCHAIN_ROOT:-/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0}"
export AARCH64_CROSS_PREFIX="${AARCH64_CROSS_PREFIX:-$ANLOGIC_VM_TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-}"
export CC="${CC:-${AARCH64_CROSS_PREFIX}gcc}"
export CXX="${CXX:-${AARCH64_CROSS_PREFIX}g++}"
export AR="${AR:-${AARCH64_CROSS_PREFIX}ar}"
export LD="${LD:-${AARCH64_CROSS_PREFIX}ld}"
export STRIP="${STRIP:-${AARCH64_CROSS_PREFIX}strip}"
export SYSROOT="${SYSROOT:-$ANLOGIC_VM_TOOLCHAIN_ROOT/aarch64-linux-gnu/libc}"

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  printf 'ANLOGIC_VM_TOOLCHAIN_ROOT=%s\n' "$ANLOGIC_VM_TOOLCHAIN_ROOT"
  printf 'AARCH64_CROSS_PREFIX=%s\n' "$AARCH64_CROSS_PREFIX"
  printf 'CC=%s\n' "$CC"
  printf 'CXX=%s\n' "$CXX"
  printf 'AR=%s\n' "$AR"
  printf 'LD=%s\n' "$LD"
  printf 'STRIP=%s\n' "$STRIP"
  printf 'SYSROOT=%s\n' "$SYSROOT"
  printf 'reference_only=true\n'
fi
