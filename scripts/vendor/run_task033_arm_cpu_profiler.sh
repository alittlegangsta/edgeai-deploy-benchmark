#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --check|--execute) MODE="$1" ;;
    *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VM_SSH="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/task033-arm-cpu-profiler}"
SHARED_VM="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/task033-arm-cpu-profiler}"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_NCNN_ROOT="/home/uisrc/build/ncnn-aarch64-openmp/install-libgomp-81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
VM_TOOLCHAIN="/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0"
VM_BUILD_ROOT="/home/uisrc/build/edgeai-task033-arm-cpu-profiler"
EXPECTED_NCNN="bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
EXPECTED_GOMP="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"
ARCHIVE="/tmp/edgeai-task033-source.tar.gz"

[[ -x "$VM_SSH" ]] || { printf 'VM SSH wrapper is not executable: %s\n' "$VM_SSH" >&2; exit 1; }
for required in \
  "$REPO_ROOT/cpp/CMakeLists.txt" \
  "$REPO_ROOT/cpp/apps/arm_cpu_profiler.cpp" \
  "$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake"; do
  [[ -f "$required" ]] || { printf 'required source is missing: %s\n' "$required" >&2; exit 1; }
done

if [[ "$MODE" == "--check" ]]; then
  "$VM_SSH" bash -s -- "$VM_CMAKE" "$VM_NCNN_ROOT" "$VM_OPENCV_ROOT" "$VM_TOOLCHAIN" "$EXPECTED_NCNN" "$EXPECTED_GOMP" <<'REMOTE'
set -euo pipefail
cmake_bin=$1
ncnn_root=$2
opencv_root=$3
toolchain_root=$4
expected_ncnn=$5
expected_gomp=$6
for required in \
  "$cmake_bin" \
  "$ncnn_root/lib/libncnn.a" \
  "$ncnn_root/lib/cmake/ncnn/ncnnConfig.cmake" \
  "$opencv_root/lib/cmake/opencv4/OpenCVConfig.cmake" \
  "$toolchain_root/bin/aarch64-linux-gnu-g++"; do
  test -f "$required"
  printf 'present=%s\n' "$required"
done
test "$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" = "$expected_ncnn"
gxx="$toolchain_root/bin/aarch64-linux-gnu-g++"
gomp="$("$gxx" -print-file-name=libgomp.so.1)"
gomp="$(readlink -f "$gomp")"
test -f "$gomp"
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"
"$cmake_bin" --version | head -1
"$gxx" --version | head -1
file "$ncnn_root/lib/libncnn.a"
printf 'task033_build_check=PASS\n'
REMOTE
  exit 0
fi

tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  -czf "$ARCHIVE" -C "$REPO_ROOT" cpp configs/toolchains/anlogic-dr1-aarch64.cmake
source_sha256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
source_size="$(stat -c '%s' "$ARCHIVE")"
mkdir -p "$SHARED_LOCAL"
cp "$ARCHIVE" "$SHARED_LOCAL/edgeai-task033-source.tar.gz"

"$VM_SSH" bash -s -- "$SHARED_VM" "$source_sha256" "$source_size" "$VM_BUILD_ROOT" \
  "$VM_CMAKE" "$VM_NCNN_ROOT" "$VM_OPENCV_ROOT" "$VM_TOOLCHAIN" "$EXPECTED_NCNN" "$EXPECTED_GOMP" <<'REMOTE'
set -euo pipefail
shared=$1
source_sha256=$2
source_size=$3
build_root=$4
cmake_bin=$5
ncnn_root=$6
opencv_root=$7
toolchain_root=$8
expected_ncnn=$9
expected_gomp=${10}
archive="$shared/edgeai-task033-source.tar.gz"
source_dir="$build_root/source-$source_sha256"
build_dir="$build_root/build-$source_sha256"
output_dir="$shared/build-output"
log_dir="$build_root/logs-$source_sha256"
test -f "$archive"
test "$(stat -c '%s' "$archive")" = "$source_size"
test "$(sha256sum "$archive" | awk '{print $1}')" = "$source_sha256"
mkdir -p "$source_dir" "$build_dir" "$output_dir/lib" "$log_dir"
if [ ! -f "$source_dir/.source_sha256" ]; then
  tar -xzf "$archive" -C "$source_dir"
  printf '%s\n' "$source_sha256" > "$source_dir/.source_sha256"
