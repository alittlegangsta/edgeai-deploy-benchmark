#!/usr/bin/env bash
set -euo pipefail

mode=--check
case "$#" in
  0) ;;
  1)
    case "$1" in
      --check|--execute) mode="$1" ;;
      *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;;
    esac
    ;;
  *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
vm_ssh="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
shared_local="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/task035-ncnn-int8}"
shared_vm="${ANLOGIC_SHARED_VM:-/mnt/hgfs/fpga_info/_generated/task035-ncnn-int8}"
cmake=/home/uisrc/.local/cmake-3.16.9/bin/cmake
opencv=/home/uisrc/vendor/anlogic/sdk/sdk/app/npu/libs/ffmpeg_opencv4.7.0_aarch64
toolchain=/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
build_root=/home/uisrc/build/edgeai-task035-ncnn-int8
ncnn_source=/home/dministrator/src/ncnn-20240410
commit=56775de50990ab7f16627efdcf5529b49541206f
libgomp_sha=87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
param_sha=72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
bin_sha=658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0
input_sha=625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
golden_sha=fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9

[[ -x "$vm_ssh" ]] || { printf 'missing VM wrapper: %s\n' "$vm_ssh" >&2; exit 1; }
[[ -d "$ncnn_source/.git" ]] || { printf 'missing ncnn source: %s\n' "$ncnn_source" >&2; exit 1; }
[[ "$(git -C "$ncnn_source" rev-parse HEAD)" == "$commit" ]] || {
  printf 'unexpected ncnn source commit\n' >&2
  exit 1
}
if [[ "$mode" == --check ]]; then
  sha256sum "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.param" \
    "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.bin" \
    "$repo_root/data/samples/images/pc_reference.jpg" \
    "$repo_root/results/acceptance/cpp_ncnn_reference.json"
  "$vm_ssh" bash -s -- "$cmake" "$toolchain" "$opencv" "$libgomp_sha" <<'REMOTE'
set -euo pipefail
cmake=$1; toolchain=$2; opencv=$3; expected=$4
test -x "$cmake"; test -x "$toolchain/bin/aarch64-linux-gnu-g++"
test -f "$opencv/lib/cmake/opencv4/OpenCVConfig.cmake"
gomp=$(readlink -f "$($toolchain/bin/aarch64-linux-gnu-g++ -print-file-name=libgomp.so.1)")
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected"
printf 'cmake=%s\n' "$($cmake --version | head -1)"
printf 'compiler=%s\n' "$($toolchain/bin/aarch64-linux-gnu-g++ --version | head -1)"
printf 'task035_vm_check=PASS\n'
REMOTE
  exit 0
fi

mkdir -p "$shared_local"
ncnn_archive=/tmp/task035-ncnn-${commit}.tar.gz
project_archive=/tmp/task035-project-${commit}.tar.gz
git -C "$ncnn_source" archive --format=tar --prefix=ncnn-20240410/ "$commit" | gzip -n > "$ncnn_archive"
tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  -czf "$project_archive" -C "$repo_root" cpp configs/toolchains/anlogic-dr1-aarch64.cmake
cp "$ncnn_archive" "$shared_local/ncnn-source.tar.gz"
cp "$project_archive" "$shared_local/project-source.tar.gz"
ncnn_sha="$(sha256sum "$ncnn_archive" | awk '{print $1}')"
project_sha="$(sha256sum "$project_archive" | awk '{print $1}')"

"$vm_ssh" bash -s -- "$shared_vm" "$build_root" "$cmake" "$opencv" "$toolchain" \
  "$ncnn_sha" "$project_sha" "$commit" "$libgomp_sha" <<'REMOTE'
