#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"
case "$MODE" in
  --check|--execute) ;;
  *)
    printf 'usage: %s [--check|--execute]\n' "$0" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VM_WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
NCNN_SOURCE="${NCNN_SOURCE:-/home/dministrator/src/ncnn-20240410}"
NCNN_REVISION="56775de50990ab7f16627efdcf5529b49541206f"
NCNN_REMOTE="https://github.com/Tencent/ncnn.git"
LOCAL_ARCHIVE="/tmp/ncnn-20240410-56775de.tar.gz"
TOOLCHAIN_FILE="$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake"
SMOKE_SOURCE="$REPO_ROOT/cpp/apps/anlogic_ncnn_smoke.cpp"
VM_ROOT="/home/uisrc/build/ncnn-aarch64"

[[ -x "$VM_WRAPPER" ]] || {
  printf 'VM wrapper is not executable: %s\n' "$VM_WRAPPER" >&2
  exit 1
}
[[ -d "$NCNN_SOURCE/.git" ]] || {
  printf 'ncnn Git source is missing: %s\n' "$NCNN_SOURCE" >&2
  exit 1
}
[[ -f "$TOOLCHAIN_FILE" ]] || {
  printf 'toolchain file is missing: %s\n' "$TOOLCHAIN_FILE" >&2
  exit 1
}
[[ -f "$SMOKE_SOURCE" ]] || {
  printf 'smoke source is missing: %s\n' "$SMOKE_SOURCE" >&2
  exit 1
}

actual_revision="$(git -C "$NCNN_SOURCE" rev-parse HEAD)"
actual_remote="$(git -C "$NCNN_SOURCE" remote get-url origin)"
mapfile -t point_tags < <(git -C "$NCNN_SOURCE" tag --points-at HEAD)
[[ "$actual_revision" == "$NCNN_REVISION" ]] || {
  printf 'ncnn revision mismatch: %s\n' "$actual_revision" >&2
  exit 1
}
[[ "$actual_remote" == "$NCNN_REMOTE" ]] || {
  printf 'ncnn remote mismatch: %s\n' "$actual_remote" >&2
  exit 1
}
printf '%s\n' "${point_tags[@]}" | grep -Fxq '20240410' || {
  printf 'ncnn tag 20240410 does not point at HEAD\n' >&2
  exit 1
}

printf 'mode=%s\n' "$MODE"
printf 'ncnn_remote=%s\n' "$actual_remote"
printf 'ncnn_revision=%s\n' "$actual_revision"
printf 'toolchain_file=%s\n' "$TOOLCHAIN_FILE"
printf 'smoke_source=%s\n' "$SMOKE_SOURCE"

"$VM_WRAPPER" '
set -eu
test -x /home/uisrc/.local/cmake-3.16.9/bin/cmake
test -x /home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-gcc
test -x /home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
test -d /home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/aarch64-linux-gnu/libc
/home/uisrc/.local/cmake-3.16.9/bin/cmake --version
/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-gcc -dumpmachine
'

if [[ "$MODE" == "--check" ]]; then
  printf 'build_check=PASS\n'
  exit 0
fi

git -C "$NCNN_SOURCE" archive \
  --format=tar.gz \
  --prefix=ncnn-20240410/ \
  -o "$LOCAL_ARCHIVE.part" \
  "$NCNN_REVISION"
mv "$LOCAL_ARCHIVE.part" "$LOCAL_ARCHIVE"

transfer_if_needed() {
  local source_path="$1"
  local target_path="$2"
  local source_hash target_hash

  source_hash="$(sha256sum "$source_path" | cut -d ' ' -f 1)"
  target_hash="$("$VM_WRAPPER" "if [ -f '$target_path' ]; then sha256sum '$target_path' | cut -d ' ' -f 1; else printf 'MISSING\\n'; fi")"
  if [[ "$target_hash" == "$source_hash" ]]; then
    printf 'transfer=SKIP_MATCH %s\n' "$target_path"
    return 0
  fi
  if [[ "$target_hash" != "MISSING" ]]; then
    printf 'refusing to overwrite mismatched VM input: %s\n' "$target_path" >&2
    exit 1
  fi
  "$VM_WRAPPER" "cat > '$target_path.part' && mv '$target_path.part' '$target_path'" < "$source_path"
  target_hash="$("$VM_WRAPPER" "sha256sum '$target_path' | cut -d ' ' -f 1")"
  [[ "$target_hash" == "$source_hash" ]] || {
    printf 'transfer hash mismatch: %s\n' "$target_path" >&2
    exit 1
  }
  printf 'transfer=PASS %s\n' "$target_path"
}

