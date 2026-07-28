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
VM_SSH="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
NCNN_SOURCE="${NCNN_SOURCE:-/home/dministrator/src/ncnn-20240410}"
NCNN_REVISION="56775de50990ab7f16627efdcf5529b49541206f"
NCNN_REMOTE="https://github.com/Tencent/ncnn.git"
SHARED_LOCAL="${ANLOGIC_OPENMP_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_threading_task018_openmp}"
SHARED_VM="${ANLOGIC_OPENMP_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/edgeai_arm_threading_task018_openmp}"
VM_ROOT="/home/uisrc/build/ncnn-aarch64-openmp"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
LOCAL_NCNN_ARCHIVE="/tmp/ncnn-20240410-56775de-openmp.tar.gz"
LOCAL_PROJECT_ARCHIVE="/tmp/edgeai-task018-openmp-source.tar.gz"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_threading_openmp"

[[ -x "$VM_SSH" ]] || {
  printf 'VM SSH wrapper is missing or not executable: %s\n' "$VM_SSH" >&2
  exit 1
}
[[ -d "$NCNN_SOURCE/.git" ]] || {
  printf 'ncnn source is missing: %s\n' "$NCNN_SOURCE" >&2
  exit 1
}

actual_revision="$(git -C "$NCNN_SOURCE" rev-parse HEAD)"
actual_remote="$(git -C "$NCNN_SOURCE" remote get-url origin)"
[[ "$actual_revision" == "$NCNN_REVISION" ]] || {
  printf 'ncnn revision mismatch: %s\n' "$actual_revision" >&2
  exit 1
}
[[ "$actual_remote" == "$NCNN_REMOTE" ]] || {
  printf 'ncnn remote mismatch: %s\n' "$actual_remote" >&2
  exit 1
}
git -C "$NCNN_SOURCE" tag --points-at HEAD | grep -Fxq 20240410 || {
  printf 'ncnn tag 20240410 does not point at the frozen revision\n' >&2
  exit 1
}

printf 'mode=%s\n' "$MODE"
printf 'ncnn_remote=%s\n' "$actual_remote"
printf 'ncnn_revision=%s\n' "$actual_revision"
printf 'vm_build_root=%s\n' "$VM_ROOT"

"$VM_SSH" 'bash -s' <<'REMOTE'
set -euo pipefail
CMAKE=/home/uisrc/.local/cmake-3.16.9/bin/cmake
GCC=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-gcc
GXX=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
test -x "$CMAKE"
test -x "$GCC"
test -x "$GXX"
test -d /home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/aarch64-linux-gnu/libc
test -f /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/cmake/opencv4/OpenCVConfig.cmake
"$CMAKE" --version | head -1
"$GXX" --version | head -1
"$GXX" -dumpmachine
gomp=$("$GXX" -print-file-name=libgomp.so.1)
test "$gomp" != libgomp.so.1
test -f "$gomp"
file -L "$gomp"
readelf -h "$gomp" | grep -q 'Machine:.*AArch64'
REMOTE

if [[ "$MODE" == "--check" ]]; then
  printf 'openmp_build_check=PASS\n'
  exit 0
fi

git -C "$NCNN_SOURCE" archive \
  --format=tar.gz \
  --prefix=ncnn-20240410/ \
  -o "$LOCAL_NCNN_ARCHIVE.part" \
  "$NCNN_REVISION"
mv "$LOCAL_NCNN_ARCHIVE.part" "$LOCAL_NCNN_ARCHIVE"

tar \
  --sort=name \
  --mtime='UTC 1970-01-01' \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  -czf "$LOCAL_PROJECT_ARCHIVE.part" \
  -C "$REPO_ROOT" \
  cpp \
  configs/toolchains/anlogic-dr1-aarch64.cmake
mv "$LOCAL_PROJECT_ARCHIVE.part" "$LOCAL_PROJECT_ARCHIVE"

ncnn_sha256="$(sha256sum "$LOCAL_NCNN_ARCHIVE" | awk '{print $1}')"
project_sha256="$(sha256sum "$LOCAL_PROJECT_ARCHIVE" | awk '{print $1}')"
mkdir -p "$SHARED_LOCAL" "$LOG_DIR"
cp "$LOCAL_NCNN_ARCHIVE" "$SHARED_LOCAL/ncnn-source-$ncnn_sha256.tar.gz"
cp "$LOCAL_PROJECT_ARCHIVE" "$SHARED_LOCAL/project-source-$project_sha256.tar.gz"

"$VM_SSH" 'bash -s -- '"$ncnn_sha256"' '"$project_sha256"' '"$SHARED_VM" "$VM_ROOT" "$VM_CMAKE" "$VM_OPENCV_ROOT" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/openmp_build.log"
set -euo pipefail

