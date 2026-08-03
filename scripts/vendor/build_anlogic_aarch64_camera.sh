#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
if [[ "$#" -gt 1 ]]; then printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2; fi
if [[ "$#" -eq 1 ]]; then MODE="$1"; fi
case "$MODE" in --check|--execute) ;; *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;; esac

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VM_SSH="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_camera_task021}"
SHARED_VM="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/edgeai_arm_camera_task021}"
LOCAL_ARCHIVE="/tmp/edgeai-task021-source.tar.gz"
VM_BUILD_ROOT="/home/uisrc/build/edgeai-arm-camera-task021"
VM_CMAKE="/home/uisrc/.local/cmake-3.16.9/bin/cmake"
VM_NCNN_ROOT="/home/uisrc/build/ncnn-aarch64-openmp/install-libgomp-81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45"
VM_OPENCV_ROOT="/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64"
EXPECTED_NCNN="bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
EXPECTED_LIBGOMP="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_uvc_camera"

[[ -x "$VM_SSH" ]] || { printf 'VM SSH wrapper is not executable: %s\n' "$VM_SSH" >&2; exit 1; }
for required in \
  "$REPO_ROOT/cpp/CMakeLists.txt" "$REPO_ROOT/cpp/apps/ncnn_camera.cpp" \
  "$REPO_ROOT/cpp/include/edgeai/common/camera_pipeline.hpp" \
  "$REPO_ROOT/cpp/src/common/camera_pipeline.cpp" \
  "$REPO_ROOT/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  "$REPO_ROOT/configs/runtime_profiles/anlogic-dr1-recommended-dual-thread.json"; do
  [[ -f "$required" ]] || { printf 'required Task 021 source is missing: %s\n' "$required" >&2; exit 1; }
done
mkdir -p "$LOG_DIR"

if [[ "$MODE" == "--check" ]]; then
  "$VM_SSH" 'bash -s -- '"$VM_CMAKE"' '"$VM_NCNN_ROOT"' '"$VM_OPENCV_ROOT"' '"$EXPECTED_NCNN"' '"$EXPECTED_LIBGOMP" <<'REMOTE' \
    2>&1 | tee "$LOG_DIR/vm_camera_capability_check.log"
set -euo pipefail
cmake_bin=$1; ncnn_root=$2; opencv_root=$3; expected_ncnn=$4; expected_gomp=$5
gxx=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
for required in "$cmake_bin" "$gxx" "$ncnn_root/lib/libncnn.a" "$ncnn_root/lib/cmake/ncnn/ncnnConfig.cmake" \
  "$opencv_root/include/opencv4/opencv2/videoio.hpp" "$opencv_root/lib/cmake/opencv4/OpenCVConfig.cmake" \
  "$opencv_root/lib/libopencv_videoio.so.4.7.0" "$opencv_root/lib/libavcodec.so.58.54.100" \
  "$opencv_root/lib/libavformat.so.58.29.100" "$opencv_root/lib/libavutil.so.56.31.100" \
  "$opencv_root/lib/libswscale.so.5.5.100"; do
  test -f "$required"; printf 'present=%s\n' "$required"
done
test "$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" = "$expected_ncnn"
gomp=$(readlink -f "$("$gxx" -print-file-name=libgomp.so.1)")
test -f "$gomp"; test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"
file "$opencv_root/lib/libopencv_videoio.so.4.7.0" "$gomp"
readelf -dW "$opencv_root/lib/libopencv_videoio.so.4.7.0" | grep NEEDED
"$cmake_bin" --version | head -1; "$gxx" --version | head -1
printf 'camera_capability_check=PASS\n'
REMOTE
  exit 0
fi

tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  -czf "$LOCAL_ARCHIVE" -C "$REPO_ROOT" cpp configs/toolchains/anlogic-dr1-aarch64.cmake \
  configs/runtime_profiles/anlogic-dr1-recommended-dual-thread.json
source_sha256="$(sha256sum "$LOCAL_ARCHIVE" | awk '{print $1}')"
source_size="$(stat -c '%s' "$LOCAL_ARCHIVE")"
mkdir -p "$SHARED_LOCAL"; cp "$LOCAL_ARCHIVE" "$SHARED_LOCAL/edgeai-task021-source.tar.gz"
test "$(sha256sum "$SHARED_LOCAL/edgeai-task021-source.tar.gz" | awk '{print $1}')" = "$source_sha256"

"$VM_SSH" 'bash -s -- '"$source_sha256"' '"$source_size"' '"$SHARED_VM"' '"$VM_BUILD_ROOT"' '"$VM_CMAKE"' '"$VM_NCNN_ROOT"' '"$VM_OPENCV_ROOT"' '"$EXPECTED_NCNN"' '"$EXPECTED_LIBGOMP" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/vm_camera_build.log"
set -euo pipefail
source_sha256=$1; source_size=$2; shared_root=$3; build_root=$4; cmake_bin=$5; ncnn_root=$6; opencv_root=$7; expected_ncnn=$8; expected_gomp=$9
archive="$shared_root/edgeai-task021-source.tar.gz"
source_dir="$build_root/source-$source_sha256"; build_dir="$build_root/build-$source_sha256"; log_dir="$build_root/logs-$source_sha256"; export_dir="$shared_root/build-output"
gxx=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-g++
test -f "$archive"; test "$(stat -c '%s' "$archive")" = "$source_size"; test "$(sha256sum "$archive" | awk '{print $1}')" = "$source_sha256"
test -x "$cmake_bin"; test -f "$ncnn_root/lib/libncnn.a"; test "$(sha256sum "$ncnn_root/lib/libncnn.a" | awk '{print $1}')" = "$expected_ncnn"
gomp_real=$(readlink -f "$("$gxx" -print-file-name=libgomp.so.1)"); test -f "$gomp_real"; test "$(sha256sum "$gomp_real" | awk '{print $1}')" = "$expected_gomp"
rm -rf "$source_dir" "$build_dir" "$log_dir" "$export_dir.new"; mkdir -p "$source_dir" "$build_dir" "$log_dir"
tar -xzf "$archive" -C "$source_dir"
"$cmake_bin" -S "$source_dir/cpp" -B "$build_dir" \
  -DCMAKE_TOOLCHAIN_FILE="$source_dir/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DEDGEAI_ENABLE_ORT=OFF \
  -DEDGEAI_ENABLE_NCNN=ON -DEDGEAI_ENABLE_VIDEO=ON -DEDGEAI_OPENCV_ROOT="$opencv_root" \
  -DNCNN_ROOT="$ncnn_root" -DEDGEAI_NCNN_LIBRARY_SHA256="$expected_ncnn" \
  -DEDGEAI_PRIVATE_LIBGOMP_SHA256="$expected_gomp" 2>&1 | tee "$log_dir/configure.log"
