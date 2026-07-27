#!/usr/bin/env bash

set -euo pipefail

WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"

if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: VM SSH wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi

"$WRAPPER" 'bash -s' <<'REMOTE'
set -u

SDK_ROOT=/home/uisrc/vendor/anlogic/sdk/sdk
SDK_ARCHIVE=/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz
DEMO_ROOT=/home/uisrc/vendor/anlogic/demos/milianke_npu_demo
LOG_ROOT=/home/uisrc/vendor/anlogic/logs/npu_dependency_audit
ARMNN_ROOT=$SDK_ROOT/app/npu/libs/armnn_lib
OPENCV_ROOT=$SDK_ROOT/app/npu/libs/ffmpeg_opencv4.7.0_aarch64

mkdir -p "$LOG_ROOT"

command_status() {
  command -v "$1" 2>/dev/null || printf 'NOT_FOUND\n'
}

text_files() {
  find -P "$1" -type f -size -2M \( \
    -iname 'README*' -o -iname '*.md' -o -iname '*.txt' -o -iname '*.ini' \
    -o -iname 'Makefile' -o -iname 'CMakeLists.txt' -o -iname '*.cmake' \
    -o -iname '*.mk' -o -iname '*.sh' -o -iname '*.conf' -o -iname '*.cfg' \
  \) -print0 2>/dev/null
}

append_matches() {
  output=$1
  file=$2
  expression=$3
  matches=$(grep -n -I -E "$expression" "$file" 2>/dev/null || true)
  if [ -n "$matches" ]; then
    printf '\n--- %s ---\n%s\n' "$file" "$matches" >> "$output"
  fi
}

elf_report() {
  output=$1
  file_path=$2
  kind=$(file -b "$file_path" 2>/dev/null || printf 'file_command_failed')
  printf '\n=== %s ===\nfile=%s\n' "$file_path" "$kind" >> "$output"
  case "$kind" in
    *ELF*)
      if command -v readelf >/dev/null 2>&1; then
        readelf -h "$file_path" 2>/dev/null \
          | grep -E 'Class:|Data:|Machine:|Type:|Entry point' >> "$output" || true
        readelf -d "$file_path" 2>/dev/null \
          | grep -E 'SONAME|NEEDED|RPATH|RUNPATH' >> "$output" || true
        readelf -Ws "$file_path" 2>/dev/null \
          | grep -i -E 'npu|armnn|backend|delegate|cma_mem|hard_npu|soft_npu' \
          | head -n 40 >> "$output" || true
      else
        printf 'readelf=NOT_FOUND\n' >> "$output"
      fi
      if command -v strings >/dev/null 2>&1; then
        strings -a "$file_path" 2>/dev/null \
          | grep -i -E 'npu|armnn|backend|delegate|cma_mem|hard_npu|soft_npu' \
          | head -n 40 >> "$output" || true
      fi
      ;;
  esac
}

{
  printf 'sdk_root=%s\n' "$SDK_ROOT"
  printf 'sdk_archive=%s\n' "$SDK_ARCHIVE"
  printf 'demo_root=%s\n' "$DEMO_ROOT"
  printf 'log_root=%s\n' "$LOG_ROOT"
  printf 'date=%s\n' "$(date --iso-8601=seconds)"
  printf 'file=%s\n' "$(command_status file)"
  printf 'readelf=%s\n' "$(command_status readelf)"
  printf 'strings=%s\n' "$(command_status strings)"
  printf 'modinfo=%s\n' "$(command_status modinfo)"
} > "$LOG_ROOT/tool_commands.txt"

find -P "$DEMO_ROOT" -maxdepth 4 -printf '%y\t%p\n' 2>/dev/null \
  | sort > "$LOG_ROOT/demo_tree.txt"

{
  printf 'demo_root=%s\n' "$DEMO_ROOT"
  printf 'regular_files='; find -P "$DEMO_ROOT" -type f -printf '.' | wc -c
  printf 'directories='; find -P "$DEMO_ROOT" -type d -printf '.' | wc -c
  printf 'symlinks='; find -P "$DEMO_ROOT" -type l -printf '.' | wc -c
  printf 'small_text_candidates='; text_files "$DEMO_ROOT" | tr -cd '\0' | wc -c
  printf '\n=== top-level and depth-4 path sample ===\n'
  sed -n '1,400p' "$LOG_ROOT/demo_tree.txt"
} > "$LOG_ROOT/demo_tree_summary.txt"

