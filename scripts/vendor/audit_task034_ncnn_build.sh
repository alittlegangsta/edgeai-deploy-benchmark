#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s --build-output PATH [--source PATH]\n' "$0" >&2
  exit 2
}

build_output=''
source_dir='/home/dministrator/src/ncnn-20240410'
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-output) [[ $# -ge 2 ]] || usage; build_output=$2; shift 2 ;;
    --source) [[ $# -ge 2 ]] || usage; source_dir=$2; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$build_output" ]] || usage

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
expected_commit='56775de50990ab7f16627efdcf5529b49541206f'
expected_param='72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4'
expected_bin='658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0'
expected_input='625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071'

[[ -d "$source_dir/.git" ]] || { printf 'missing ncnn source: %s\n' "$source_dir" >&2; exit 1; }
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$expected_commit" ]] || {
  printf 'unexpected ncnn source commit\n' >&2
  exit 1
}
[[ "$(sha256sum "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.param" | awk '{print $1}')" == "$expected_param" ]]
[[ "$(sha256sum "$repo_root/models/yolov5n-v7.0/yolov5n.ncnn.bin" | awk '{print $1}')" == "$expected_bin" ]]
[[ "$(sha256sum "$repo_root/data/samples/images/pc_reference.jpg" | awk '{print $1}')" == "$expected_input" ]]

for variant in profiling candidate-a candidate-b; do
  [[ -s "$build_output/CMakeCache-$variant.txt" ]] || { printf 'missing cache: %s\n' "$variant" >&2; exit 1; }
  [[ -s "$build_output/edgeai_arm_cpu_profiler-$variant" ]] || { printf 'missing profiler: %s\n' "$variant" >&2; exit 1; }
  grep -q 'Machine:                           AArch64' "$build_output/readelf-h-$variant.txt"
  grep -q 'CMAKE_BUILD_TYPE:STRING=Release' "$build_output/CMakeCache-$variant.txt"
  grep -q 'EDGEAI_ENABLE_NCNN:BOOL=ON' "$build_output/CMakeCache-$variant.txt"
done
[[ -s "$build_output/build_identity.json" ]]
grep -q '"ncnn_source_commit": "56775de50990ab7f16627efdcf5529b49541206f"' "$build_output/build_identity.json"
grep -q '"NCNN_OPENMP": true' "$build_output/build_identity.json"
grep -q '"NCNN_THREADS": true' "$build_output/build_identity.json"
grep -q '"NCNN_SIMPLEOMP": false' "$build_output/build_identity.json"
grep -q '"A": "-O3 -DNDEBUG"' "$build_output/build_identity.json"
grep -q '"B": "-O3 -DNDEBUG -mtune=cortex-a35"' "$build_output/build_identity.json"

printf 'task034_build_audit=PASS\n'
printf 'ncnn_commit=%s\n' "$expected_commit"
printf 'build_output=%s\n' "$build_output"
