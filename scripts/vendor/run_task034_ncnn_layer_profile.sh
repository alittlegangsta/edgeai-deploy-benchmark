#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check|--execute) MODE="$1" ;;
    *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VM_SSH="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/task034-ncnn-optimization}"
SHARED_VM="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/task034-ncnn-optimization}"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
VM_TOOLCHAIN="/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0"
VM_BUILD_ROOT="/home/uisrc/build/edgeai-task034-ncnn-optimization"
NCNN_SOURCE="/home/dministrator/src/ncnn-20240410"
NCNN_COMMIT="56775de50990ab7f16627efdcf5529b49541206f"
EXPECTED_PARAM="72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
EXPECTED_BIN="658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
EXPECTED_INPUT="625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
EXPECTED_GOLDEN="fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9"
EXPECTED_LIBGOMP="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"

[[ -x "$VM_SSH" ]] || { printf 'VM SSH wrapper is not executable: %s\n' "$VM_SSH" >&2; exit 1; }
[[ -d "$NCNN_SOURCE/.git" ]] || { printf 'ncnn source checkout is missing: %s\n' "$NCNN_SOURCE" >&2; exit 1; }
for required in \
  "$REPO_ROOT/cpp/CMakeLists.txt" \
  "$REPO_ROOT/cpp/apps/arm_cpu_profiler.cpp" \
  "$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  "$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param" \
  "$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin"; do
  [[ -f "$required" ]] || { printf 'required source is missing: %s\n' "$required" >&2; exit 1; }
done

if [[ "$MODE" == "--check" ]]; then
  git -C "$NCNN_SOURCE" rev-parse HEAD | grep -Fx "$NCNN_COMMIT"
  git -C "$NCNN_SOURCE" show -s --format='%H %D %s' "$NCNN_COMMIT"
  sha256sum "$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param" \
    "$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin" \
    "$REPO_ROOT/data/samples/images/pc_reference.jpg" \
    "$REPO_ROOT/results/acceptance/cpp_ncnn_reference.json"
  "$VM_SSH" bash -s -- "$VM_CMAKE" "$VM_TOOLCHAIN" "$VM_OPENCV_ROOT" "$EXPECTED_LIBGOMP" <<'REMOTE'
set -euo pipefail
cmake=$1
toolchain=$2
opencv=$3
expected_gomp=$4
test -x "$cmake"
test -x "$toolchain/bin/aarch64-linux-gnu-g++"
test -f "$opencv/lib/cmake/opencv4/OpenCVConfig.cmake"
gomp=$(readlink -f "$($toolchain/bin/aarch64-linux-gnu-g++ -print-file-name=libgomp.so.1)")
test -f "$gomp"
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"
printf 'cmake=%s\n' "$($cmake --version | head -1)"
printf 'compiler=%s\n' "$($toolchain/bin/aarch64-linux-gnu-g++ --version | head -1)"
printf 'libgomp=%s\n' "$gomp"
printf 'task034_vm_check=PASS\n'
REMOTE
  exit 0
fi

mkdir -p "$SHARED_LOCAL"
NCNN_ARCHIVE="/tmp/task034-ncnn-${NCNN_COMMIT}.tar.gz"
PROJECT_ARCHIVE="/tmp/task034-project-${NCNN_COMMIT}.tar.gz"
git -C "$NCNN_SOURCE" archive --format=tar --prefix=ncnn-20240410/ "$NCNN_COMMIT" | gzip -n > "$NCNN_ARCHIVE"
tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  -czf "$PROJECT_ARCHIVE" -C "$REPO_ROOT" cpp configs/toolchains/anlogic-dr1-aarch64.cmake
cp "$NCNN_ARCHIVE" "$SHARED_LOCAL/ncnn-source.tar.gz"
cp "$PROJECT_ARCHIVE" "$SHARED_LOCAL/project-source.tar.gz"
ncnn_archive_sha256="$(sha256sum "$NCNN_ARCHIVE" | awk '{print $1}')"
ncnn_archive_size="$(stat -c '%s' "$NCNN_ARCHIVE")"
project_archive_sha256="$(sha256sum "$PROJECT_ARCHIVE" | awk '{print $1}')"
project_archive_size="$(stat -c '%s' "$PROJECT_ARCHIVE")"

