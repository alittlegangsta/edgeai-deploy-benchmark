#!/usr/bin/env bash
set -euo pipefail

WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"
MODE=check

usage() {
  cat <<'EOF'
Usage: stage_vm_vendor_inputs.sh [--check|--execute]

  --check     Inspect sources and destinations without changing the VM (default).
  --execute   Create the approved workspace and copy the two inputs safely.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --check) MODE=check ;;
    --execute) MODE=execute ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: VM SSH wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi

if [[ "$MODE" == check ]]; then
  "$WRAPPER" '
set +e
SDK_SRC="/mnt/hgfs/fpga_info/sdk.2025.7.tar.gz"
DEMO_SRC="/mnt/hgfs/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/05-5_NPU演示"
ROOT="/home/uisrc/vendor/anlogic"
SDK_DST="$ROOT/packages/sdk.2025.7.tar.gz"
DEMO_DST="$ROOT/demos/milianke_npu_demo"

tree_digest() (
  cd "$1"
  find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
)

echo "mode=check"
echo "source_paths:"
if [ -f "$SDK_SRC" ]; then
  stat --printf="sdk_size_bytes=%s\\nsdk_mtime=%y\\n" "$SDK_SRC"
  sha256sum "$SDK_SRC"
else
  echo "sdk_source=NOT_FOUND"
fi
if [ -d "$DEMO_SRC" ]; then
  printf "demo_source_files="; find "$DEMO_SRC" -type f | wc -l
  printf "demo_source_dirs="; find "$DEMO_SRC" -type d | wc -l
  du -sb "$DEMO_SRC"
else
  echo "demo_source=NOT_FOUND"
fi

echo "destination_paths:"
if [ -f "$SDK_DST" ]; then
  stat --printf="sdk_destination_size_bytes=%s\\nsdk_destination_mtime=%y\\n" "$SDK_DST"
  sha256sum "$SDK_DST"
else
  echo "sdk_destination=NOT_FOUND"
fi
if [ -d "$DEMO_DST" ]; then
  printf "demo_destination_files="; find "$DEMO_DST" -type f | wc -l
  printf "demo_destination_dirs="; find "$DEMO_DST" -type d | wc -l
  du -sb "$DEMO_DST"
  if [ -d "$DEMO_SRC" ]; then
    source_tree_digest=$(tree_digest "$DEMO_SRC" | awk "{print \$1}")
    destination_tree_digest=$(tree_digest "$DEMO_DST" | awk "{print \$1}")
    echo "demo_source_tree_digest=$source_tree_digest"
    echo "demo_destination_tree_digest=$destination_tree_digest"
    if [ "$source_tree_digest" = "$destination_tree_digest" ]; then
      echo "demo_destination_content=HASH_MATCH"
    else
      echo "demo_destination_content=HASH_MISMATCH"
    fi
  fi
else
  echo "demo_destination=NOT_FOUND"
fi
echo "workspace_creation=NOT_PERFORMED"
echo "copy=NOT_PERFORMED"
echo "sdk_extraction=NOT_PERFORMED"
echo "demo_execution=NOT_PERFORMED"
echo "putty=windows_only_not_staged"
'
  exit 0
fi

"$WRAPPER" '
set -euo pipefail
SDK_SRC="/mnt/hgfs/fpga_info/sdk.2025.7.tar.gz"
DEMO_SRC="/mnt/hgfs/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/05-5_NPU演示"
ROOT="/home/uisrc/vendor/anlogic"
SDK_DST="$ROOT/packages/sdk.2025.7.tar.gz"
DEMO_DST="$ROOT/demos/milianke_npu_demo"
LOG_DIR="$ROOT/logs/input_staging"

test -f "$SDK_SRC" || { echo "SDK source not found: $SDK_SRC" >&2; exit 10; }
test -d "$DEMO_SRC" || { echo "NPU demo source not found: $DEMO_SRC" >&2; exit 11; }

mkdir -p "$ROOT/packages" "$ROOT/sdk" "$ROOT/demos" "$ROOT/builds" "$ROOT/logs" "$ROOT/manifests" "$LOG_DIR"

sdk_source_sha256=$(sha256sum "$SDK_SRC" | awk "{print \$1}")
if [ -e "$SDK_DST" ]; then
  test -f "$SDK_DST" || { echo "SDK destination is not a regular file: $SDK_DST" >&2; exit 12; }
  sdk_destination_sha256=$(sha256sum "$SDK_DST" | awk "{print \$1}")
  [ "$sdk_source_sha256" = "$sdk_destination_sha256" ] || {
    echo "SDK destination exists with a different SHA256" >&2
    exit 13
  }
  sdk_copy_status="skipped_existing_hash_match"