: > "$LOG_ROOT/demo_build_references.txt"
: > "$LOG_ROOT/demo_runtime_references.txt"
while IFS= read -r -d '' file_path; do
  append_matches "$LOG_ROOT/demo_build_references.txt" "$file_path" \
    'aarch64|gcc|g\+\+|CROSS_COMPILE|SYSROOT|sysroot|toolchain|armnn|ArmNN|OpenCV|opencv|find_package|CMAKE_PREFIX_PATH|OpenCV_DIR|ArmNN_DIR|-[lL]|SDK_[0-9]|2025[._-]07|2026[._-]01|cmake_minimum_required'
  append_matches "$LOG_ROOT/demo_runtime_references.txt" "$file_path" \
    'LD_LIBRARY_PATH|dlopen|/npu_demo|run\.sh|run_.*\.sh|model|models|\.onnx|\.tflite|\.bin|\.param|\.hpf|\.bit|hard_npu|soft_npu|cma_mem|NPU|npu|DR1M90|build\.sh|envsetup'
done < <(text_files "$DEMO_ROOT")

{
  printf 'armnn_root=%s\n' "$ARMNN_ROOT"
  if [ -d "$ARMNN_ROOT" ]; then
    find -P "$ARMNN_ROOT" -maxdepth 4 -printf '%y\t%p\n' | sort
    printf '\n=== expected component markers ===\n'
    for marker in include/armnn Version.hpp lib ArmnnConfig.cmake ArmNNConfig.cmake; do
      if [ -e "$ARMNN_ROOT/$marker" ]; then
        printf 'present=%s\n' "$ARMNN_ROOT/$marker"
      else
        printf 'missing=%s\n' "$ARMNN_ROOT/$marker"
      fi
    done
    printf '\n=== version/config text matches ===\n'
    find -P "$ARMNN_ROOT" -type f -size -512k \( -iname 'Version.hpp' -o -iname '*config*.cmake' -o -iname '*.h' \) -print0 \
      | while IFS= read -r -d '' file_path; do
          append_matches "$LOG_ROOT/armnn_inventory.txt" "$file_path" \
            'ARMNN_VERSION|ARMNN_MAJOR|ARMNN_MINOR|ARMNN_PATCH|VERSION|ArmNN|armnn'
        done
  else
    printf 'ARMNN_NOT_FOUND\n'
  fi
} > "$LOG_ROOT/armnn_inventory.txt"

printf '\n=== ELF/library reports ===\n' >> "$LOG_ROOT/armnn_elf.txt"
if [ -d "$ARMNN_ROOT" ]; then
  find -P "$ARMNN_ROOT" -type f \( -name '*.so*' -o -name '*.a' \) -print0 \
    | sort -z | while IFS= read -r -d '' file_path; do
        elf_report "$LOG_ROOT/armnn_elf.txt" "$file_path"
      done
fi

{
  printf 'opencv_root=%s\n' "$OPENCV_ROOT"
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type d \( -iname '*opencv*' -o -iname '*OpenCV*' \) \
    -print 2>/dev/null | sort
  printf '\n=== OpenCV config/version files ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f \( \
    -iname 'OpenCVConfig.cmake' -o -iname 'OpenCVConfig-version.cmake' \
    -iname 'version.hpp' -o -iname 'opencv4.pc' \) -print 2>/dev/null | sort
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -size -512k \( \
    -iname 'OpenCVConfig.cmake' -o -iname 'OpenCVConfig-version.cmake' \
    -iname 'version.hpp' -o -iname 'opencv4.pc' \) -print0 2>/dev/null \
    | while IFS= read -r -d '' file_path; do
        append_matches "$LOG_ROOT/opencv_inventory.txt" "$file_path" \
          'OpenCV_VERSION|CV_VERSION|4\.7|opencv4|OpenCV'
      done
  printf '\n=== expected module markers ===\n'
  for module in core imgproc dnn videoio highgui imgcodecs; do
    find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -name "libopencv_${module}.so*" -print 2>/dev/null \
      | sort | head -n 20
  done
} > "$LOG_ROOT/opencv_inventory.txt"

