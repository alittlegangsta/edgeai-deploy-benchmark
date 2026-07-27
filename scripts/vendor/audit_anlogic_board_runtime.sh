#!/usr/bin/env bash
# Anlogic DR1M90 board runtime audit. Default mode is read-only. The optional
# smoke-permission mode changes only the three authorized ELF permission bits;
# it never installs, loads modules, runs vendor demos, writes eMMC, or changes
# any other board state. The SSH wrapper is the only supported board entry point.
set -u

WRAPPER="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
LOG_DIR="${BOARD_AUDIT_LOG_DIR:-results/logs/vendor/board_runtime}"
FIX_SMOKE_PERMISSIONS=0
RUN_SMOKE=0

usage() {
  cat <<'USAGE'
Usage: audit_anlogic_board_runtime.sh [--fix-smoke-permissions|--run-smoke]

Default mode is read-only board runtime probing. --fix-smoke-permissions
performs the approved checksum -> chmod 0755 (three ELF files only) ->
checksum sequence. --run-smoke performs that sequence and then runs the three
ELFs in order, stopping on the first non-zero exit code.
USAGE
}

case "${1:-}" in
  "") ;;
  --fix-smoke-permissions) FIX_SMOKE_PERMISSIONS=1 ;;
  --run-smoke) FIX_SMOKE_PERMISSIONS=1; RUN_SMOKE=1 ;;
  --help|-h) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

if [[ ! -x "$WRAPPER" ]]; then
  printf 'ERROR: board SSH wrapper is not executable: %s\n' "$WRAPPER" >&2
  exit 1
fi
mkdir -p "$LOG_DIR"

run_remote_audit() {
  "$WRAPPER" 'sh -s' <<'REMOTE'
set +u
mkdir -p /tmp/anlogic_board_audit
echo "=== identity ==="
date; uptime; whoami; id; hostname
echo "=== system ==="
uname -a; uname -m; cat /etc/os-release; cat /proc/version
if command -v nproc >/dev/null 2>&1; then nproc; else echo nproc=NOT_AVAILABLE; fi
cat /proc/cpuinfo
echo "=== abi ==="
if command -v ldd >/dev/null 2>&1; then ldd --version; else echo ldd=NOT_AVAILABLE; fi
for p in /lib/ld-linux-aarch64.so.1 /lib/libc.so.6 /lib/libstdc++.so.6 /lib/libgcc_s.so.1; do
  if [ -e "$p" ] || [ -L "$p" ]; then ls -l "$p"; else echo "NOT_PRESENT $p"; fi
done
echo "=== resources ==="
free; df -h; mount; cat /proc/partitions; cat /proc/cmdline
echo "=== network ==="
if command -v ip >/dev/null 2>&1; then ip addr; ip route; ip link; else echo ip=NOT_AVAILABLE; fi
if command -v ss >/dev/null 2>&1; then ss -ltn; else echo ss=NOT_AVAILABLE; fi
ps 2>/dev/null | grep -E '[s]shd|[d]ropbear' || true
echo "=== kernel ==="
dmesg; cat /proc/modules
m="/lib/modules/$(uname -r)"
if [ -f "$m/modules.dep" ]; then grep -iE 'npu|cma|alnpu|hard_npu|soft_npu' "$m/modules.dep" || true; else echo modules_dep=NOT_AVAILABLE; fi
echo "=== npu rootfs search ==="
find / -xdev \( -path /proc -o -path /sys -o -path /dev -o -path /tmp -o -path /run -o -path /mnt/usb_boot -o -path /mnt/usb_rootfs -o -path /mnt/mmcblk1p1 -o -path /mnt/mmcblk1p2 \) -prune -o \( -iname '*npu*' -o -iname '*alnpu*' -o -iname 'hard_npu' -o -iname 'soft_npu' -o -iname 'cma_mem' -o -iname '*.hpf' -o -iname '*.bit' -o -iname '*.ko' -o -iname 'libarmnn*' \) -print 2>/dev/null | sort
echo "=== smoke input ==="
for p in /tmp/board_smoke/hello_c_static /tmp/board_smoke/hello_c_dynamic /tmp/board_smoke/hello_cpp_dynamic; do
  if [ -f "$p" ]; then sha256sum "$p"; else echo "NOT_PRESENT $p"; fi
done
REMOTE
}

fix_smoke_permissions() {
  "$WRAPPER" 'sh -s' <<'REMOTE'
set -eu
cd /tmp/board_smoke
echo "=== smoke checksum before chmod ==="
sha256sum -c SHA256SUMS
echo "=== smoke hashes before chmod ==="
sha256sum hello_c_static hello_c_dynamic hello_cpp_dynamic
echo "=== chmod scope ==="
chmod 0755 hello_c_static hello_c_dynamic hello_cpp_dynamic
ls -ln hello_c_static hello_c_dynamic hello_cpp_dynamic
echo "=== smoke checksum after chmod ==="
sha256sum -c SHA256SUMS
echo "chmod_changes_metadata_only=true"
REMOTE
}

run_smoke() {
  "$WRAPPER" 'sh -s' <<'REMOTE'
set +e
cd /tmp/board_smoke
run_one() {
  p="$1"
  out="/tmp/anlogic_board_audit/${p}.stdout"
  err="/tmp/anlogic_board_audit/${p}.stderr"
  echo "=== $p ==="
  ls -l "$p"
  sha256sum "$p"
  printf "start_time="; date
  if command -v timeout >/dev/null 2>&1; then timeout 5s "./$p" >"$out" 2>"$err"; rc=$?; else "./$p" >"$out" 2>"$err"; rc=$?; fi
  echo "stdout_begin"; cat "$out"; echo "stdout_end"
  echo "stderr_begin"; cat "$err"; echo "stderr_end"
  echo "exit_code=$rc"
  printf "end_time="; date
  return "$rc"
}
run_one hello_c_static || exit $?
run_one hello_c_dynamic || exit $?
run_one hello_cpp_dynamic || exit $?
echo "smoke_sequence=PASS"
REMOTE
}

if [[ "$FIX_SMOKE_PERMISSIONS" -eq 1 ]]; then
  fix_smoke_permissions 2>&1 | tee "$LOG_DIR/board_smoke_permissions_script.log"
  rc=${PIPESTATUS[0]}
  [[ "$rc" -eq 0 ]] || exit "$rc"
fi
if [[ "$RUN_SMOKE" -eq 1 ]]; then
  run_smoke 2>&1 | tee "$LOG_DIR/board_smoke_runtime_script.log"
  rc=${PIPESTATUS[0]}
  [[ "$rc" -eq 0 ]] || exit "$rc"
fi
run_remote_audit 2>&1 | tee "$LOG_DIR/runtime_audit_script.log"
rc=${PIPESTATUS[0]}
printf 'remote_audit_exit_code=%s\n' "$rc" | tee -a "$LOG_DIR/runtime_audit_script.log"
exit "$rc"