"$cmake_bin" --build "$build_dir" --target edgeai_ncnn_camera -- -j2 2>&1 | tee "$log_dir/build.log"
application="$build_dir/edgeai_ncnn_camera"; test -x "$application"
file "$application" | tee "$log_dir/application.file.txt"
readelf -hW "$application" > "$log_dir/application.readelf-h.txt"; readelf -lW "$application" > "$log_dir/application.readelf-l.txt"
readelf -dW "$application" > "$log_dir/application.readelf-d.txt"; readelf -AW "$application" > "$log_dir/application.readelf-a.txt"; readelf -VW "$application" > "$log_dir/application.readelf-v.txt"; sha256sum "$application" | tee "$log_dir/application.sha256"
grep -Fq 'ELF 64-bit' "$log_dir/application.file.txt"; grep -Eq 'ARM aarch64|AArch64' "$log_dir/application.file.txt"; grep -Fq '/lib/ld-linux-aarch64.so.1' "$log_dir/application.readelf-l.txt"
for dependency in libopencv_core.so.407 libopencv_imgproc.so.407 libopencv_imgcodecs.so.407 libopencv_videoio.so.407 libgomp.so.1; do grep -Fq "Shared library: [$dependency]" "$log_dir/application.readelf-d.txt"; done
if grep -Eiq 'vulkan|python' "$log_dir/application.readelf-d.txt"; then printf 'unexpected Vulkan/Python dependency\n' >&2; exit 1; fi
rm -rf "$export_dir.new"; mkdir -p "$export_dir.new/lib"; cp "$application" "$export_dir.new/edgeai_ncnn_camera"
copy_soname() { cp -L "$opencv_root/lib/$1" "$export_dir.new/lib/$2"; }
copy_soname libopencv_core.so.4.7.0 libopencv_core.so.407; copy_soname libopencv_imgproc.so.4.7.0 libopencv_imgproc.so.407; copy_soname libopencv_imgcodecs.so.4.7.0 libopencv_imgcodecs.so.407; copy_soname libopencv_videoio.so.4.7.0 libopencv_videoio.so.407
copy_soname libavcodec.so.58.54.100 libavcodec.so.58; copy_soname libavformat.so.58.29.100 libavformat.so.58; copy_soname libavutil.so.56.31.100 libavutil.so.56; copy_soname libswscale.so.5.5.100 libswscale.so.5; copy_soname libswresample.so.3.5.100 libswresample.so.3; copy_soname libx264.so.157 libx264.so.157
cp -L "$gomp_real" "$export_dir.new/lib/libgomp.so.1"
application_sha256=$(sha256sum "$application" | awk '{print $1}')
cat > "$export_dir.new/runtime_build_identity.json" <<IDENTITY
{
  "schema_version": 1, "task": "021", "runtime_profile": "recommended-dual-thread",
  "NCNN_OPENMP": true, "NCNN_THREADS": true, "NCNN_SIMPLEOMP": false,
  "effective_parallel_backend": "openmp", "configured_threads": 2,
  "libncnn_a_sha256": "$expected_ncnn", "private_libgomp_so_1_sha256": "$expected_gomp",
  "executable_sha256": "$application_sha256", "opencv_version": "4.7.0",
  "opencv_videoio_sha256": "$(sha256sum "$opencv_root/lib/libopencv_videoio.so.4.7.0" | awk '{print $1}')"
}
IDENTITY
printf 'task=021\nsource_archive_sha256=%s\ncmake=%s\ncompiler=%s\nncnn_library_sha256=%s\nprivate_libgomp_sha256=%s\napplication_sha256=%s\napplication=%s\nbuild_dir=%s\nstatus=PASS\n' "$source_sha256" "$("$cmake_bin" --version | head -1)" "$("$gxx" --version | head -1)" "$expected_ncnn" "$expected_gomp" "$application_sha256" "$application" "$build_dir" > "$export_dir.new/build_summary.txt"
(
  cd "$export_dir.new"
  find . -type f ! -name BUILD_OUTPUT_SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > BUILD_OUTPUT_SHA256SUMS
)
rm -rf "$export_dir"; mv "$export_dir.new" "$export_dir"
cat "$export_dir/build_summary.txt"; cat "$export_dir/BUILD_OUTPUT_SHA256SUMS"
REMOTE

printf 'source_archive=%s\nsource_archive_sha256=%s\nshared_build_output=%s/build-output\n' "$LOCAL_ARCHIVE" "$source_sha256" "$SHARED_LOCAL"
