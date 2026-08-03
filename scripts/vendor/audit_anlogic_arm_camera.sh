#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
if [[ "$#" -gt 1 ]]; then
  printf 'usage: %s [--check|--execute]\n' "$0" >&2
  exit 2
fi
if [[ "$#" -eq 1 ]]; then MODE="$1"; fi
case "$MODE" in
  --check|--execute) ;;
  *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
LOG_DIR="$ROOT/results/logs/vendor/arm_uvc_camera"
LOG_FILE="$LOG_DIR/camera_audit_$(date -u +%Y%m%dT%H%M%SZ).log"

[[ -x "$BOARD_SSH" ]] || {
  printf 'board SSH wrapper is missing: %s\n' "$BOARD_SSH" >&2
  exit 1
}
mkdir -p "$LOG_DIR"

# This is a read-only board audit. It intentionally does not install tools,
# alter V4L2 controls, or open a capture stream.
"$BOARD_SSH" 'set -u
printf "board_ssh=PASS\n"
printf "hostname="; hostname
printf "uname="; uname -a
printf "architecture="; uname -m
printf "glibc="; ldd --version 2>&1 | head -1
printf "video_nodes=\n"
for node in /dev/video*; do
  [ -e "$node" ] || continue
  printf "node=%s\n" "$node"
  for field in name dev driver modalias; do
    path="/sys/class/video4linux/${node##*/}/$field"
    if [ -r "$path" ]; then printf "%s=" "$field"; cat "$path"; fi
  done
done
printf "tools=\n"
for tool in v4l2-ctl ffmpeg gst-launch-1.0; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf "%s=%s\n" "$tool" "$(command -v "$tool")"
  else
    printf "%s=unavailable\n" "$tool"
  fi
done
printf "load_average="; cat /proc/loadavg
printf "free="; free -h 2>/dev/null || free
printf "camera_audit_status=PASS\n"' 2>&1 | tee "$LOG_FILE"

printf 'camera_audit_log=%s\n' "$LOG_FILE"
printf 'camera_audit_mode=%s\n' "$MODE"