: > "$LOG_ROOT/opencv_elf.txt"
if [ -d "$OPENCV_ROOT" ]; then
  find -P "$OPENCV_ROOT" -type f -name 'libopencv_*.so*' -print0 \
    | sort -z | while IFS= read -r -d '' file_path; do
        elf_report "$LOG_ROOT/opencv_elf.txt" "$file_path"
      done
fi

{
  printf '=== link/build references ===\n'
  cat "$LOG_ROOT/demo_build_references.txt"
  printf '\n=== candidate runtime libraries and ELF dependencies ===\n'
  find -P "$DEMO_ROOT" "$SDK_ROOT/app/npu" -type f \( -name '*.so*' -o -perm -111 \) -print0 2>/dev/null \
    | sort -z | while IFS= read -r -d '' file_path; do
        kind=$(file -b "$file_path" 2>/dev/null || true)
        case "$kind" in
          *ELF*) elf_report "$LOG_ROOT/npu_interface_inventory.txt" "$file_path" ;;
        esac
      done
  printf '\n=== npu-like source references ===\n'
  grep -R -n -I -E 'libnpu_runtime|npu_runtime|hard_npu|soft_npu|cma_mem|ArmNN|armnn|backend|dlopen' \
    "$DEMO_ROOT" "$SDK_ROOT/app/npu" 2>/dev/null | head -n 500 || true
} > "$LOG_ROOT/npu_interface_inventory.txt"

{
  printf '=== driver and hardware paths ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f \( \
    -name '*.ko' -o -name '*.hpf' -o -name '*.bit' -o -name 'BOOT.BIN' \
    -o -name 'uImage' -o -name 'Image' -o -name '*.dtb' -o -name '*.dts' \
    -o -iname '*rootfs*' -o -iname '*cma*' -o -iname '*hard_npu*' -o -iname '*soft_npu*' \
  \) -print 2>/dev/null | sort
  printf '\n=== driver metadata ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -name '*.ko' -print0 2>/dev/null \
    | sort -z | while IFS= read -r -d '' file_path; do
        printf '\n--- %s ---\n' "$file_path"
        file "$file_path" 2>/dev/null || true
        if command -v modinfo >/dev/null 2>&1; then
          modinfo "$file_path" 2>&1 | grep -E '^(filename|version|vermagic|description|name):' || true
        else
          printf 'modinfo=NOT_FOUND\n'
        fi
        if command -v strings >/dev/null 2>&1; then
          strings -a "$file_path" 2>/dev/null | grep -i -E 'version|hard_npu|soft_npu|cma_mem|npu' | head -n 30 || true
        fi
      done
} > "$LOG_ROOT/driver_inventory.txt"

find -P "$SDK_ROOT" "$DEMO_ROOT" -type f \( \
  -name '*.hpf' -o -name '*.bit' -o -name 'BOOT.BIN' -o -name 'uImage' \
  -o -name 'Image' -o -name '*.dtb' -o -name '*.dts' -o -iname '*rootfs*' \
\) -printf '%p\n' 2>/dev/null | sort > "$LOG_ROOT/hardware_artifact_inventory.txt"

{
  printf '=== toolchain archive paths ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f \( \
    -iname '*aarch64*' -o -iname '*toolchain*' -o -iname '*gcc*' \) \
    -print 2>/dev/null | sort
  printf '\n=== archive metadata and bounded member previews ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f \( \
    -iname '*.tar' -o -iname '*.tar.gz' -o -iname '*.tgz' -o -iname '*.tar.xz' \
    -o -iname '*.tar.bz2' \) -print0 2>/dev/null \
    | sort -z | while IFS= read -r -d '' file_path; do
        printf '\n--- %s ---\n' "$file_path"
        stat --printf='size_bytes=%s\n' "$file_path" 2>/dev/null || true
        case "$file_path" in
          *.tar|*.tar.gz|*.tgz|*.tar.xz|*.tar.bz2)
            tar tf "$file_path" 2>/dev/null | head -n 200 || true
            ;;
        esac
      done
} > "$LOG_ROOT/toolchain_archive_inventory.txt"