set -euo pipefail
shared=$1; root=$2; cmake=$3; opencv=$4; toolchain=$5
ncnn_sha=$6; project_sha=$7; commit=$8; expected_gomp=$9
mkdir -p "$root" "$shared/build-output"
na="$root/ncnn-source-$ncnn_sha.tar"; pa="$root/project-source-$project_sha.tar"
mkdir -p "$root/ncnn-source-$ncnn_sha" "$root/project-source-$project_sha"
tar -xzf "$shared/ncnn-source.tar.gz" -C "$root/ncnn-source-$ncnn_sha"
tar -xzf "$shared/project-source.tar.gz" -C "$root/project-source-$project_sha"
ns="$root/ncnn-source-$ncnn_sha/ncnn-20240410"
ps="$root/project-source-$project_sha"
gxx="$toolchain/bin/aarch64-linux-gnu-g++"
gomp=$(readlink -f "$($gxx -print-file-name=libgomp.so.1)")
test "$(sha256sum "$gomp" | awk '{print $1}')" = "$expected_gomp"
nb="$root/ncnn-build-int8-$ncnn_sha"; ni="$root/ncnn-install-int8-$ncnn_sha"
mkdir -p "$root/logs"
"$cmake" -S "$ns" -B "$nb" -DCMAKE_TOOLCHAIN_FILE="$ps/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$ni" -DNCNN_VERSION=20240410 \
  -DNCNN_SHARED_LIB=OFF -DNCNN_OPENMP=ON -DNCNN_SIMPLEOMP=OFF -DNCNN_THREADS=ON \
  -DNCNN_RUNTIME_CPU=ON -DNCNN_BENCHMARK=OFF -DNCNN_VULKAN=OFF -DNCNN_INT8=ON \
  -DNCNN_BF16=ON -DNCNN_FORCE_INLINE=ON -DNCNN_ENABLE_LTO=OFF -DNCNN_ARM82=OFF \
  -DNCNN_VFPV4=ON -DNCNN_GNU_INLINE_ASM=ON -DCMAKE_C_FLAGS_RELEASE='-O3 -DNDEBUG' \
  -DCMAKE_CXX_FLAGS_RELEASE='-O3 -DNDEBUG' > "$root/logs/ncnn-configure.log" 2>&1
"$cmake" --build "$nb" --target install -- -j2 > "$root/logs/ncnn-build.log" 2>&1
lib_sha=$(sha256sum "$ni/lib/libncnn.a" | awk '{print $1}')
pb="$root/project-build-int8-$project_sha"
"$cmake" -S "$ps/cpp" -B "$pb" -DCMAKE_TOOLCHAIN_FILE="$ps/configs/toolchains/anlogic-dr1-aarch64.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DEDGEAI_ENABLE_ORT=OFF -DEDGEAI_ENABLE_NCNN=ON \
  -DEDGEAI_ENABLE_VIDEO=OFF -DEDGEAI_OPENCV_ROOT="$opencv" -DNCNN_ROOT="$ni" \
  -DEDGEAI_NCNN_LIBRARY_SHA256="$lib_sha" -DEDGEAI_PRIVATE_LIBGOMP_SHA256="$expected_gomp" \
  > "$root/logs/project-configure.log" 2>&1
"$cmake" --build "$pb" --target edgeai_arm_cpu_profiler edgeai_arm_cpu_profiler_tests -- -j2 \
  > "$root/logs/project-build.log" 2>&1
cp "$pb/edgeai_arm_cpu_profiler" "$shared/build-output/edgeai_arm_cpu_profiler-int8"
cp "$pb/edgeai_arm_cpu_profiler_tests" "$shared/build-output/edgeai_arm_cpu_profiler_tests-int8"
cp "$nb/CMakeCache.txt" "$shared/build-output/CMakeCache-ncnn-int8.txt"
cp "$pb/CMakeCache.txt" "$shared/build-output/CMakeCache-project-int8.txt"
cp "$root/logs/"*.log "$shared/build-output/"
file "$pb/edgeai_arm_cpu_profiler" > "$shared/build-output/file-profiler-int8.txt"
readelf -h "$pb/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-h-profiler-int8.txt"
readelf -lW "$pb/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-l-profiler-int8.txt"
readelf -dW "$pb/edgeai_arm_cpu_profiler" > "$shared/build-output/readelf-d-profiler-int8.txt"
sha256sum "$pb/edgeai_arm_cpu_profiler" > "$shared/build-output/sha256-profiler-int8.txt"
sha256sum "$ni/lib/libncnn.a" > "$shared/build-output/sha256-libncnn-int8.txt"
cat > "$shared/build-output/build_identity.json" <<IDENTITY
{"schema_version":1,"task":"035","ncnn_source_commit":"$commit","ncnn_source_archive_sha256":"$ncnn_sha","project_source_archive_sha256":"$project_sha","compiler":"$($gxx --version | head -1)","cmake":"$($cmake --version | head -1)","options":{"NCNN_OPENMP":true,"NCNN_THREADS":true,"NCNN_SIMPLEOMP":false,"NCNN_RUNTIME_CPU":true,"NCNN_INT8":true,"NCNN_BF16":true,"NCNN_FORCE_INLINE":true,"NCNN_ENABLE_LTO":false,"NCNN_ARM82":false,"NCNN_VFPV4":true,"release":true},"libncnn_sha256":"$lib_sha","libgomp_sha256":"$expected_gomp"}
IDENTITY
printf 'task035_vm_build=PASS\n'
printf 'ncnn_source_archive_sha256=%s\nproject_source_archive_sha256=%s\n' "$ncnn_sha" "$project_sha"
REMOTE
printf 'task035_shared_build_output=%s\n' "$shared_local/build-output"
