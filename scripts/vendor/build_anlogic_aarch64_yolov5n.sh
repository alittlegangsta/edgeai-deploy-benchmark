#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
RUNTIME_PROFILE="baseline-single-thread"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --check|--execute)
      MODE="$1"
      ;;
    --runtime-profile)
      [[ "$#" -ge 2 ]] || { printf 'missing --runtime-profile value\n' >&2; exit 2; }
      RUNTIME_PROFILE="$2"
      shift
      ;;
    *)
      printf 'usage: %s [--check|--execute] [--runtime-profile baseline-single-thread|recommended-dual-thread]\n' "$0" >&2
      exit 2
      ;;
  esac
  shift
done

case "$RUNTIME_PROFILE" in
  baseline-single-thread)
    VM_NCNN_ROOT="/home/uisrc/build/ncnn-aarch64/install"
    EXPECTED_NCNN_SHA256="5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a"
    EXPECTED_LIBGOMP_SHA256=""
    DEFAULT_SHARED_NAME="edgeai_arm_yolov5n"
    ;;
  recommended-dual-thread)
    VM_NCNN_ROOT="/home/uisrc/build/ncnn-aarch64-openmp/install-libgomp-81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45"
    EXPECTED_NCNN_SHA256="bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
    EXPECTED_LIBGOMP_SHA256="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"
    DEFAULT_SHARED_NAME="edgeai_arm_runtime_profiles/recommended-dual-thread"
    ;;
  *)
    printf 'unknown runtime profile: %s\n' "$RUNTIME_PROFILE" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VM_SSH="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/$DEFAULT_SHARED_NAME}"
SHARED_VM="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/$DEFAULT_SHARED_NAME}"
LOCAL_ARCHIVE="/tmp/edgeai-task014-source.tar.gz"
SHARED_ARCHIVE="$SHARED_LOCAL/edgeai-task014-source.tar.gz"
VM_BUILD_ROOT="/home/uisrc/build/edgeai-arm-yolov5n-$RUNTIME_PROFILE"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_yolov5n"

[[ -x "$VM_SSH" ]] || {
  printf 'VM SSH wrapper is not executable: %s\n' "$VM_SSH" >&2
  exit 1
}
for required in \
  "$REPO_ROOT/cpp/CMakeLists.txt" \
  "$REPO_ROOT/cpp/apps/ncnn_image.cpp" \
  "$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  "$REPO_ROOT/configs/runtime_profiles/anlogic-dr1-$RUNTIME_PROFILE.json"; do
  [[ -f "$required" ]] || {
    printf 'required source is missing: %s\n' "$required" >&2
    exit 1
  }
done

mkdir -p "$LOG_DIR"

if [[ "$MODE" == "--check" ]]; then
  "$VM_SSH" 'bash -s -- '"$RUNTIME_PROFILE"' '"$VM_NCNN_ROOT"' '"$EXPECTED_NCNN_SHA256"' '"$EXPECTED_LIBGOMP_SHA256" <<'REMOTE' | tee "$LOG_DIR/arm_yolov5n_build_check.log"
set -euo pipefail
profile=$1
ncnn_root=$2
expected_ncnn=$3
expected_gomp=$4
for required in \
  /home/uisrc/.local/cmake-3.16.9/bin/cmake \
  "$ncnn_root/lib/libncnn.a" \
  "$ncnn_root/lib/cmake/ncnn/ncnnConfig.cmake" \
  /home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++ \
  /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/cmake/opencv4/OpenCVConfig.cmake \
  /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/libopencv_core.so.4.7.0 \
  /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/libopencv_imgproc.so.4.7.0 \
  /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/libopencv_imgcodecs.so.4.7.0; do
  test -f "$required"
  printf 'present=%s\n' "$required"
done
/home/uisrc/.local/cmake-3.16.9/bin/cmake --version
/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++ --version | head -1
file /home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64/lib/libopencv_core.so.4.7.0
test "$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" = "$expected_ncnn"
if [ "$profile" = recommended-dual-thread ]; then
  gomp=$(/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++ -print-file-name=libgomp.so.1)
  test -f "$gomp"
  test "$(sha256sum "$(readlink -f "$gomp")" | awk '{print $1}')" = "$expected_gomp"
  file -L "$gomp"
