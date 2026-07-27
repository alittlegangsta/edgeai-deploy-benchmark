#!/usr/bin/env bash
# Prepare the already-built AArch64 hello programs for a later board test.
# This script only inspects/copies files in the Anlogic VM and VMware share;
# it never connects to a board and never executes a target ELF.
set -euo pipefail

WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: VM wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi

"$WRAPPER" 'bash -s' <<'REMOTE'
set -euo pipefail

BUILD_ROOT=/home/uisrc/vendor/anlogic/builds
SOURCE_ROOT="$BUILD_ROOT/toolchain_smoke"
PACKAGE="$BUILD_ROOT/board_smoke_package"
SHARED=/mnt/hgfs/fpga_info/_generated/board_smoke_package

[[ -d "$SOURCE_ROOT" ]] || { printf 'ERROR: source build directory not found: %s\n' "$SOURCE_ROOT" >&2; exit 1; }
mkdir -p "$PACKAGE" "$SHARED"

static_candidate=''
c_dynamic_candidate=''
cpp_dynamic_candidate=''

audit_candidate() {
  local path=$1
  local kind
  kind="$(file -b "$path")"
  case "$kind" in
    *'ELF 64-bit'*'ARM aarch64'*) ;;
    *) return 0 ;;
  esac

  printf '\n=== candidate: %s ===\n' "$path"
  printf 'file: '
  file "$path"
  printf 'sha256: '
  sha256sum "$path"
  printf '%s\n' '-- readelf -h --'
  readelf -h "$path"
  printf '%s\n' '-- readelf -l --'
  readelf -l "$path"

  if [[ "$kind" == *'statically linked'* ]]; then
    static_candidate="$path"
    printf 'classification=static_c\n'
    if dynamic_output="$(readelf -d "$path" 2>&1)"; then
      status=0
    else
      status=$?
    fi
    printf '%s\n' "$dynamic_output"
    printf 'readelf_dynamic_exit=%s\n' "$status"
    if printf '%s\n' "$dynamic_output" | grep -Eq 'NEEDED|Dynamic section'; then
      printf 'ERROR: static candidate unexpectedly has dynamic entries\n' >&2
      return 1
    fi
    return 0
  fi

  if ! readelf -lW "$path" | grep -Fq '/lib/ld-linux-aarch64.so.1'; then
    printf 'ERROR: dynamic candidate has unexpected interpreter\n' >&2
    return 1
  fi
  printf '%s\n' '-- readelf -d --'
  readelf -d "$path"
  if readelf -d "$path" | grep -Fq 'libstdc++.so.6'; then
    cpp_dynamic_candidate="$path"
    printf 'classification=dynamic_cpp\n'
  else
    c_dynamic_candidate="$path"
    printf 'classification=dynamic_c\n'
  fi
}

while IFS= read -r -d '' candidate; do
  audit_candidate "$candidate"
done < <(find "$SOURCE_ROOT" -maxdepth 2 -type f -perm -111 -print0 | sort -z)

[[ -n "$static_candidate" ]] || { echo 'ERROR: no static AArch64 ELF found' >&2; exit 1; }
[[ -n "$c_dynamic_candidate" ]] || { echo 'ERROR: no C dynamic AArch64 ELF found' >&2; exit 1; }
[[ -n "$cpp_dynamic_candidate" ]] || { echo 'ERROR: no C++ dynamic AArch64 ELF found' >&2; exit 1; }

declare -A source_for=(
  [hello_c_static]="$static_candidate"
  [hello_c_dynamic]="$c_dynamic_candidate"
  [hello_cpp_dynamic]="$cpp_dynamic_candidate"
)

