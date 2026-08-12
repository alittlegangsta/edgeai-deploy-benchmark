#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_dir="${NCNN_SOURCE_DIR:-/home/dministrator/src/ncnn-20240410}"
tools_dir="${NCNN_TOOLS_DIR:-$source_dir/build-linux-x64-release/tools}"
commit=56775de50990ab7f16627efdcf5529b49541206f
param_sha=72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
bin_sha=658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0

[[ -d "$source_dir/.git" ]]
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$commit" ]]
[[ "$(sha256sum "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.param" | awk '{print $1}')" == "$param_sha" ]]
[[ "$(sha256sum "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.bin" | awk '{print $1}')" == "$bin_sha" ]]
for tool in "$tools_dir/ncnnoptimize" "$tools_dir/quantize/ncnn2table" "$tools_dir/quantize/ncnn2int8"; do
  [[ -s "$tool" ]]
  file "$tool"
  sha256sum "$tool"
done
grep -q 'option(NCNN_INT8 "int8 inference" ON)' "$source_dir/CMakeLists.txt"
find "$source_dir/src/layer/arm" -maxdepth 1 -type f -iname '*int8*' -printf '%f\n' | sort
printf 'task035_int8_source_audit=PASS\n'