fi
sha256sum "$ncnn_root/lib/libncnn.a"
printf 'runtime_profile=%s\n' "$profile"
REMOTE
  exit 0
fi

tar \
  --sort=name \
  --mtime='UTC 1970-01-01' \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  -czf "$LOCAL_ARCHIVE" \
  -C "$REPO_ROOT" \
  cpp \
  configs/toolchains/anlogic-dr1-aarch64.cmake \
  "configs/runtime_profiles/anlogic-dr1-$RUNTIME_PROFILE.json"

source_sha256="$(sha256sum "$LOCAL_ARCHIVE" | awk '{print $1}')"
source_size="$(stat -c '%s' "$LOCAL_ARCHIVE")"
mkdir -p "$SHARED_LOCAL"
cp "$LOCAL_ARCHIVE" "$SHARED_ARCHIVE"
test "$(sha256sum "$SHARED_ARCHIVE" | awk '{print $1}')" = "$source_sha256"

"$VM_SSH" 'bash -s -- '"$source_sha256"' '"$source_size"' '"$SHARED_VM" "$VM_BUILD_ROOT" "$VM_CMAKE" "$VM_NCNN_ROOT" "$VM_OPENCV_ROOT" "$RUNTIME_PROFILE" "$EXPECTED_NCNN_SHA256" "$EXPECTED_LIBGOMP_SHA256" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/arm_yolov5n_build.log"
set -euo pipefail

source_sha256=$1
source_size=$2
shared_root=$3
build_root=$4
cmake_bin=$5
ncnn_root=$6
opencv_root=$7
runtime_profile=$8
expected_ncnn=$9
expected_gomp=${10}
archive="$shared_root/edgeai-task014-source.tar.gz"
source_dir="$build_root/source-$source_sha256"
build_dir="$build_root/build-$source_sha256"
log_dir="$build_root/logs-$source_sha256"
export_dir="$shared_root/build-output"

test -f "$archive"
test "$(stat -c '%s' "$archive")" = "$source_size"
test "$(sha256sum "$archive" | awk '{print $1}')" = "$source_sha256"
test -x "$cmake_bin"
test -f "$ncnn_root/lib/libncnn.a"
test -f "$opencv_root/lib/cmake/opencv4/OpenCVConfig.cmake"
test "$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" = "$expected_ncnn"

gomp_real=
if [ "$runtime_profile" = recommended-dual-thread ]; then
  gxx=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
  gomp_real=$(readlink -f "$("$gxx" -print-file-name=libgomp.so.1)")
  test -f "$gomp_real"
  test "$(sha256sum "$gomp_real" | awk '{print $1}')" = "$expected_gomp"
fi

mkdir -p "$source_dir" "$build_dir" "$log_dir" "$export_dir/lib"
if [[ ! -f "$source_dir/.source_sha256" ]]; then
  tar -xzf "$archive" -C "$source_dir"
  printf '%s\n' "$source_sha256" > "$source_dir/.source_sha256"
fi
test "$(cat "$source_dir/.source_sha256")" = "$source_sha256"

toolchain="$source_dir/configs/toolchains/anlogic-dr1-aarch64.cmake"
source_cpp="$source_dir/cpp"

"$cmake_bin" \
  -S "$source_cpp" \
  -B "$build_dir" \
  -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
  -DCMAKE_BUILD_TYPE=Release \
  -DEDGEAI_ENABLE_ORT=OFF \
  -DEDGEAI_ENABLE_NCNN=ON \
  -DEDGEAI_ENABLE_VIDEO=OFF \
  -DEDGEAI_OPENCV_ROOT="$opencv_root" \
  -DNCNN_ROOT="$ncnn_root" \
  -DEDGEAI_NCNN_LIBRARY_SHA256="$expected_ncnn" \
  -DEDGEAI_PRIVATE_LIBGOMP_SHA256="$expected_gomp" \
  2>&1 | tee "$log_dir/configure.log"

"$cmake_bin" --build "$build_dir" \
  --target edgeai_ncnn_image edgeai_benchmark_ncnn -- -j2 \
  2>&1 | tee "$log_dir/build.log"

