#!/usr/bin/env bash
set -euo pipefail

# Read-only local SDK inventory helper. It never installs, extracts, builds, or
# modifies a source tree.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
PATHS_FILE="$REPO_ROOT/.knowledge/local_paths.yaml"

read_local_path() {
    local key=$1
    if [[ ! -f "$PATHS_FILE" ]]; then
        return 0
    fi
    awk -F': ' -v wanted="$key" '
        $1 == wanted {
            value=$2
            gsub(/^"|"$/, "", value)
            print value
            exit
        }
    ' "$PATHS_FILE"
}

MILIANKE_ROOT=${EDGEAI_MILIANKE_ROOT:-"$(read_local_path milianke_source_root)"}

section() {
    printf '\n===== %s =====\n' "$1"
}

run_optional() {
    local label=$1
    shift
    printf '\n-- %s --\n' "$label"
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'command=%s\nstatus=NOT_FOUND\n' "$1"
        return 0
    fi
    set +e
    "$@"
    local rc=$?
    set -e
    printf 'exit_code=%d\n' "$rc"
}

check_path() {
    local label=$1
    local path=$2
    printf '%s: ' "$label"
    if [[ -d "$path" ]]; then
        printf 'PRESENT_DIRECTORY '
        stat --printf='type=%F size=%s mtime=%y path=%n\n' "$path"
    elif [[ -e "$path" ]]; then
        if [[ -x "$path" ]]; then
            printf 'PRESENT_EXECUTABLE '
        else
            printf 'PRESENT '
        fi
        stat --printf='type=%F size=%s mtime=%y path=%n\n' "$path"
    else
        printf 'NOT_FOUND path=%s\n' "$path"
    fi
}

section "Audit metadata"
printf 'script=%s\nrepo_root=%s\npaths_file=%s\n' "$SCRIPT_DIR/audit_local_sdk.sh" "$REPO_ROOT" "$PATHS_FILE"
printf 'milianke_source_root=%s\n' "${MILIANKE_ROOT:-unknown}"
printf 'EDGEAI_SDK_ROOT=%s\n' "${EDGEAI_SDK_ROOT:-not_set}"

section "SDK candidate paths"
if [[ -z "${MILIANKE_ROOT:-}" || ! -d "$MILIANKE_ROOT" ]]; then
    printf 'milianke_root_status=NOT_FOUND\n'
else
    printf 'milianke_root_status=PRESENT\n'
    check_path "secondary_soc_sdk" "$MILIANKE_ROOT/01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk"
    check_path "soc_linux_course_tree" "$MILIANKE_ROOT/03_demo/3-4_ex_soc_linux"
    check_path "linux_base_archive" "$MILIANKE_ROOT/03_demo/3-4_ex_soc_linux/01_ex_linux_base_F3P_DR1M90G.zip"
    check_path "linux_driver_archive" "$MILIANKE_ROOT/03_demo/3-4_ex_soc_linux/02_ex_linux_drive_F3P_DR1M90G.zip"
    check_path "secondary_demo_archive" "$MILIANKE_ROOT/01_start/02_start_Linux/04_secondary_developmemt/demo.zip"
fi

if [[ -n "${EDGEAI_SDK_ROOT:-}" ]]; then
    check_path "configured_sdk_root" "$EDGEAI_SDK_ROOT"
else
    printf 'configured_sdk_root: NOT_CONFIGURED\n'
fi

section "Candidate version and environment files"
if [[ -n "${MILIANKE_ROOT:-}" ]]; then
    for relative in \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/.metadata/version.ini" \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/VERSION" \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/version" \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/envsetup.sh" \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/setenv.sh" \
        "01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk/build.sh" \
        "03_demo/3-4_ex_soc_linux/VERSION" \
        "03_demo/3-4_ex_soc_linux/envsetup.sh" \
        "03_demo/3-4_ex_soc_linux/setenv.sh" \
        "03_demo/3-4_ex_soc_linux/build.sh"; do
        file="$MILIANKE_ROOT/$relative"
        if [[ -f "$file" ]]; then
            printf '\nfile=%s\n' "$file"
            stat --printf='size=%s mtime=%y\n' "$file"
            sed -n '1,80p' "$file"
        fi
    done