for existing in "$PACKAGE"/*; do
  [[ -e "$existing" ]] || continue
  case "$(basename "$existing")" in
    hello_c_static|hello_c_dynamic|hello_cpp_dynamic|SHA256SUMS|BOARD_RUN_ORDER.txt|board_probe.sh|README.txt) ;;
    *) printf 'ERROR: unexpected existing package entry: %s\n' "$existing" >&2; exit 1 ;;
  esac
done

for name in hello_c_static hello_c_dynamic hello_cpp_dynamic; do
  source_path="${source_for[$name]}"
  destination="$PACKAGE/$name"
  source_sha="$(sha256sum "$source_path" | awk '{print $1}')"
  if [[ -e "$destination" ]]; then
    destination_sha="$(sha256sum "$destination" | awk '{print $1}')"
    [[ "$source_sha" == "$destination_sha" ]] || {
      printf 'ERROR: package hash mismatch for %s\n' "$name" >&2
      exit 1
    }
    printf 'skip_same_hash=%s\n' "$name"
  else
    cp -p "$source_path" "$destination"
    printf 'copied=%s\n' "$name"
  fi
done

# Keep the package-side ELF metadata executable. The Windows shared copy may
# not preserve Unix mode bits, so the board staging helper must repeat the
# checksum -> chmod -> checksum sequence after transfer.
declare -A package_hash_before=()
for name in hello_c_static hello_c_dynamic hello_cpp_dynamic; do
  package_hash_before[$name]="$(sha256sum "$PACKAGE/$name" | awk '{print $1}')"
done
chmod 0755 "$PACKAGE/hello_c_static" "$PACKAGE/hello_c_dynamic" "$PACKAGE/hello_cpp_dynamic"
for name in hello_c_static hello_c_dynamic hello_cpp_dynamic; do
  package_hash_after="$(sha256sum "$PACKAGE/$name" | awk '{print $1}')"
  [[ "${package_hash_before[$name]}" == "$package_hash_after" ]] || {
    printf 'ERROR: chmod changed package hash for %s\n' "$name" >&2
    exit 1
  }
  printf 'package_permission=0755 hash_unchanged=%s\n' "$name"
done

cat > "$PACKAGE/BOARD_RUN_ORDER.txt" <<'ORDER'
Board smoke execution order (manual board step; this package does not run it)

1. After transfer, run `sha256sum -c SHA256SUMS`.
2. Run `chmod 0755 hello_c_static hello_c_dynamic hello_cpp_dynamic`.
3. Run `sha256sum -c SHA256SUMS` again; chmod changes metadata only.
4. Run hello_c_static first and collect its exit code.
5. Before dynamic programs, inspect the board dynamic loader and required libc.
6. Run hello_c_dynamic second and collect its exit code.
7. Run hello_cpp_dynamic last and collect its exit code.
8. Stop immediately if any step fails; do not continue to later programs.

The package was prepared on the VM and no target ELF was executed during
preparation.
ORDER

cat > "$PACKAGE/board_probe.sh" <<'PROBE'
#!/usr/bin/env bash
set -u
section() { printf '\n=== %s ===\n' "$1"; }
run_cmd() {
  label=$1; shift; section "$label"
  if command -v "$1" >/dev/null 2>&1; then
    "$@" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$1"
  fi
}
run_path() {
  label=$1; path=$2; section "$label"
  if [ -e "$path" ] || [ -L "$path" ]; then
    ls -l "$path" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$path"
  fi
}
section 'identity'
run_cmd date date
run_cmd hostname hostname
section 'kernel and operating system'
run_cmd uname uname -a
run_cmd architecture uname -m
run_cmd os_release cat /etc/os-release
run_cmd proc_version cat /proc/version
section 'cpu summary'
if command -v awk >/dev/null 2>&1; then
  awk '/^processor[[:space:]]*:/ || /^model name[[:space:]]*:/ || /^CPU implementer[[:space:]]*:/ || /^CPU architecture[[:space:]]*:/ || /^CPU part[[:space:]]*:/ || /^Features[[:space:]]*:/ { print }' /proc/cpuinfo 2>&1 || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: awk\n'
fi
run_cmd cpu_count getconf _NPROCESSORS_ONLN
section 'libc and loader'
run_cmd libc_version getconf GNU_LIBC_VERSION
run_cmd ldd_version ldd --version
run_path dynamic_loader /lib/ld-linux-aarch64.so.1
run_path libstdcxx /usr/lib/libstdc++.so
run_path libgcc /usr/lib/libgcc_s.so
section 'memory and storage'
run_cmd free free -h
run_cmd disk df -h
section 'mounts (credential fields redacted)'
if command -v mount >/dev/null 2>&1; then
  mount 2>&1 | sed -e 's/password=[^, ]*/password=<redacted>/g' -e 's/passwd=[^, ]*/passwd=<redacted>/g' -e 's/credentials=[^, ]*/credentials=<redacted>/g' -e 's/username=[^, ]*/username=<redacted>/g' -e 's/user=[^, ]*/user=<redacted>/g' || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: mount\n'
fi
section 'network'
run_cmd ipv4 ip -4 addr
if command -v ss >/dev/null 2>&1; then
  section 'tcp 22 listener'
  ss -ltn 2>&1 | awk '$4 ~ /(^|:)22$/ { print }' || printf 'exit_code=%s\n' "$?"
elif command -v netstat >/dev/null 2>&1; then
  section 'tcp 22 listener'
  netstat -ltn 2>&1 | awk '$4 ~ /(^|:)22$/ { print }' || printf 'exit_code=%s\n' "$?"
else
  section 'tcp 22 listener'
  printf 'NOT_AVAILABLE: ss/netstat\n'