application="$build_dir/edgeai_ncnn_image"
benchmark_application="$build_dir/edgeai_benchmark_ncnn"
test -x "$application"
test -x "$benchmark_application"
for artifact in "$application" "$benchmark_application"; do
  name=$(basename "$artifact")
  file "$artifact" | tee "$log_dir/$name.file.txt"
  readelf -h "$artifact" > "$log_dir/$name.readelf-h.txt"
  readelf -lW "$artifact" > "$log_dir/$name.readelf-l.txt"
  readelf -dW "$artifact" > "$log_dir/$name.readelf-d.txt"
  readelf -AW "$artifact" > "$log_dir/$name.readelf-a.txt"
  readelf -VW "$artifact" > "$log_dir/$name.readelf-v.txt"
  sha256sum "$artifact" | tee "$log_dir/$name.sha256"
  grep -Fq 'ELF 64-bit' "$log_dir/$name.file.txt"
  grep -Eq 'ARM aarch64|AArch64' "$log_dir/$name.file.txt"
  grep -Fq '/lib/ld-linux-aarch64.so.1' "$log_dir/$name.readelf-l.txt"
  if grep -Eiq 'vulkan|python' "$log_dir/$name.readelf-d.txt"; then
    echo "unexpected runtime dependency found in $name" >&2
    exit 1
  fi
  if [ "$runtime_profile" = recommended-dual-thread ]; then
    grep -Fq 'Shared library: [libgomp.so.1]' "$log_dir/$name.readelf-d.txt"
  elif grep -Fq 'Shared library: [libgomp.so.1]' "$log_dir/$name.readelf-d.txt"; then
    echo "baseline profile unexpectedly depends on libgomp" >&2
    exit 1
  fi
done

cp "$application" "$export_dir/edgeai_ncnn_image"
cp "$benchmark_application" "$export_dir/edgeai_benchmark_ncnn"
cp -L "$opencv_root/lib/libopencv_core.so.407" "$export_dir/lib/libopencv_core.so.407"
cp -L "$opencv_root/lib/libopencv_imgproc.so.407" "$export_dir/lib/libopencv_imgproc.so.407"
cp -L "$opencv_root/lib/libopencv_imgcodecs.so.407" "$export_dir/lib/libopencv_imgcodecs.so.407"
if [ "$runtime_profile" = recommended-dual-thread ]; then
  cp -L "$gomp_real" "$export_dir/lib/libgomp.so.1"
fi

application_sha256=$(sha256sum "$application" | awk '{print $1}')
cat > "$export_dir/runtime_build_identity.json" <<IDENTITY
{
  "schema_version": 1,
  "runtime_profile": "$runtime_profile",
  "NCNN_OPENMP": $([ "$runtime_profile" = recommended-dual-thread ] && printf true || printf false),
  "NCNN_THREADS": true,
  "NCNN_SIMPLEOMP": false,
  "effective_parallel_backend": "$([ "$runtime_profile" = recommended-dual-thread ] && printf openmp || printf none)",
  "libncnn_a_sha256": "$expected_ncnn",
  "private_libgomp_so_1_sha256": $([ -n "$expected_gomp" ] && printf '"%s"' "$expected_gomp" || printf null),
  "executable_sha256": "$application_sha256"
}
IDENTITY

(
  cd "$export_dir"
  find edgeai_ncnn_image edgeai_benchmark_ncnn runtime_build_identity.json lib \
    -type f -print0 | sort -z | xargs -0 sha256sum > BUILD_OUTPUT_SHA256SUMS
)

{
  echo "source_archive_sha256=$source_sha256"
  echo "runtime_profile=$runtime_profile"
  echo "cmake_version=$("$cmake_bin" --version | head -1)"
  echo "compiler=$(/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++ --version | head -1)"
  echo "ncnn_library_sha256=$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')"
  echo "application_sha256=$application_sha256"
  echo "benchmark_application_sha256=$(sha256sum "$benchmark_application" | awk '{print $1}')"
  echo "application=$application"
  echo "build_dir=$build_dir"
  echo "opencv_root=$opencv_root"
  echo "status=PASS"
} > "$export_dir/build_summary.txt"
cat "$export_dir/build_summary.txt"
cat "$export_dir/BUILD_OUTPUT_SHA256SUMS"
REMOTE

printf 'source_archive=%s\n' "$LOCAL_ARCHIVE"
printf 'source_archive_sha256=%s\n' "$source_sha256"
printf 'shared_build_output=%s\n' "$SHARED_LOCAL/build-output"
