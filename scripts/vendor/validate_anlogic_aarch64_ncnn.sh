#!/usr/bin/env bash
set -euo pipefail

VM_WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
[[ -x "$VM_WRAPPER" ]] || {
  printf 'VM wrapper is not executable: %s\n' "$VM_WRAPPER" >&2
  exit 1
}

"$VM_WRAPPER" 'bash -s' <<'REMOTE'
set -euo pipefail

ROOT=/home/uisrc/build/ncnn-aarch64
CMAKE=/home/uisrc/.local/cmake-3.16.9/bin/cmake
TOOLCHAIN=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
LIB="$ROOT/install/lib/libncnn.a"
SMOKE="$ROOT/anlogic_ncnn_smoke"

test -x "$CMAKE"
test -x "$TOOLCHAIN/bin/aarch64-linux-gnu-gcc"
test -x "$TOOLCHAIN/bin/aarch64-linux-gnu-g++"
test -f "$ROOT/build/CMakeCache.txt"
test -s "$LIB"
test -s "$SMOKE"

"$CMAKE" --version
test "$("$TOOLCHAIN/bin/aarch64-linux-gnu-gcc" -dumpmachine)" = "aarch64-linux-gnu"

for expected in \
  'CMAKE_BUILD_TYPE:STRING=Release' \
  'NCNN_ARM82:BOOL=OFF' \
  'NCNN_BF16:BOOL=ON' \
  'NCNN_BUILD_BENCHMARK:BOOL=OFF' \
  'NCNN_BUILD_EXAMPLES:BOOL=OFF' \
  'NCNN_BUILD_TESTS:BOOL=OFF' \
  'NCNN_BUILD_TOOLS:BOOL=OFF' \
  'NCNN_INT8:BOOL=OFF' \
  'NCNN_OPENMP:BOOL=OFF' \
  'NCNN_PYTHON:BOOL=OFF' \
  'NCNN_RUNTIME_CPU:BOOL=ON' \
  'NCNN_SHARED_LIB:BOOL=OFF' \
  'NCNN_VFPV4:BOOL=ON' \
  'NCNN_VULKAN:BOOL=OFF'
do
  grep -Fxq "$expected" "$ROOT/build/CMakeCache.txt"
done

member_count="$("$TOOLCHAIN/bin/aarch64-linux-gnu-ar" t "$LIB" | wc -l)"
machine_count="$("$TOOLCHAIN/bin/aarch64-linux-gnu-readelf" -h "$LIB" 2>/dev/null |
  grep -c 'Machine:.*AArch64')"
test "$member_count" -gt 0
test "$machine_count" -eq "$member_count"

file "$SMOKE"
"$TOOLCHAIN/bin/aarch64-linux-gnu-readelf" -h "$SMOKE" |
  grep -q 'Machine:.*AArch64'
"$TOOLCHAIN/bin/aarch64-linux-gnu-readelf" -l "$SMOKE" |
  grep -q 'Requesting program interpreter: /lib/ld-linux-aarch64.so.1'
if "$TOOLCHAIN/bin/aarch64-linux-gnu-readelf" -d "$SMOKE" |
  grep -Eiq 'vulkan|python|gomp'; then
  printf 'unexpected runtime dependency\n' >&2
  exit 1
fi

sha256sum "$LIB" "$SMOKE"
printf 'aarch64_ncnn_validation=PASS\n'
printf 'board_execution=NOT_RUN\n'
REMOTE