else
    printf 'NOT_FOUND: no Milianke root configured\n'
fi

section "Cross compiler discovery"
for compiler_name in \
    aarch64-linux-gnu-gcc \
    aarch64-none-linux-gnu-gcc \
    aarch64-buildroot-linux-gnu-gcc \
    aarch64-linux-gnu-g++; do
    if compiler_path=$(command -v "$compiler_name" 2>/dev/null); then
        printf '\ncompiler=%s path=%s\n' "$compiler_name" "$compiler_path"
        run_optional "compiler --version" "$compiler_path" --version
        run_optional "compiler -dumpmachine" "$compiler_path" -dumpmachine
        run_optional "compiler -print-sysroot" "$compiler_path" -print-sysroot
    else
        printf 'compiler=%s status=NOT_FOUND\n' "$compiler_name"
    fi
done
for documented in \
    /home/uisrc/uisrc-lab-anlogic/tools/aarch64-linux/bin/aarch64-linux-gnu-gcc \
    /home/uisrc/uisrc-lab-anlogic/tools/aarch64-linux/bin/aarch64-linux-gnu-g++ \
    /opt/toolchain/arm-gnu-toolchain-12.3.rel1-x86_64-aarch64-none-elf/bin/aarch64-none-elf-gcc \
    /opt/toolchain/13.2/arm-gnu-toolchain-13.2.Rel1-x86_64-arm-none-eabi/bin/arm-none-eabi-gcc; do
    check_path "documented_compiler" "$documented"
done

section "Host build tools (context only)"
for command_name in gcc g++ cmake ninja make pkg-config; do
    run_optional "host command --version" "$command_name" --version
done

section "Expected SDK layout"
SDK_ROOTS=()
HAS_SDK_ROOT=0
if [[ -n "${EDGEAI_SDK_ROOT:-}" ]]; then
    SDK_ROOTS+=("$EDGEAI_SDK_ROOT")
    HAS_SDK_ROOT=1
fi
if [[ -n "${MILIANKE_ROOT:-}" ]]; then
    SDK_ROOTS+=(
        "$MILIANKE_ROOT/01_start/02_start_Linux/04_secondary_developmemt/demo/soc_sdk"
        "$MILIANKE_ROOT/03_demo/3-4_ex_soc_linux"
    )
    HAS_SDK_ROOT=1
fi
if ((HAS_SDK_ROOT == 0)); then
    printf 'NOT_FOUND: no candidate SDK roots\n'
else
    for sdk in "${SDK_ROOTS[@]}"; do
        printf '\nroot=%s\n' "$sdk"
        for relative in \
            toolchains \
            toolchains/aarch64-linux \
            buildroot \
            device \
            device/output \
            sysroot \
            rootfs \
            envsetup.sh \
            setenv.sh \
            toolchain.cmake \
            pkg-config; do
            check_path "$relative" "$sdk/$relative"
        done
    done
fi

section "OpenCV and linker inventory"
if command -v pkg-config >/dev/null 2>&1; then
    run_optional "pkg-config --modversion opencv4" pkg-config --modversion opencv4
    run_optional "pkg-config --cflags opencv4" pkg-config --cflags opencv4
    run_optional "pkg-config --libs opencv4" pkg-config --libs opencv4
else
    printf 'pkg-config=NOT_FOUND\n'
fi
if command -v ldconfig >/dev/null 2>&1; then
    printf '\n-- ldconfig filtered entries --\n'
    set +e
    ldconfig -p 2>/dev/null | grep -Ei 'opencv|armnn|npu|stdc\+\+|gomp|pthread'
    rc=${PIPESTATUS[0]}
    set -e
    printf 'ldconfig_exit_code=%d\n' "$rc"
else
    printf 'ldconfig=NOT_FOUND\n'
fi

section "Read-only boundary"
printf 'archive_extraction=NOT_RUN\ncompilation=NOT_RUN\ndemo_execution=NOT_RUN\nnetwork=NOT_USED\ngit_lfs_download=NOT_RUN\nqmd_embed=NOT_RUN\nqmd_query=NOT_RUN\nsource_modification=NOT_RUN\n'