ncnn_sha256=$1
project_sha256=$2
shared_root=$3
root=$4
cmake_bin=$5
opencv_root=$6
toolchain_root=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
gxx=$toolchain_root/bin/aarch64-linux-gnu-g++
sysroot=$toolchain_root/aarch64-linux-gnu/libc
ncnn_archive=$shared_root/ncnn-source-$ncnn_sha256.tar.gz
project_archive=$shared_root/project-source-$project_sha256.tar.gz
ncnn_source=$root/source-$ncnn_sha256
ncnn_build=$root/build-libgomp-$ncnn_sha256
ncnn_install=$root/install-libgomp-$ncnn_sha256
project_source=$root/project-source-$project_sha256
project_build=$root/project-build-libgomp-$project_sha256
log_dir=$root/logs-libgomp-$project_sha256
export_dir=$shared_root/build-output-libgomp-$project_sha256

test "$(sha256sum "$ncnn_archive" | awk '{print $1}')" = "$ncnn_sha256"
test "$(sha256sum "$project_archive" | awk '{print $1}')" = "$project_sha256"
test -x "$cmake_bin"
test -x "$gxx"
test -d "$sysroot"

mkdir -p "$root" "$log_dir"
if [[ ! -f "$ncnn_source/.source_sha256" ]]; then
  mkdir -p "$ncnn_source"
  tar -xzf "$ncnn_archive" -C "$ncnn_source" --strip-components=1
  printf '%s\n' "$ncnn_sha256" > "$ncnn_source/.source_sha256"
fi
if [[ ! -f "$project_source/.source_sha256" ]]; then
  mkdir -p "$project_source"
  tar -xzf "$project_archive" -C "$project_source"
  printf '%s\n' "$project_sha256" > "$project_source/.source_sha256"
fi
test "$(cat "$ncnn_source/.source_sha256")" = "$ncnn_sha256"
test "$(cat "$project_source/.source_sha256")" = "$project_sha256"

"$cmake_bin" \
  -S "$ncnn_source" \
  -B "$ncnn_build" \
  -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE="$project_source/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_INSTALL_PREFIX="$ncnn_install" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DNCNN_VERSION=20240410 \
  -DNCNN_SHARED_LIB=OFF \
  -DNCNN_VULKAN=OFF \
  -DNCNN_PYTHON=OFF \
  -DNCNN_BUILD_TOOLS=OFF \
  -DNCNN_BUILD_EXAMPLES=OFF \
  -DNCNN_BUILD_BENCHMARK=OFF \
  -DNCNN_BUILD_TESTS=OFF \
  -DNCNN_OPENMP=ON \
  -DNCNN_THREADS=ON \
  -DNCNN_SIMPLEOMP=OFF \
  -DNCNN_RUNTIME_CPU=ON \
  -DNCNN_INT8=OFF \
  -DNCNN_BF16=ON \
  -DNCNN_ARM82=OFF \
  > "$log_dir/ncnn_configure.log" 2>&1

printf 'openmp_build_stage=verify_configure\n'
grep -Fxq 'NCNN_OPENMP:BOOL=ON' "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=NCNN_OPENMP\n' >&2
  exit 1
}
grep -Fxq 'NCNN_THREADS:BOOL=ON' "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=NCNN_THREADS\n' >&2
  exit 1
}
grep -Fxq 'NCNN_SIMPLEOMP:BOOL=OFF' "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=NCNN_SIMPLEOMP\n' >&2
  exit 1
}
grep -Fxq 'OpenMP_COMPILE_RESULT_CXX_fopenmp:INTERNAL=TRUE' \
  "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=OpenMP_COMPILE_RESULT_CXX_fopenmp\n' >&2
  exit 1
}
grep -Fxq 'OpenMP_CXX_FLAGS:STRING=-fopenmp' "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=OpenMP_CXX_FLAGS\n' >&2
  exit 1
}
grep -Eq '^OpenMP_gomp_LIBRARY:FILEPATH=.+libgomp\.so$' "$ncnn_build/CMakeCache.txt" || {
  printf 'openmp_build_assertion=OpenMP_gomp_LIBRARY\n' >&2
  exit 1
}
grep -Eq '(^| )-fopenmp( |$)' "$ncnn_build/compile_commands.json" || {
  printf 'openmp_build_assertion=compile_commands_fopenmp\n' >&2
  exit 1
}

printf 'openmp_build_stage=build_ncnn\n'
"$cmake_bin" --build "$ncnn_build" --parallel 2 \
  > "$log_dir/ncnn_build.log" 2>&1
printf 'openmp_build_stage=install_ncnn\n'
"$cmake_bin" --install "$ncnn_build" \
  > "$log_dir/ncnn_install.log" 2>&1

printf 'openmp_build_stage=configure_project\n'
"$cmake_bin" \
  -S "$project_source/cpp" \
  -B "$project_build" \
  -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE="$project_source/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_BUILD_TYPE=Release \
  -DEDGEAI_ENABLE_ORT=OFF \
  -DEDGEAI_ENABLE_NCNN=ON \
  -DEDGEAI_ENABLE_VIDEO=OFF \
  -DEDGEAI_OPENCV_ROOT="$opencv_root" \
  -DNCNN_ROOT="$ncnn_install" \
  > "$log_dir/project_configure.log" 2>&1