else
  cp -p -- "$SDK_SRC" "$SDK_DST"
  sdk_destination_sha256=$(sha256sum "$SDK_DST" | awk "{print \$1}")
  [ "$sdk_source_sha256" = "$sdk_destination_sha256" ] || {
    echo "SDK copy SHA256 verification failed" >&2
    exit 14
  }
  sdk_copy_status="copied_and_verified"
fi

tree_digest() (
  cd "$1"
  find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
)

if [ -e "$DEMO_DST" ]; then
  test -d "$DEMO_DST" || { echo "Demo destination is not a directory: $DEMO_DST" >&2; exit 15; }
  source_tree_digest=$(tree_digest "$DEMO_SRC" | awk "{print \$1}")
  destination_tree_digest=$(tree_digest "$DEMO_DST" | awk "{print \$1}")
  [ "$source_tree_digest" = "$destination_tree_digest" ] || {
    echo "Demo destination exists with a different content digest" >&2
    exit 16
  }
  demo_copy_status="skipped_existing_content_match"
else
  cp -a -- "$DEMO_SRC" "$DEMO_DST"
  source_tree_digest=$(tree_digest "$DEMO_SRC" | awk "{print \$1}")
  destination_tree_digest=$(tree_digest "$DEMO_DST" | awk "{print \$1}")
  [ "$source_tree_digest" = "$destination_tree_digest" ] || {
    echo "Demo copy content digest verification failed" >&2
    exit 17
  }
  demo_copy_status="copied_and_verified"
fi

{
  echo "=== VM environment ==="
  date --iso-8601=seconds
  whoami
  hostname
  uname -a
  uname -m
  cat /etc/os-release
  free -h
  df -h "$HOME"
  ip -4 addr
  systemctl is-active ssh || true
  gcc --version || true
  g++ --version || true
  make --version || true
  cmake --version || true
  python3 --version || true
  tar --version || true
  git --version || true
} > "$LOG_DIR/vm_environment.txt"

{
  echo "sdk_source=$SDK_SRC"
  echo "sdk_destination=$SDK_DST"
  echo "sdk_source_sha256=$sdk_source_sha256"
  echo "sdk_destination_sha256=$sdk_destination_sha256"
  echo "sdk_copy_status=$sdk_copy_status"
} > "$LOG_DIR/sdk_sha256.txt"

set +e
tar tzf "$SDK_DST" | head -n 200 > "$LOG_DIR/sdk_archive_preview.txt"
tar_status=${PIPESTATUS[0]}
set -e
printf "tar_tzf_exit_code=%s\\n" "$tar_status" >> "$LOG_DIR/sdk_archive_preview.txt"

find "$DEMO_DST" -mindepth 1 -maxdepth 3 -printf "%y %p\\n" | sort > "$LOG_DIR/npu_demo_tree.txt"
{
  echo "source=$DEMO_SRC"
  echo "destination=$DEMO_DST"
  printf "source_file_count="; find "$DEMO_SRC" -type f | wc -l
  printf "source_dir_count="; find "$DEMO_SRC" -type d | wc -l
  du -sb "$DEMO_SRC"
  printf "destination_file_count="; find "$DEMO_DST" -type f | wc -l
  printf "destination_dir_count="; find "$DEMO_DST" -type d | wc -l
  du -sb "$DEMO_DST"
  echo "source_tree_digest=$source_tree_digest"
  echo "destination_tree_digest=$destination_tree_digest"
} > "$LOG_DIR/npu_demo_summary.txt"

{
  echo "# VM vendor input staging"
  echo
  echo "- SDK copy: $sdk_copy_status"
  echo "- SDK state: staged_not_extracted"
  echo "- NPU Demo copy: $demo_copy_status"
  echo "- NPU Demo state: staged_not_executed"
  echo "- Putty: windows_only"
  echo "- SDK extraction: not performed"
  echo "- Vendor scripts and demos: not executed"
  echo "- Source files were not modified"
} > "$LOG_DIR/staging_summary.md"

echo "execute_complete"
echo "sdk_state=staged_not_extracted"
echo "demo_state=staged_not_executed"
echo "sdk_source_sha256=$sdk_source_sha256"
echo "sdk_destination_sha256=$sdk_destination_sha256"
echo "demo_source_tree_digest=$source_tree_digest"
echo "demo_destination_tree_digest=$destination_tree_digest"
'
