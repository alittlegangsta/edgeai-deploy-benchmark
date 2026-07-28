#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VM_WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
SOURCE_LOCAL="$REPO_ROOT/cpp/apps/anlogic_opencv_smoke.cpp"
VM_BUILD_ROOT="/home/uisrc/vendor/anlogic/builds/opencv_board_smoke"
VM_SOURCE="$VM_BUILD_ROOT/anlogic_opencv_smoke.cpp"

[[ -x "$VM_WRAPPER" ]] || { echo "VM wrapper is not executable: $VM_WRAPPER" >&2; exit 1; }
[[ -f "$SOURCE_LOCAL" ]] || { echo "Smoke source is missing: $SOURCE_LOCAL" >&2; exit 1; }

SOURCE_B64="$(base64 < "$SOURCE_LOCAL" | tr -d '\n')"
printf '%s' "$SOURCE_B64" | "$VM_WRAPPER" "mkdir -p '$VM_BUILD_ROOT' && base64 -d > '$VM_SOURCE'"

mkdir -p "$REPO_ROOT/results/logs/vendor/board_opencv"
"$VM_WRAPPER" 'bash -s' <<'REMOTE' 2>&1 | tee "$REPO_ROOT/results/logs/vendor/board_opencv/opencv_build.log"
set -euo pipefail

TOOLCHAIN_ROOT=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
OPENCV_ROOT=/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64
BUILD_ROOT=/home/uisrc/vendor/anlogic/builds/opencv_board_smoke
SOURCE="$BUILD_ROOT/anlogic_opencv_smoke.cpp"
APP="$BUILD_ROOT/opencv_board_smoke"
PACKAGE="$BUILD_ROOT/package"
SHARED=/mnt/hgfs/fpga_info/_generated/board_opencv_smoke
CXX="$TOOLCHAIN_ROOT/bin/aarch64-linux-gnu-g++"

test -x "$CXX"
test -f "$SOURCE"
test -d "$OPENCV_ROOT/include/opencv4"
test -d "$OPENCV_ROOT/lib"

echo "toolchain_root=$TOOLCHAIN_ROOT"
echo "opencv_root=$OPENCV_ROOT"
echo "compiler=$CXX"
echo "compiler_version=$($CXX --version | head -n 1)"
echo "target_triple=$($CXX -dumpmachine)"
echo "sysroot=$($CXX -print-sysroot)"
opencv_version="$(awk '
  /^#define CV_VERSION_MAJOR/ { major = $3 }
  /^#define CV_VERSION_MINOR/ { minor = $3 }
  /^#define CV_VERSION_REVISION/ { revision = $3 }
  END { print major "." minor "." revision }
' "$OPENCV_ROOT/include/opencv4/opencv2/core/version.hpp")"
echo "opencv_version=$opencv_version"

declare -A LIBS=()
for module in core imgproc imgcodecs; do
  link="$OPENCV_ROOT/lib/libopencv_${module}.so"
  test -e "$link"
  resolved="$(readlink -f "$link")"
  test -f "$resolved"
  soname="$(readelf -d "$resolved" | awk -F'[][]' '/SONAME/ { print $2; exit }')"
  case "$soname" in
    "libopencv_${module}.so."*) ;;
    *) echo "unexpected SONAME for $link: $soname" >&2; exit 1 ;;
  esac
  LIBS[$module]="$resolved|$soname"
  echo "opencv_${module}_resolved=$resolved"
  echo "opencv_${module}_soname=$soname"
  sha256sum "$resolved"
  file "$resolved"
  readelf -h "$resolved" | grep -E 'Class:|Machine:|Type:'
  readelf -d "$resolved" | grep -E 'NEEDED|SONAME|RPATH|RUNPATH'
done

"$CXX" \
  -std=c++17 -O2 -g -Wall -Wextra -Werror \
  -I"$OPENCV_ROOT/include/opencv4" \
  -L"$OPENCV_ROOT/lib" \
  '-Wl,-rpath,$ORIGIN/lib' \
  "$SOURCE" \
  -o "$APP" \
  -lopencv_imgcodecs -lopencv_imgproc -lopencv_core

echo '=== application identity ==='
sha256sum "$APP"
file "$APP"
readelf -h "$APP" | grep -E 'Class:|Machine:|Type:'
readelf -l "$APP" | grep -E 'Requesting program interpreter|INTERP'
readelf -d "$APP" | grep -E 'NEEDED|RPATH|RUNPATH'
if readelf -d "$APP" | grep -Eq 'libopencv_(highgui|videoio|dnn)'; then
  echo 'forbidden OpenCV module linked' >&2
  exit 1
fi

mkdir -p "$PACKAGE/lib"
for existing in "$PACKAGE/lib"/*; do
  [[ -e "$existing" ]] || continue
  case "$(basename "$existing")" in
    libopencv_core.so.*|libopencv_imgproc.so.*|libopencv_imgcodecs.so.*) ;;
    *) echo "unexpected existing package library: $existing" >&2; exit 1 ;;
  esac
done
rm -f "$PACKAGE/opencv_board_smoke" "$PACKAGE/run.sh" "$PACKAGE/README.txt" "$PACKAGE/SHA256SUMS"

for module in core imgproc imgcodecs; do
  entry="${LIBS[$module]}"
  resolved="${entry%%|*}"
  soname="${entry##*|}"
  rm -f "$PACKAGE/lib/$soname"
  cp -L "$resolved" "$PACKAGE/lib/$soname"
done
cp "$APP" "$PACKAGE/opencv_board_smoke"

cat > "$PACKAGE/run.sh" <<'RUN'
#!/bin/sh
set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export LD_LIBRARY_PATH="$SCRIPT_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$SCRIPT_DIR" || exit 1
exec "$SCRIPT_DIR/opencv_board_smoke"
RUN
chmod 0755 "$PACKAGE/opencv_board_smoke" "$PACKAGE/run.sh"

cat > "$PACKAGE/README.txt" <<'README'
Anlogic DR1M90 AArch64 OpenCV user-space smoke package

This package uses the SDK OpenCV 4.7.0 AArch64 build and links only:
  opencv_core
  opencv_imgproc
  opencv_imgcodecs

It does not use highgui, videoio, dnn, FFmpeg, camera, GUI, ncnn, or NPU.
The package does not replace system glibc, the dynamic loader, libstdc++, or
libgcc_s. Run it on the board with:

  sha256sum -c SHA256SUMS
  chmod 0755 opencv_board_smoke run.sh
  sha256sum -c SHA256SUMS
  sh run.sh

The program writes opencv_smoke.png in the package directory.
README

(
  cd "$PACKAGE"
  find opencv_board_smoke run.sh README.txt lib -type f -print0 |
    sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS
)

for existing in "$SHARED"/*; do
  [[ -e "$existing" ]] || continue
  case "$(basename "$existing")" in
    opencv_board_smoke|run.sh|README.txt|SHA256SUMS|lib) ;;
    *) echo "unexpected existing shared entry: $existing" >&2; exit 1 ;;
  esac
done
mkdir -p "$SHARED/lib"
cp -p "$PACKAGE/opencv_board_smoke" "$PACKAGE/run.sh" "$PACKAGE/README.txt" "$PACKAGE/SHA256SUMS" "$SHARED/"
cp -p "$PACKAGE"/lib/* "$SHARED/lib/"
(
  cd "$SHARED"
  sha256sum -c SHA256SUMS
)

echo "package=$PACKAGE"
echo "shared_package=$SHARED"
echo 'build_status=PASS'
REMOTE