printf 'openmp_build_stage=build_project\n'
"$cmake_bin" --build "$project_build" \
  --target edgeai_benchmark_ncnn -- -j2 \
  > "$log_dir/project_build.log" 2>&1

application=$project_build/edgeai_benchmark_ncnn
gomp_path=$("$gxx" -print-file-name=libgomp.so.1)
gomp_real=$(readlink -f "$gomp_path")
test -x "$application"
test -f "$ncnn_install/lib/libncnn.a"
test -f "$gomp_real"

file "$application" | tee "$log_dir/benchmark.file.txt"
readelf -hW "$application" > "$log_dir/benchmark.readelf-h.txt"
readelf -lW "$application" > "$log_dir/benchmark.readelf-l.txt"
readelf -dW "$application" > "$log_dir/benchmark.readelf-d.txt"
readelf -VW "$application" > "$log_dir/benchmark.readelf-v.txt"
readelf -hW "$gomp_real" > "$log_dir/libgomp.readelf-h.txt"
readelf -dW "$gomp_real" > "$log_dir/libgomp.readelf-d.txt"
readelf -VW "$gomp_real" > "$log_dir/libgomp.readelf-v.txt"
grep -q 'Machine:.*AArch64' "$log_dir/benchmark.readelf-h.txt"
grep -Fq '/lib/ld-linux-aarch64.so.1' "$log_dir/benchmark.readelf-l.txt"
grep -Fq 'Shared library: [libgomp.so.1]' "$log_dir/benchmark.readelf-d.txt"
grep -q 'Machine:.*AArch64' "$log_dir/libgomp.readelf-h.txt"

printf 'openmp_build_stage=export\n'
mkdir -p "$export_dir/bin" "$export_dir/lib" "$export_dir/provenance"
cp "$application" "$export_dir/bin/edgeai_benchmark_ncnn"
cp -L "$opencv_root/lib/libopencv_core.so.407" "$export_dir/lib/libopencv_core.so.407"
cp -L "$opencv_root/lib/libopencv_imgproc.so.407" "$export_dir/lib/libopencv_imgproc.so.407"
cp -L "$opencv_root/lib/libopencv_imgcodecs.so.407" "$export_dir/lib/libopencv_imgcodecs.so.407"
cp -L "$gomp_real" "$export_dir/lib/libgomp.so.1"
cp "$ncnn_build/CMakeCache.txt" "$export_dir/provenance/ncnn_CMakeCache.txt"
cp "$ncnn_build/compile_commands.json" "$export_dir/provenance/ncnn_compile_commands.json"
cp "$ncnn_install/include/ncnn/platform.h" "$export_dir/provenance/ncnn_platform.h"
cp "$ncnn_install/lib/cmake/ncnn/ncnnConfig.cmake" "$export_dir/provenance/ncnnConfig.cmake"
cp "$project_build/CMakeFiles/edgeai_benchmark_ncnn.dir/link.txt" \
  "$export_dir/provenance/benchmark_link.txt"
cp "$log_dir/"*.txt "$export_dir/provenance/"

(
  cd "$export_dir"
  find bin lib -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS
)

{
  printf 'backend=standard_libgomp\n'
  printf 'ncnn_source_archive_sha256=%s\n' "$ncnn_sha256"
  printf 'project_source_archive_sha256=%s\n' "$project_sha256"
  printf 'ncnn_options=NCNN_OPENMP=ON NCNN_THREADS=ON NCNN_SIMPLEOMP=OFF\n'
  printf 'ncnn_library_sha256=%s\n' "$(sha256sum "$ncnn_install/lib/libncnn.a" | awk '{print $1}')"
  printf 'libgomp_sha256=%s\n' "$(sha256sum "$gomp_real" | awk '{print $1}')"
  printf 'benchmark_elf_sha256=%s\n' "$(sha256sum "$application" | awk '{print $1}')"
  printf 'cmake=%s\n' "$("$cmake_bin" --version | head -1)"
  printf 'compiler=%s\n' "$("$gxx" --version | head -1)"
  printf 'ncnn_install=%s\n' "$ncnn_install"
  printf 'project_build=%s\n' "$project_build"
  printf 'status=PASS\n'
} > "$export_dir/build_summary.txt"
cat "$export_dir/build_summary.txt"
cat "$export_dir/SHA256SUMS"
REMOTE

printf 'ncnn_source_archive_sha256=%s\n' "$ncnn_sha256"
printf 'project_source_archive_sha256=%s\n' "$project_sha256"
printf 'shared_build_output=%s/build-output-libgomp-%s\n' \
  "$SHARED_LOCAL" "$project_sha256"
