#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"
case "$MODE" in
  --check|--execute) ;;
  *)
    printf 'usage: %s [--check|--execute]\n' "$0" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
BOARD_SCP="${ANLOGIC_BOARD_SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
BOARD_KEY_WINDOWS="${ANLOGIC_BOARD_KEY_WINDOWS:-C:/Users/Administrator/.ssh/anlogic_board_ed25519}"
BOARD_TARGET="${ANLOGIC_BOARD_TARGET:-root@192.168.50.2}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_yolov5n}"
SHARED_WINDOWS="${ANLOGIC_SHARED_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_yolov5n}"
BUILD_OUTPUT="$SHARED_LOCAL/build-output"
PACKAGE_LOCAL="$SHARED_LOCAL/package"
PACKAGE_WINDOWS="$SHARED_WINDOWS/package"
RETURN_LOCAL="$SHARED_LOCAL/returned"
RETURN_WINDOWS="$SHARED_WINDOWS/returned"
REMOTE_NEW="/root/edgeai/yolov5n-ncnn-single-image.new"
REMOTE_DEST="/root/edgeai/yolov5n-ncnn-single-image"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_yolov5n"
EVIDENCE_DIR="$REPO_ROOT/results/evidence/014"
IMAGE_OUT="$REPO_ROOT/results/images/anlogic_arm_ncnn_reference.png"

PARAM="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param"
BIN="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin"
MODEL_MANIFEST="$REPO_ROOT/models/yolov5n-v7.0/ncnn_manifest.json"
CONFIG="$REPO_ROOT/configs/yolov5n_v7_inference.json"
INPUT="$REPO_ROOT/data/samples/images/pc_reference.jpg"

EXPECTED_PARAM="72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
EXPECTED_BIN="658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
EXPECTED_INPUT="625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"

[[ -x "$BOARD_SSH" ]] || { printf 'board SSH wrapper is missing\n' >&2; exit 1; }
[[ -x "$BOARD_SCP" ]] || { printf 'Windows scp is missing\n' >&2; exit 1; }
for required in "$PARAM" "$BIN" "$MODEL_MANIFEST" "$CONFIG" "$INPUT" \
  "$BUILD_OUTPUT/edgeai_ncnn_image" \
  "$BUILD_OUTPUT/lib/libopencv_core.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgproc.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgcodecs.so.407"; do
  [[ -f "$required" ]] || { printf 'required deployment input is missing: %s\n' "$required" >&2; exit 1; }
done

[[ "$(sha256sum "$PARAM" | awk '{print $1}')" == "$EXPECTED_PARAM" ]]
[[ "$(sha256sum "$BIN" | awk '{print $1}')" == "$EXPECTED_BIN" ]]
[[ "$(sha256sum "$INPUT" | awk '{print $1}')" == "$EXPECTED_INPUT" ]]
(
  cd "$BUILD_OUTPUT"
  sha256sum -c BUILD_OUTPUT_SHA256SUMS
)

mkdir -p "$LOG_DIR"
"$BOARD_SSH" '
set -u
echo board_ssh=PASS
hostname
uname -a
uname -m
cat /etc/os-release
ldd --version 2>&1 | head -1
df -h /root
free -h 2>/dev/null || free
' 2>&1 | tee "$LOG_DIR/board_preflight.log"

if [[ "$MODE" == "--check" ]]; then
  printf 'deployment_check=PASS\n'
  exit 0
fi