"$VM_SSH" bash -s -- \
  "$SHARED_VM" "$VM_BUILD_ROOT" "$VM_CMAKE" "$VM_OPENCV_ROOT" "$VM_TOOLCHAIN" \
  "$ncnn_archive_sha256" "$ncnn_archive_size" "$project_archive_sha256" "$project_archive_size" \
  "$NCNN_COMMIT" "$EXPECTED_LIBGOMP" <<'REMOTE'
set -euo pipefail
shared=$1
build_root=$2
cmake=$3
opencv=$4
toolchain_root=$5
ncnn_sha=$6
ncnn_size=$7
project_sha=$8
project_size=$9
ncnn_commit=${10}
expected_gomp=${11}
ncnn_archive="$shared/ncnn-source.tar.gz"
project_archive="$shared/project-source.tar.gz"
test "$(stat -c '%s' "$ncnn_archive")" = "$ncnn_size"
test "$(sha256sum "$ncnn_archive" | awk '{print $1}')" = "$ncnn_sha"
test "$(stat -c '%s' "$project_archive")" = "$project_size"
test "$(sha256sum "$project_archive" | awk '{print $1}')" = "$project_sha"
mkdir -p "$build_root" "$shared/build-output"
ncnn_source="$build_root/ncnn-source-$ncnn_sha"
project_source="$build_root/project-source-$project_sha"
if [ ! -f "$ncnn_source/.archive_sha256" ]; then
  mkdir -p "$ncnn_source"
  tar -xzf "$ncnn_archive" -C "$ncnn_source"
  printf '%s\n' "$ncnn_sha" > "$ncnn_source/.archive_sha256"
fi
if [ ! -f "$project_source/.archive_sha256" ]; then
  mkdir -p "$project_source"
  tar -xzf "$project_archive" -C "$project_source"
  printf '%s\n' "$project_sha" > "$project_source/.archive_sha256"
fi
test "$(cat "$ncnn_source/.archive_sha256")" = "$ncnn_sha"
test "$(cat "$project_source/.archive_sha256")" = "$project_sha"
ncnn_source="$ncnn_source/ncnn-20240410"
gxx="$toolchain_root/bin/aarch64-linux-gnu-g++"
gomp=$(readlink -f "$($gxx -print-file-name=libgomp.so.1)")
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"

configure_ncnn() {
  name=$1
  benchmark=$2
  extra_flags=$3
  source_dir="$build_root/ncnn-$name-$ncnn_sha"
  build_dir="$build_root/ncnn-build-$name-$ncnn_sha"
  install_dir="$build_root/ncnn-install-$name-$ncnn_sha"
  log_dir="$build_root/ncnn-logs-$name-$ncnn_sha"
  mkdir -p "$source_dir"
  mkdir -p "$log_dir"
  if [ ! -f "$source_dir/.source_sha256" ]; then
    cp -a "$ncnn_source/." "$source_dir/"
    printf '%s\n' "$ncnn_sha" > "$source_dir/.source_sha256"
  fi
  test "$(cat "$source_dir/.source_sha256")" = "$ncnn_sha"
  "$cmake" -S "$source_dir" -B "$build_dir" \
    -DCMAKE_TOOLCHAIN_FILE="$project_source/configs/toolchains/anlogic-dr1-aarch64.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$install_dir" \
    -DNCNN_VERSION=20240410 \
    -DNCNN_SHARED_LIB=OFF -DNCNN_OPENMP=ON -DNCNN_SIMPLEOMP=OFF -DNCNN_THREADS=ON \
    -DNCNN_RUNTIME_CPU=ON -DNCNN_BENCHMARK="$benchmark" -DNCNN_VULKAN=OFF \
    -DNCNN_INT8=OFF -DNCNN_BF16=ON -DNCNN_FORCE_INLINE=ON -DNCNN_ENABLE_LTO=OFF \
    -DNCNN_ARM82=OFF -DNCNN_VFPV4=ON -DNCNN_GNU_INLINE_ASM=ON \
    -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG $extra_flags" \
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG $extra_flags" \
    > "$log_dir/configure.log" 2>&1
  "$cmake" --build "$build_dir" --target install -- -j2 \
    > "$log_dir/build.log" 2>&1
  printf '%s\n' "$install_dir"
}