{
  printf '=== CMake/toolchain references ===\n'
  find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -size -2M \( \
    -name 'CMakeLists.txt' -o -name '*.cmake' -o -name 'Makefile' -o -name '*.mk' -o -name '*.sh' \
  \) -print0 2>/dev/null | while IFS= read -r -d '' file_path; do
    append_matches "$LOG_ROOT/cmake_requirements.txt" "$file_path" \
      'cmake_minimum_required|find_package|CMAKE_PREFIX_PATH|OpenCV_DIR|ArmNN_DIR|toolchain|CMAKE_TOOLCHAIN_FILE|CMAKE_C_COMPILER|CMAKE_CXX_COMPILER'
  done
} > "$LOG_ROOT/cmake_requirements.txt"

{
  printf '=== SDK version ===\n'
  if [ -f "$SDK_ROOT/buildroot/rel_ver" ]; then cat "$SDK_ROOT/buildroot/rel_ver"; else printf 'SDK_VERSION_NOT_FOUND\n'; fi
  printf '\n=== Demo/SDK version references ===\n'
  grep -R -n -I -E 'SDK_[0-9]|2025[._-]07|2026[._-]01|sdk\.2025|SDK_VERSION|release' \
    "$DEMO_ROOT" "$SDK_ROOT/app/npu" "$SDK_ROOT/README.md" 2>/dev/null | head -n 500 || true
} > "$LOG_ROOT/version_evidence.txt"

{
  printf '# NPU dependency audit summary\n\n'
  printf -- '- SDK_ROOT: %s\n' "$SDK_ROOT"
  printf -- '- SDK_ARCHIVE: %s\n' "$SDK_ARCHIVE"
  printf -- '- NPU_DEMO_ROOT: %s\n' "$DEMO_ROOT"
  printf -- '- SDK release marker: %s\n' "$(cat "$SDK_ROOT/buildroot/rel_ver" 2>/dev/null || printf unknown)"
  printf -- '- Arm NN directory: %s\n' "$(if [ -d "$ARMNN_ROOT" ]; then printf present; else printf missing; fi)"
  printf -- '- OpenCV 4.7-named directory: %s\n' "$(if [ -d "$OPENCV_ROOT" ]; then printf present; else printf missing; fi)"
  printf -- '- documented AArch64 compiler: %s\n' "$(if [ -e "$SDK_ROOT/toolchains/aarch64-linux/bin/aarch64-linux-gnu-gcc" ]; then printf present; else printf missing_not_extracted; fi)"
  printf -- '- exact libnpu_runtime path: %s\n' "$(find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -name 'libnpu_runtime*' -print -quit 2>/dev/null || true)"
  printf -- '- no build or execution performed: true\n'
} > "$LOG_ROOT/summary.md"

printf 'audit_complete\n'
printf 'log_root=%s\n' "$LOG_ROOT"
printf 'sdk_release=%s\n' "$(cat "$SDK_ROOT/buildroot/rel_ver" 2>/dev/null || printf unknown)"
printf 'armnn_dir=%s\n' "$(if [ -d "$ARMNN_ROOT" ]; then printf present; else printf missing; fi)"
printf 'opencv_dir=%s\n' "$(if [ -d "$OPENCV_ROOT" ]; then printf present; else printf missing; fi)"
printf 'compiler_path=%s\n' "$(if [ -e "$SDK_ROOT/toolchains/aarch64-linux/bin/aarch64-linux-gnu-gcc" ]; then printf present; else printf missing_not_extracted; fi)"
printf 'libnpu_runtime_path=%s\n' "$(find -P "$SDK_ROOT" "$DEMO_ROOT" -type f -name 'libnpu_runtime*' -print -quit 2>/dev/null || true)"
REMOTE