if [[ ! -e "$PACKAGE_LOCAL" ]]; then
  mkdir -p \
    "$PACKAGE_LOCAL/model" \
    "$PACKAGE_LOCAL/config" \
    "$PACKAGE_LOCAL/input" \
    "$PACKAGE_LOCAL/lib"
  cp "$BUILD_OUTPUT/edgeai_ncnn_image" "$PACKAGE_LOCAL/edgeai_ncnn_image"
  cp "$PARAM" "$PACKAGE_LOCAL/model/yolov5n.ncnn.param"
  cp "$BIN" "$PACKAGE_LOCAL/model/yolov5n.ncnn.bin"
  cp "$MODEL_MANIFEST" "$PACKAGE_LOCAL/model/ncnn_manifest.json"
  cp "$CONFIG" "$PACKAGE_LOCAL/config/yolov5n_v7_inference.json"
  cp "$INPUT" "$PACKAGE_LOCAL/input/pc_reference.jpg"
  cp "$BUILD_OUTPUT/lib/"*.so.407 "$PACKAGE_LOCAL/lib/"

  cat > "$PACKAGE_LOCAL/run.sh" <<'RUN'
#!/bin/sh
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$ROOT/results"
LD_LIBRARY_PATH="$ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
exec "$ROOT/edgeai_ncnn_image" \
  --manifest "$ROOT/model/ncnn_manifest.json" \
  --model-param "$ROOT/model/yolov5n.ncnn.param" \
  --model-bin "$ROOT/model/yolov5n.ncnn.bin" \
  --config "$ROOT/config/yolov5n_v7_inference.json" \
  --input "$ROOT/input/pc_reference.jpg" \
  --output-json "$ROOT/results/anlogic_arm_ncnn_detections.json" \
  --output-image "$ROOT/results/anlogic_arm_ncnn_reference.png" \
  --threads 1
RUN

  python3 - "$PACKAGE_LOCAL" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
