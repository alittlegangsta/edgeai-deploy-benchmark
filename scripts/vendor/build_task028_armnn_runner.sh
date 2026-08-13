#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
usage: build_task028_armnn_runner.sh --source-root PATH --build-dir PATH \
  --armnn-root PATH --opencv-root PATH --toolchain-file PATH \
  [--cmake PATH] [--jobs N] [--check|--dry-run]
EOF
}

source_root=
build_dir=
armnn_root=
opencv_root=
toolchain_file=
cmake_bin=cmake
jobs=2
mode=build

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-root) source_root=$2; shift 2 ;;
        --build-dir) build_dir=$2; shift 2 ;;
        --armnn-root) armnn_root=$2; shift 2 ;;
        --opencv-root) opencv_root=$2; shift 2 ;;
        --toolchain-file) toolchain_file=$2; shift 2 ;;
        --cmake) cmake_bin=$2; shift 2 ;;
        --jobs) jobs=$2; shift 2 ;;
        --check) mode=check; shift ;;
        --dry-run) mode=dry-run; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

for required in source_root build_dir armnn_root opencv_root toolchain_file; do
    if [[ -z "${!required}" ]]; then
        echo "missing --${required//_/-}" >&2
        usage
        exit 2
    fi
done

for path in "$source_root/cpp/CMakeLists.txt" \
            "$armnn_root/include/armnn/ArmNN.hpp" \
            "$armnn_root/include/armnnOnnxParser/IOnnxParser.hpp" \
            "$armnn_root/lib/libarmnn.so" \
            "$armnn_root/lib/libarmnnOnnxParser.so" \
            "$toolchain_file"; do
    [[ -e "$path" ]] || { echo "required path missing: $path" >&2; exit 1; }
done

armnn_sha256=$(sha256sum "$armnn_root/lib/libarmnn.so" | awk '{print $1}')
build_id=$(basename "$armnn_root")
configure=("$cmake_bin" -S "$source_root/cpp" -B "$build_dir"
    -DCMAKE_BUILD_TYPE=Release
    -DCMAKE_TOOLCHAIN_FILE="$toolchain_file"
    -DEDGEAI_ENABLE_ORT=OFF
    -DEDGEAI_ENABLE_NCNN=OFF
    -DEDGEAI_ENABLE_VIDEO=OFF
    -DEDGEAI_ENABLE_ARMNN=ON
    -DARMNN_ROOT="$armnn_root"
    -DEDGEAI_OPENCV_ROOT="$opencv_root"
    -DEDGEAI_ARMNN_BUILD_ID="$build_id"
    -DEDGEAI_ARMNN_LIBRARY_SHA256="$armnn_sha256")
build=("$cmake_bin" --build "$build_dir" --target edgeai_armnn_image -- -j"$jobs")

if [[ "$mode" == check ]]; then
    printf 'PASS check source=%s armnn=%s opencv=%s toolchain=%s armnn_sha256=%s\n' \
        "$source_root" "$armnn_root" "$opencv_root" "$toolchain_file" "$armnn_sha256"
    exit 0
fi
if [[ "$mode" == dry-run ]]; then
    printf 'configure:'; printf ' %q' "${configure[@]}"; printf '\n'
    printf 'build:'; printf ' %q' "${build[@]}"; printf '\n'
    exit 0
fi

"${configure[@]}"
"${build[@]}"
file "$build_dir/edgeai_armnn_image"
readelf -h "$build_dir/edgeai_armnn_image"
readelf -d "$build_dir/edgeai_armnn_image"
sha256sum "$build_dir/edgeai_armnn_image"
