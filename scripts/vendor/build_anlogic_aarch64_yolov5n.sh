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
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_yolov5n}"
SHARED_VM="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/edgeai_arm_yolov5n}"
LOCAL_ARCHIVE="/tmp/edgeai-task014-source.tar.gz"
SHARED_ARCHIVE="$SHARED_LOCAL/edgeai-task014-source.tar.gz"
VM_BUILD_ROOT="/home/uisrc/build/edgeai-arm-yolov5n"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_NCNN_ROOT="/home/uisrc/build/ncnn-aarch64/install"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_yolov5n"

[[ -x "$VM_SSH" ]] || {
  printf 'VM SSH wrapper is not executable: %s\n' "$VM_SSH" >&2
  exit 1
}
for required in \
  "$REPO_ROOT/cpp/CMakeLists.txt" \
  "$REPO_ROOT/cpp/apps/ncnn_image.cpp" \
  "$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake"; do
  [[ -f "$required" ]] || {
    printf 'required source is missing: %s\n' "$required" >&2
    exit 1
  }
done

mkdir -p "$LOG_DIR"

if [[ "$MODE" == "--check" ]]; then
  "$VM_SSH" 'bash -s' <<'REMOTE' | tee "$LOG_DIR/arm_yolov5n_build_check.log"
set -euo pipefail
for required in \
  /home/uisrc/.local/cmake-3.16.9/bin/cmake \
  /home/uisrc/build/ncnn-aarch64/install/lib/libncnn.a \
  /home/uisrc/build/ncnn-aarch64/install/lib/cmake/ncnn/ncnnConfig.cmake \
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
sha256sum /home/uisrc/build/ncnn-aarch64/install/lib/libncnn.a
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
  configs/toolchains/anlogic-dr1-aarch64.cmake

source_sha256="$(sha256sum "$LOCAL_ARCHIVE" | awk '{print $1}')"
source_size="$(stat -c '%s' "$LOCAL_ARCHIVE")"
mkdir -p "$SHARED_LOCAL"
cp "$LOCAL_ARCHIVE" "$SHARED_ARCHIVE"
test "$(sha256sum "$SHARED_ARCHIVE" | awk '{print $1}')" = "$source_sha256"

"$VM_SSH" 'bash -s -- '"$source_sha256"' '"$source_size"' '"$SHARED_VM" "$VM_BUILD_ROOT" "$VM_CMAKE" "$VM_NCNN_ROOT" "$VM_OPENCV_ROOT" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/arm_yolov5n_build.log"
set -euo pipefail

source_sha256=$1
source_size=$2
shared_root=$3
build_root=$4
cmake_bin=$5
ncnn_root=$6
opencv_root=$7
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
  if grep -Eiq 'vulkan|python|libgomp' "$log_dir/$name.readelf-d.txt"; then
    echo "unexpected runtime dependency found in $name" >&2
    exit 1
  fi
done

cp "$application" "$export_dir/edgeai_ncnn_image"
cp "$benchmark_application" "$export_dir/edgeai_benchmark_ncnn"
cp -L "$opencv_root/lib/libopencv_core.so.407" "$export_dir/lib/libopencv_core.so.407"
cp -L "$opencv_root/lib/libopencv_imgproc.so.407" "$export_dir/lib/libopencv_imgproc.so.407"
cp -L "$opencv_root/lib/libopencv_imgcodecs.so.407" "$export_dir/lib/libopencv_imgcodecs.so.407"

(
  cd "$export_dir"
  sha256sum edgeai_ncnn_image edgeai_benchmark_ncnn lib/libopencv_core.so.407 \
    lib/libopencv_imgproc.so.407 lib/libopencv_imgcodecs.so.407 \
    > BUILD_OUTPUT_SHA256SUMS
)

{
  echo "source_archive_sha256=$source_sha256"
  echo "cmake_version=$("$cmake_bin" --version | head -1)"
  echo "compiler=$(/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++ --version | head -1)"
  echo "ncnn_library_sha256=$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')"
  echo "application_sha256=$(sha256sum "$application" | awk '{print $1}')"
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