profile_root=$(configure_ncnn profiling ON "")
candidate_a_root=$(configure_ncnn candidate-a OFF "")
candidate_b_root=$(configure_ncnn candidate-b2 OFF "-mtune=cortex-a35")

build_project() {
  name=$1
  ncnn_root=$2
  build_dir="$build_root/project-build-$name-$project_sha"
  log_dir="$build_root/project-logs-$name-$project_sha"
  mkdir -p "$log_dir"
  "$cmake" -S "$project_source/cpp" -B "$build_dir" \
    -DCMAKE_TOOLCHAIN_FILE="$project_source/configs/toolchains/anlogic-dr1-aarch64.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DEDGEAI_ENABLE_ORT=OFF -DEDGEAI_ENABLE_NCNN=ON \
    -DEDGEAI_ENABLE_VIDEO=OFF -DEDGEAI_OPENCV_ROOT="$opencv" -DNCNN_ROOT="$ncnn_root" \
    -DEDGEAI_NCNN_LIBRARY_SHA256="$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" \
    -DEDGEAI_PRIVATE_LIBGOMP_SHA256="$expected_gomp" > "$log_dir/configure.log" 2>&1
  "$cmake" --build "$build_dir" --target edgeai_arm_cpu_profiler edgeai_arm_cpu_profiler_tests -- -j2 > "$log_dir/build.log" 2>&1
  test -x "$build_dir/edgeai_arm_cpu_profiler"
  test -x "$build_dir/edgeai_arm_cpu_profiler_tests"
  cp "$build_dir/edgeai_arm_cpu_profiler" "$shared/build-output/edgeai_arm_cpu_profiler-$name"
  cp "$build_dir/edgeai_arm_cpu_profiler_tests" "$shared/build-output/edgeai_arm_cpu_profiler_tests-$name"
  cp "$build_dir/CMakeCache.txt" "$shared/build-output/CMakeCache-$name.txt"
  cp "$log_dir/configure.log" "$shared/build-output/configure-$name.log"
  cp "$log_dir/build.log" "$shared/build-output/build-$name.log"
  file "$build_dir/edgeai_arm_cpu_profiler" > "$shared/build-output/file-$name.txt"
  readelf -h "$build_dir/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-h-$name.txt"
  readelf -lW "$build_dir/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-l-$name.txt"
  readelf -dW "$build_dir/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-d-$name.txt"
  sha256sum "$build_dir/edgeai_arm_cpu_profiler" > "$shared/build-output/sha256-$name.txt"
}

build_project profiling "$profile_root"
build_project candidate-a "$candidate_a_root"
build_project candidate-b "$candidate_b_root"

cat > "$shared/build-output/build_identity.json" <<IDENTITY
{
  "schema_version": 1,
  "task": "034",
  "ncnn_source_commit": "$ncnn_commit",
  "ncnn_source_archive_sha256": "$ncnn_sha",
  "project_source_archive_sha256": "$project_sha",
  "compiler": "$($gxx --version | head -1)",
  "cmake": "$($cmake --version | head -1)",
  "options": {
    "NCNN_OPENMP": true,
    "NCNN_THREADS": true,
    "NCNN_SIMPLEOMP": false,
    "NCNN_RUNTIME_CPU": true,
    "NCNN_INT8": false,
    "NCNN_BF16": true,
    "NCNN_FORCE_INLINE": true,
    "NCNN_ENABLE_LTO": false,
    "release": true
  },
  "candidate_flags": {"A": "-O3 -DNDEBUG", "B": "-O3 -DNDEBUG -mtune=cortex-a35"},
  "libgomp_sha256": "$expected_gomp"
}
IDENTITY
(
  cd "$shared/build-output"
  find . -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > BUILD_OUTPUT_SHA256SUMS
)
printf 'task034_vm_build=PASS\n'
printf 'source_archive_sha256=%s\n' "$ncnn_sha"
printf 'project_archive_sha256=%s\n' "$project_sha"
printf 'build_output=%s\n' "$shared/build-output"
REMOTE

printf 'task034_shared_build_output=%s\n' "$SHARED_LOCAL/build-output"