"$VM_WRAPPER" "mkdir -p '$VM_ROOT' '$VM_ROOT/logs'"
transfer_if_needed "$LOCAL_ARCHIVE" "$VM_ROOT/ncnn-20240410-56775de.tar.gz"
transfer_if_needed "$TOOLCHAIN_FILE" "$VM_ROOT/anlogic-dr1-aarch64.cmake"
transfer_if_needed "$SMOKE_SOURCE" "$VM_ROOT/anlogic_ncnn_smoke.cpp"

"$VM_WRAPPER" 'bash -s' <<'REMOTE'
set -euo pipefail

ROOT=/home/uisrc/build/ncnn-aarch64
CMAKE=/home/uisrc/.local/cmake-3.16.9/bin/cmake
GXX=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
SYSROOT=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/aarch64-linux-gnu/libc

mkdir -p "$ROOT/source" "$ROOT/build" "$ROOT/install" "$ROOT/logs"
if [[ ! -f "$ROOT/source/CMakeLists.txt" ]]; then
  tar -xzf "$ROOT/ncnn-20240410-56775de.tar.gz" \
    -C "$ROOT/source" --strip-components=1
fi
cp "$ROOT/anlogic-dr1-aarch64.cmake" \
  "$ROOT/source/anlogic-dr1-aarch64.cmake"

"$CMAKE" \
  -S "$ROOT/source" \
  -B "$ROOT/build" \
  -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE="$ROOT/source/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_INSTALL_PREFIX="$ROOT/install" \
  -DCMAKE_BUILD_TYPE=Release \
  -DNCNN_VERSION=20240410 \
  -DNCNN_SHARED_LIB=OFF \
  -DNCNN_VULKAN=OFF \
  -DNCNN_PYTHON=OFF \
  -DNCNN_BUILD_TOOLS=OFF \
  -DNCNN_BUILD_EXAMPLES=OFF \
  -DNCNN_BUILD_BENCHMARK=OFF \
  -DNCNN_BUILD_TESTS=OFF \
  -DNCNN_OPENMP=OFF \
  -DNCNN_RUNTIME_CPU=ON \
  -DNCNN_INT8=OFF \
  -DNCNN_BF16=ON \
  -DNCNN_ARM82=OFF \
  > "$ROOT/logs/ncnn_configure.log" 2>&1
"$CMAKE" --build "$ROOT/build" --parallel 2 \
  > "$ROOT/logs/ncnn_build.log" 2>&1
"$CMAKE" --install "$ROOT/build" \
  > "$ROOT/logs/ncnn_install.log" 2>&1

"$GXX" \
  --sysroot="$SYSROOT" \
  -std=c++17 -O2 -g -Wall -Wextra -Werror \
  -I"$ROOT/install/include/ncnn" \
  "$ROOT/anlogic_ncnn_smoke.cpp" \
  "$ROOT/install/lib/libncnn.a" \
  -pthread -ldl -lm \
  -o "$ROOT/anlogic_ncnn_smoke" \
  > "$ROOT/logs/ncnn_smoke_build.log" 2>&1

test -s "$ROOT/install/lib/libncnn.a"
test -s "$ROOT/anlogic_ncnn_smoke"
file "$ROOT/anlogic_ncnn_smoke"
readelf -h "$ROOT/anlogic_ncnn_smoke" | grep -q 'Machine:.*AArch64'
readelf -l "$ROOT/anlogic_ncnn_smoke" |
  grep -q 'Requesting program interpreter: /lib/ld-linux-aarch64.so.1'
if readelf -d "$ROOT/anlogic_ncnn_smoke" | grep -Eiq 'vulkan|python|gomp'; then
  printf 'unexpected runtime dependency\n' >&2
  exit 1
fi
sha256sum "$ROOT/install/lib/libncnn.a" "$ROOT/anlogic_ncnn_smoke"
REMOTE
