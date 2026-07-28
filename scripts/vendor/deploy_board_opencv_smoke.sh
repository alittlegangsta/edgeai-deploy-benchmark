#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PACKAGE_LOCAL="${ANLOGIC_OPENCV_PACKAGE_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/board_opencv_smoke}"
PACKAGE_WINDOWS="${ANLOGIC_OPENCV_PACKAGE_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/board_opencv_smoke}"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
BOARD_SCP="${ANLOGIC_BOARD_SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
BOARD_KEY="${ANLOGIC_BOARD_KEY_WINDOWS:-C:/Users/Administrator/.ssh/anlogic_board_ed25519}"
BOARD_DEST="/tmp/edgeai_opencv_smoke"
LOG_DIR="$REPO_ROOT/results/logs/vendor/board_opencv"
IMAGE_OUT="$REPO_ROOT/results/images/anlogic_opencv_smoke.png"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

[[ -x "$BOARD_SSH" ]] || { echo "Board SSH wrapper is not executable: $BOARD_SSH" >&2; exit 1; }
[[ -x "$BOARD_SCP" ]] || { echo "Windows scp is not executable: $BOARD_SCP" >&2; exit 1; }
[[ -d "$PACKAGE_LOCAL" ]] || { echo "Local package is missing: $PACKAGE_LOCAL" >&2; exit 1; }
[[ -f "$PACKAGE_LOCAL/SHA256SUMS" ]] || { echo "SHA256SUMS is missing" >&2; exit 1; }
mkdir -p "$LOG_DIR" "$(dirname "$IMAGE_OUT")"

(
  cd "$PACKAGE_LOCAL"
  sha256sum -c SHA256SUMS
) 2>&1 | tee "$LOG_DIR/opencv_package_checksum_local.log"

set +e
"$BOARD_SCP" -i "$BOARD_KEY" -r "$PACKAGE_WINDOWS" \
  "root@192.168.50.2:/tmp/edgeai_opencv_smoke.new" \
  2>&1 | tee "$LOG_DIR/opencv_package_transfer.log"
scp_rc=${PIPESTATUS[0]}
set -e
[[ "$scp_rc" -eq 0 ]] || { echo "board package transfer failed: $scp_rc" >&2; exit "$scp_rc"; }

set +e
"$BOARD_SSH" 'sh -s' <<'REMOTE' 2>&1 | tee "$LOG_DIR/opencv_board_runtime.log"
set -u
NEW=/tmp/edgeai_opencv_smoke.new
DEST=/tmp/edgeai_opencv_smoke
if [ ! -d "$NEW" ]; then
  echo "missing transfer directory: $NEW" >&2
  exit 1
fi
if [ -e "$DEST" ]; then
  echo "refusing to overwrite existing board directory: $DEST" >&2
  exit 1
fi
mv "$NEW" "$DEST"
cd "$DEST" || exit 1
echo '=== package files ==='
find . -maxdepth 2 -type f -print | sort
echo '=== checksum before chmod ==='
sha256sum -c SHA256SUMS || exit $?
echo '=== hashes before chmod ==='
sha256sum opencv_board_smoke run.sh
chmod 0755 opencv_board_smoke run.sh
echo '=== modes after chmod ==='
ls -ln opencv_board_smoke run.sh
echo '=== checksum after chmod ==='
sha256sum -c SHA256SUMS || exit $?
echo 'chmod_changes_metadata_only=true'
echo '=== runtime ==='
out=/tmp/anlogic_board_audit/opencv_smoke.stdout
err=/tmp/anlogic_board_audit/opencv_smoke.stderr
mkdir -p /tmp/anlogic_board_audit
if command -v timeout >/dev/null 2>&1; then
  timeout 10s sh run.sh >"$out" 2>"$err"
  rc=$?
else
  sh run.sh >"$out" 2>"$err"
  rc=$?
fi
echo 'stdout_begin'
cat "$out"
echo 'stdout_end'
echo 'stderr_begin'
cat "$err"
echo 'stderr_end'
echo "exit_code=$rc"
if [ "$rc" -eq 0 ] && [ -s opencv_smoke.png ]; then
  echo 'image_status=PASS'
  sha256sum opencv_smoke.png
else
  echo 'image_status=FAIL'
fi
exit "$rc"
REMOTE
board_rc=${PIPESTATUS[0]}
set -e
[[ "$board_rc" -eq 0 ]] || { echo "board OpenCV smoke failed: $board_rc" >&2; exit "$board_rc"; }

"$BOARD_SCP" -i "$BOARD_KEY" \
  "root@192.168.50.2:$BOARD_DEST/opencv_smoke.png" "$IMAGE_OUT" \
  2>&1 | tee "$LOG_DIR/opencv_image_transfer.log"

"$PYTHON_BIN" - <<'PY' 2>&1 | tee "$LOG_DIR/opencv_image_local_validation.log"
from pathlib import Path
import hashlib
import cv2

path = Path("results/images/anlogic_opencv_smoke.png")
image = cv2.imread(str(path), cv2.IMREAD_COLOR)
assert image is not None
assert image.shape == (240, 320, 3), image.shape
assert path.stat().st_size > 0
print("image_path:", path)
print("width:", image.shape[1])
print("height:", image.shape[0])
print("channels:", image.shape[2])
print("size_bytes:", path.stat().st_size)
print("sha256:", hashlib.sha256(path.read_bytes()).hexdigest())
print("opencv_image_validation: PASS")
PY