fi
section 'process access services'
if command -v ps >/dev/null 2>&1; then
  ps 2>&1 | grep -E '[s]shd|[d]ropbear' || printf 'no sshd/dropbear process found\n'
else
  printf 'NOT_AVAILABLE: ps\n'
fi
section 'npu device nodes'
for path in /dev/hard_npu /dev/soft_npu; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    ls -l "$path" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$path"
  fi
done
section 'loaded modules'
run_cmd lsmod lsmod
section 'npu kernel modules on disk'
if command -v find >/dev/null 2>&1 && [ -d /lib/modules ]; then
  find /lib/modules -type f \( -iname '*npu*.ko' -o -iname '*cma*.ko' \) -print 2>&1 || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: /lib/modules or find\n'
fi
PROBE
chmod 0755 "$PACKAGE/board_probe.sh"

cat > "$PACKAGE/README.txt" <<'README'
Anlogic DR1M90 user-space toolchain smoke package

This package contains prebuilt AArch64 ELF files from the VM toolchain smoke
build. It was prepared without connecting to a board and without executing any
target ELF.

Run board_probe.sh first. It is read-only and reports OS, CPU, libc/loader,
memory/storage, network/SSH, NPU device nodes and NPU module filenames. It does
not install software, load modules, or run NPU code. Mount credential fields
are redacted.

Run order:
  1. After transfer, run: sha256sum -c SHA256SUMS
  2. Run: chmod 0755 hello_c_static hello_c_dynamic hello_cpp_dynamic
  3. Run: sha256sum -c SHA256SUMS again; chmod changes metadata only.
  4. hello_c_static; record its exit code.
  5. Inspect the board loader and libc before dynamic binaries.
  6. hello_c_dynamic; record its exit code.
  7. hello_cpp_dynamic; record its exit code.
  8. Stop after any failure.

SHA256SUMS covers exactly the three ELF files and board_probe.sh.
README

tmp_sums="$PACKAGE/.SHA256SUMS.tmp"
(
  cd "$PACKAGE"
  sha256sum hello_c_static hello_c_dynamic hello_cpp_dynamic board_probe.sh > "$tmp_sums"
)
mv "$tmp_sums" "$PACKAGE/SHA256SUMS"

for existing in "$SHARED"/*; do
  [[ -e "$existing" ]] || continue
  case "$(basename "$existing")" in
    hello_c_static|hello_c_dynamic|hello_cpp_dynamic|SHA256SUMS|BOARD_RUN_ORDER.txt|board_probe.sh|README.txt) ;;
    *) printf 'ERROR: unexpected existing shared entry: %s\n' "$existing" >&2; exit 1 ;;
  esac
done

for name in hello_c_static hello_c_dynamic hello_cpp_dynamic SHA256SUMS BOARD_RUN_ORDER.txt board_probe.sh README.txt; do
  source_path="$PACKAGE/$name"
  destination="$SHARED/$name"
  if [[ -e "$destination" ]]; then
    if [[ "$name" == hello_c_static || "$name" == hello_c_dynamic || "$name" == hello_cpp_dynamic ]]; then
      source_sha="$(sha256sum "$source_path" | awk '{print $1}')"
      destination_sha="$(sha256sum "$destination" | awk '{print $1}')"
      [[ "$source_sha" == "$destination_sha" ]] || {
        printf 'ERROR: shared-copy hash mismatch for ELF %s\n' "$name" >&2
        exit 1
      }
      printf 'shared_skip_same_hash=%s\n' "$name"
    else
      cp -p "$source_path" "$destination"
      printf 'shared_refreshed_generated=%s\n' "$name"
    fi
  else
    cp -p "$source_path" "$destination"
    printf 'shared_copied=%s\n' "$name"
  fi
done

printf '\n=== package verification ===\n'
printf 'package=%s\n' "$PACKAGE"
printf 'shared=%s\n' "$SHARED"
printf 'package_regular_files=%s\n' "$(find "$PACKAGE" -maxdepth 1 -type f | wc -l)"
printf 'package_elf_files=%s\n' "$(find "$PACKAGE" -maxdepth 1 -type f -perm -111 -print0 | xargs -0 -r file -b | grep -c 'ELF 64-bit.*ARM aarch64')"
printf '%s\n' '-- package hashes --'
(cd "$PACKAGE" && sha256sum hello_c_static hello_c_dynamic hello_cpp_dynamic board_probe.sh SHA256SUMS BOARD_RUN_ORDER.txt README.txt)
printf '%s\n' '-- shared hashes --'
(cd "$SHARED" && sha256sum hello_c_static hello_c_dynamic hello_cpp_dynamic board_probe.sh SHA256SUMS BOARD_RUN_ORDER.txt README.txt)
REMOTE