files = {}
for path in sorted(item for item in root.rglob("*") if item.is_file()):
    relative = path.relative_to(root).as_posix()
    files[relative] = {
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
payload = {
    "schema_version": 1,
    "task": "014",
    "deployment": "Anlogic DR1 YOLOv5n ncnn single-image CPU/FP32",
    "threads": 1,
    "input_blob": "in0",
    "output_blob": "out0",
    "confidence_threshold": 0.25,
    "nms_iou_threshold": 0.45,
    "files": files,
}
(root / "deployment_manifest.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

  (
    cd "$PACKAGE_LOCAL"
    find . -type f ! -name SHA256SUMS -print0 |
      sort -z |
      xargs -0 sha256sum > SHA256SUMS
  )
fi
(
  cd "$PACKAGE_LOCAL"
  sha256sum -c SHA256SUMS
)

remote_mode="$("$BOARD_SSH" "
if [ -d '$REMOTE_DEST' ]; then
  printf 'reuse'
else
  printf 'transfer'
fi
")"
if [[ "$remote_mode" == "transfer" ]]; then
  set +e
  "$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$PACKAGE_WINDOWS" \
    "$BOARD_TARGET:$REMOTE_NEW" \
    2>&1 | tee "$LOG_DIR/package_transfer.log"
  transfer_rc=${PIPESTATUS[0]}
  set -e
  [[ "$transfer_rc" -eq 0 ]] || exit "$transfer_rc"
elif [[ "$remote_mode" != "reuse" ]]; then
  printf 'unexpected remote deployment mode: %s\n' "$remote_mode" >&2
  exit 1
fi

set +e
"$BOARD_SSH" 'sh -s -- '"$remote_mode" <<'REMOTE' 2>&1 | tee "$LOG_DIR/board_execution.log"
set -u
mode=$1
new=/root/edgeai/yolov5n-ncnn-single-image.new
dest=/root/edgeai/yolov5n-ncnn-single-image
if [ "$mode" = "transfer" ]; then
  if [ ! -d "$new" ]; then
    echo "missing staged package: $new" >&2
    exit 1
  fi
  if [ -e "$dest" ]; then
    echo "refusing to overwrite existing task directory: $dest" >&2
    exit 1
  fi
  mv "$new" "$dest"
elif [ ! -d "$dest" ]; then
  echo "existing task directory is missing: $dest" >&2
  exit 1
fi
cd "$dest" || exit 1
mkdir -p results
echo '=== environment ===' > results/environment.txt
date >> results/environment.txt 2>&1
uname -a >> results/environment.txt 2>&1
uname -m >> results/environment.txt 2>&1
cat /etc/os-release >> results/environment.txt 2>&1
ldd --version >> results/environment.txt 2>&1
free -h >> results/environment.txt 2>&1 || free >> results/environment.txt 2>&1
df -h "$dest" >> results/environment.txt 2>&1

echo '=== hashes before chmod ==='
sha256sum -c SHA256SUMS || exit $?
sha256sum edgeai_ncnn_image run.sh > results/hashes_before_chmod.txt
chmod 0755 edgeai_ncnn_image run.sh
sha256sum edgeai_ncnn_image run.sh > results/hashes_after_chmod.txt
cmp results/hashes_before_chmod.txt results/hashes_after_chmod.txt || exit 1
sha256sum -c SHA256SUMS || exit $?
echo 'chmod_content_hash_validation=PASS'

echo '=== dependencies ==='
LD_LIBRARY_PATH="$dest/lib" ldd "$dest/edgeai_ncnn_image" \
  > results/ldd.txt 2>&1
ldd_rc=$?
cat results/ldd.txt
if [ "$ldd_rc" -ne 0 ] || grep -q 'not found' results/ldd.txt; then
  echo "dependency_validation=FAIL" >&2
  exit 1
fi
echo 'dependency_validation=PASS'

cat > results/run_command.txt <<'CMD'
sh /root/edgeai/yolov5n-ncnn-single-image/run.sh
CMD
set +e
sh "$dest/run.sh" > results/stdout.txt 2> results/stderr.txt
rc=$?
set -e
printf '%s\n' "$rc" > results/exit_code.txt
echo '=== stdout ==='
cat results/stdout.txt
echo '=== stderr ==='
cat results/stderr.txt
echo "exit_code=$rc"
if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
test -s results/anlogic_arm_ncnn_detections.json
test -s results/anlogic_arm_ncnn_reference.png
sha256sum results/anlogic_arm_ncnn_detections.json \
  results/anlogic_arm_ncnn_reference.png > results/output_sha256.txt
cat results/output_sha256.txt
REMOTE
board_rc=${PIPESTATUS[0]}
set -e
[[ "$board_rc" -eq 0 ]] || exit "$board_rc"

if [[ -e "$RETURN_LOCAL" ]]; then
  printf 'refusing to overwrite existing returned evidence: %s\n' "$RETURN_LOCAL" >&2
  exit 1
fi
mkdir -p "$RETURN_LOCAL"
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r \
  "$BOARD_TARGET:$REMOTE_DEST/results/." "$RETURN_WINDOWS" \
  2>&1 | tee "$LOG_DIR/result_transfer.log"

mkdir -p "$EVIDENCE_DIR" "$(dirname "$IMAGE_OUT")"
cp "$RETURN_LOCAL/anlogic_arm_ncnn_detections.json" \
  "$EVIDENCE_DIR/anlogic_arm_ncnn_detections.json"
cp "$RETURN_LOCAL/anlogic_arm_ncnn_reference.png" "$IMAGE_OUT"
for returned_text in "$RETURN_LOCAL/"*.txt; do
  returned_name="$(basename "$returned_text" .txt)"
  cp "$returned_text" "$LOG_DIR/$returned_name.log"
done

python_bin="$REPO_ROOT/.venv/bin/python"
[[ -x "$python_bin" ]] || python_bin=python3
"$python_bin" - "$IMAGE_OUT" <<'PY' | tee "$LOG_DIR/image_decode_validation.log"
import hashlib
import pathlib
import sys
import cv2

path = pathlib.Path(sys.argv[1])
image = cv2.imread(str(path), cv2.IMREAD_COLOR)
if image is None:
    raise SystemExit("image_decode=FAIL")
if image.shape != (960, 1280, 3):
    raise SystemExit(f"unexpected_shape={image.shape}")
print("image_decode=PASS")
print(f"shape={image.shape[1]}x{image.shape[0]}x{image.shape[2]}")
print(f"size_bytes={path.stat().st_size}")
print(f"sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
PY

printf 'deployment_execution=PASS\n'
