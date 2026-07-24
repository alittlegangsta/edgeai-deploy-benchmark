#!/usr/bin/env bash
set -euo pipefail

WRAPPER="${ANLOGIC_VM_SSH:-/home/dministrator/bin/anlogic-vm-ssh}"

if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: VM SSH wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi

"$WRAPPER" '
set +e
probe() {
  label="$1"
  shift
  echo "--- $label ---"
  "$@"
  rc=$?
  echo "exit_code=$rc"
}

echo "=== identity ==="
probe whoami whoami
probe home printenv HOME
probe hostname hostname

echo "=== system ==="
probe uname_a uname -a
probe uname_m uname -m
probe os_release cat /etc/os-release

echo "=== resources ==="
probe memory free -h
probe disk df -h "$HOME"
probe ipv4 ip -4 addr
probe ssh_service systemctl is-active ssh

echo "=== tools ==="
probe gcc gcc --version
probe g++ g++ --version
probe make make --version
probe cmake cmake --version
probe python3 python3 --version
probe tar tar --version
probe git git --version

echo "=== shared folders ==="
probe hgfs_root ls -ld /mnt/hgfs
probe hgfs_entries find /mnt/hgfs -mindepth 1 -maxdepth 1 -printf "%M %u %g %s %p\\n"
probe fpga_info ls -ld /mnt/hgfs/fpga_info
probe sdk_source ls -l /mnt/hgfs/fpga_info/sdk.2025.7.tar.gz
probe demo_source ls -ld "/mnt/hgfs/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/05-5_NPU演示"

echo "=== exact input search ==="
find /mnt/hgfs -maxdepth 4 \( -type f -name "sdk.2025.7.tar.gz" -o -type d -name "05-5_NPU演示" \) -print

echo "=== SDK metadata (read-only) ==="
sdk="/mnt/hgfs/fpga_info/sdk.2025.7.tar.gz"
if [ -f "$sdk" ]; then
  stat --printf="size_bytes=%s\\nmtime=%y\\n" "$sdk"
  sha256sum "$sdk"
else
  echo "SDK_NOT_FOUND"
fi

echo "=== NPU demo summary (metadata only) ==="
demo="/mnt/hgfs/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/05-5_NPU演示"
if [ -d "$demo" ]; then
  printf "file_count="; find "$demo" -type f | wc -l
  printf "dir_count="; find "$demo" -type d | wc -l
  du -sb "$demo"
else
  echo "NPU_DEMO_NOT_FOUND"
fi
'