fi
test "$(cat "$source_dir/.source_sha256")" = "$source_sha256"
"$cmake_bin" -S "$source_dir/cpp" -B "$build_dir" \
  -DCMAKE_TOOLCHAIN_FILE="$source_dir/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DEDGEAI_ENABLE_ORT=OFF -DEDGEAI_ENABLE_NCNN=ON \
  -DEDGEAI_ENABLE_VIDEO=OFF -DEDGEAI_OPENCV_ROOT="$opencv_root" -DNCNN_ROOT="$ncnn_root" \
  -DEDGEAI_NCNN_LIBRARY_SHA256="$expected_ncnn" \
  -DEDGEAI_PRIVATE_LIBGOMP_SHA256="$expected_gomp" 2>&1 | tee "$log_dir/configure.log"
"$cmake_bin" --build "$build_dir" --target edgeai_arm_cpu_profiler edgeai_arm_cpu_profiler_tests -- -j2 \
  2>&1 | tee "$log_dir/build.log"
profiler="$build_dir/edgeai_arm_cpu_profiler"
test -x "$profiler"
file "$profiler" | tee "$log_dir/profiler.file.txt"
readelf -h "$profiler" > "$log_dir/profiler.readelf-h.txt"
readelf -lW "$profiler" > "$log_dir/profiler.readelf-l.txt"
readelf -dW "$profiler" > "$log_dir/profiler.readelf-d.txt"
readelf -AW "$profiler" > "$log_dir/profiler.readelf-a.txt"
sha256sum "$profiler" | tee "$log_dir/profiler.sha256"
grep -Eq 'ARM aarch64|AArch64' "$log_dir/profiler.file.txt"
grep -Fq '/lib/ld-linux-aarch64.so.1' "$log_dir/profiler.readelf-l.txt"
grep -Fq 'Shared library: [libgomp.so.1]' "$log_dir/profiler.readelf-d.txt"
cp "$profiler" "$output_dir/edgeai_arm_cpu_profiler"
gxx="$toolchain_root/bin/aarch64-linux-gnu-g++"
gomp="$("$gxx" -print-file-name=libgomp.so.1)"
gomp="$(readlink -f "$gomp")"
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"
cp "$gomp" "$output_dir/lib/libgomp.so.1"
for library in libopencv_core.so.407 libopencv_imgproc.so.407 libopencv_imgcodecs.so.407; do
  cp -L "$opencv_root/lib/$library" "$output_dir/lib/$library"
done
printf '{"schema_version":1,"task":"033","source_archive_sha256":"%s","ncnn_library_sha256":"%s","private_libgomp_sha256":"%s","profiler_sha256":"%s"}\n' \
  "$source_sha256" "$expected_ncnn" "$expected_gomp" "$(sha256sum "$profiler" | awk '{print $1}')" > "$output_dir/build_identity.json"
(
  cd "$output_dir"
  find edgeai_arm_cpu_profiler build_identity.json lib -type f -print0 | sort -z | xargs -0 sha256sum > BUILD_OUTPUT_SHA256SUMS
)
cat "$log_dir/profiler.file.txt"
cat "$output_dir/BUILD_OUTPUT_SHA256SUMS"
printf 'task033_build=PASS\n'
REMOTE

printf 'task033_source_archive=%s\n' "$SHARED_LOCAL/edgeai-task033-source.tar.gz"
printf 'task033_shared_build_output=%s\n' "$SHARED_LOCAL/build-output"
