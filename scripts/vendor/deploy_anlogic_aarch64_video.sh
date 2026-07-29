#!/usr/bin/env bash
set -euo pipefail

MODE="--check"
if [[ "$#" -gt 1 ]]; then
  printf 'usage: %s [--check|--execute]\n' "$0" >&2
  exit 2
fi
if [[ "$#" -eq 1 ]]; then
  MODE="$1"
fi
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
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_video_task020}"
SHARED_WINDOWS="${ANLOGIC_SHARED_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_video_task020}"
BUILD_OUTPUT="$SHARED_LOCAL/build-output"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
PACKAGE_LOCAL="$SHARED_LOCAL/package-$RUN_ID"
PACKAGE_WINDOWS="$SHARED_WINDOWS/package-$RUN_ID"
RETURN_LOCAL="$SHARED_LOCAL/returned-$RUN_ID"
RETURN_WINDOWS="$SHARED_WINDOWS/returned-$RUN_ID"
REMOTE_NEW="/root/edgeai/yolov5n-ncnn-video-file-$RUN_ID.new"
REMOTE_BASE="/root/edgeai/yolov5n-ncnn-video-file"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_video_file"
EVIDENCE_DIR="$REPO_ROOT/results/evidence/020"

PARAM="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param"
BIN="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin"
MODEL_MANIFEST="$REPO_ROOT/models/yolov5n-v7.0/ncnn_manifest.json"
CONFIG="$REPO_ROOT/configs/yolov5n_v7_inference.json"
PROFILE="$REPO_ROOT/configs/runtime_profiles/anlogic-dr1-recommended-dual-thread.json"
INPUT_VIDEO="$REPO_ROOT/data/samples/videos/anlogic_arm_reference.avi"
GOLDEN="$REPO_ROOT/results/acceptance/cpp_ncnn_reference.json"
CONTRACT="$EVIDENCE_DIR/video_contract.json"
VALIDATOR="$REPO_ROOT/scripts/vendor/validate_anlogic_arm_video.py"
OUTPUT_VIDEO="$REPO_ROOT/results/videos/anlogic_arm_ncnn_reference.avi"
OUTPUT_JSON="$EVIDENCE_DIR/video_frame_detections.json"
OUTPUT_ENVIRONMENT="$EVIDENCE_DIR/video_environment.json"

EXPECTED_PARAM="72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
EXPECTED_BIN="658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
EXPECTED_VIDEO="3953653b6364a844e829be68df76fce8ce673add5c4bfaf9176c5fb205e5da49"
EXPECTED_NCNN="bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
EXPECTED_LIBGOMP="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"

[[ -x "$BOARD_SSH" ]] || { printf 'board SSH wrapper is missing\n' >&2; exit 1; }
[[ -x "$BOARD_SCP" ]] || { printf 'Windows scp is missing\n' >&2; exit 1; }
for required in \
  "$PARAM" "$BIN" "$MODEL_MANIFEST" "$CONFIG" "$PROFILE" "$INPUT_VIDEO" \
  "$GOLDEN" "$CONTRACT" "$VALIDATOR" \
  "$BUILD_OUTPUT/edgeai_ncnn_video" \
  "$BUILD_OUTPUT/runtime_build_identity.json" \
  "$BUILD_OUTPUT/BUILD_OUTPUT_SHA256SUMS" \
  "$BUILD_OUTPUT/lib/libopencv_core.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgproc.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgcodecs.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_videoio.so.407" \
  "$BUILD_OUTPUT/lib/libavcodec.so.58" \
  "$BUILD_OUTPUT/lib/libavformat.so.58" \
  "$BUILD_OUTPUT/lib/libavutil.so.56" \
  "$BUILD_OUTPUT/lib/libswscale.so.5" \
  "$BUILD_OUTPUT/lib/libswresample.so.3" \
  "$BUILD_OUTPUT/lib/libx264.so.157" \
  "$BUILD_OUTPUT/lib/libgomp.so.1"; do
  [[ -f "$required" ]] || {
    printf 'required Task 020 deployment input is missing: %s\n' "$required" >&2
    exit 1
  }
done
[[ "$(sha256sum "$PARAM" | awk '{print $1}')" == "$EXPECTED_PARAM" ]]
[[ "$(sha256sum "$BIN" | awk '{print $1}')" == "$EXPECTED_BIN" ]]
[[ "$(sha256sum "$INPUT_VIDEO" | awk '{print $1}')" == "$EXPECTED_VIDEO" ]]
[[ "$(sha256sum "$BUILD_OUTPUT/lib/libgomp.so.1" | awk '{print $1}')" == \
    "$EXPECTED_LIBGOMP" ]]
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
printf "device_tree_model="
if [ -r /proc/device-tree/model ]; then
  tr -d "\000" </proc/device-tree/model
else
  printf unavailable
fi
printf "\n"
df -h /root
cat /proc/loadavg
' 2>&1 | tee "$LOG_DIR/board_video_preflight.log"

if [[ "$MODE" == "--check" ]]; then
  printf 'video_deployment_check=PASS\n'
  exit 0
fi

mkdir -p \
  "$PACKAGE_LOCAL/model" \
  "$PACKAGE_LOCAL/config" \
  "$PACKAGE_LOCAL/input" \
  "$PACKAGE_LOCAL/lib"
cp "$BUILD_OUTPUT/edgeai_ncnn_video" "$PACKAGE_LOCAL/edgeai_ncnn_video"
cp "$PARAM" "$PACKAGE_LOCAL/model/yolov5n.ncnn.param"
cp "$BIN" "$PACKAGE_LOCAL/model/yolov5n.ncnn.bin"
cp "$MODEL_MANIFEST" "$PACKAGE_LOCAL/model/ncnn_manifest.json"
cp "$CONFIG" "$PACKAGE_LOCAL/config/yolov5n_v7_inference.json"
cp "$PROFILE" "$PACKAGE_LOCAL/config/runtime_profile.json"
cp "$GOLDEN" "$PACKAGE_LOCAL/config/cpp_ncnn_reference.json"
cp "$INPUT_VIDEO" "$PACKAGE_LOCAL/input/anlogic_arm_reference.avi"
cp "$BUILD_OUTPUT/runtime_build_identity.json" "$PACKAGE_LOCAL/runtime_build_identity.json"
cp "$BUILD_OUTPUT/lib/"* "$PACKAGE_LOCAL/lib/"

cat > "$PACKAGE_LOCAL/run.sh" <<'RUN'
#!/bin/sh
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$ROOT/results"
LD_LIBRARY_PATH="$ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
OMP_NUM_THREADS=2
export OMP_NUM_THREADS
exec "$ROOT/edgeai_ncnn_video" \
  --manifest "$ROOT/model/ncnn_manifest.json" \
  --model-param "$ROOT/model/yolov5n.ncnn.param" \
  --model-bin "$ROOT/model/yolov5n.ncnn.bin" \
  --config "$ROOT/config/yolov5n_v7_inference.json" \
  --input-video "$ROOT/input/anlogic_arm_reference.avi" \
  --output-video "$ROOT/results/anlogic_arm_ncnn_reference.avi" \
  --output-json "$ROOT/results/video_frame_detections.json" \
  --runtime-profile recommended-dual-thread \
  --threads 2 \
  --output-codec MJPG \
  --max-frames 30
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
    "task": "020",
    "deployment": "Anlogic DR1 YOLOv5n ncnn repeated-frame video CPU/FP32",
    "runtime_profile": "recommended-dual-thread",
    "configured_threads": 2,
    "effective_parallel_backend": "openmp",
    "input_codec": "FFV1 lossless",
    "output_codec": "MJPEG",
    "frame_count": 30,
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
  sha256sum -c SHA256SUMS
)

remote_dest="$REMOTE_BASE"
if "$BOARD_SSH" "test -e '$remote_dest'"; then
  remote_dest="$REMOTE_BASE-$RUN_ID"
fi
"$BOARD_SSH" "test ! -e '$REMOTE_NEW'; mkdir -p /root/edgeai"

set +e
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$PACKAGE_WINDOWS" \
  "$BOARD_TARGET:$REMOTE_NEW" 2>&1 | tee "$LOG_DIR/package_transfer_$RUN_ID.log"
transfer_rc=${PIPESTATUS[0]}
set -e
[[ "$transfer_rc" -eq 0 ]] || exit "$transfer_rc"

set +e
"$BOARD_SSH" 'sh -s -- '"$REMOTE_NEW"' '"$remote_dest" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/board_video_execution_$RUN_ID.log"
set -u
new=$1
dest=$2
if [ ! -d "$new" ]; then
  echo "staged Task 020 package is missing: $new" >&2
  exit 1
fi
if [ -e "$dest" ]; then
  echo "refusing to overwrite Task 020 deployment: $dest" >&2
  exit 1
fi
mv "$new" "$dest" || exit 1
cd "$dest" || exit 1
mkdir -p results

{
  printf 'board_clock='
  date
  printf 'hostname='
  hostname
  printf 'uname='
  uname -a
  printf 'architecture='
  uname -m
  printf 'glibc='
  ldd --version 2>&1 | head -1
  printf 'device_tree_model='
  if [ -r /proc/device-tree/model ]; then
    tr -d '\000' </proc/device-tree/model
  else
    printf unavailable
  fi
  printf '\n'
  printf 'load_average='
  cat /proc/loadavg
  printf 'meminfo='
  grep -E '^(MemTotal|MemAvailable):' /proc/meminfo | tr '\n' ';'
  printf '\n'
  printf 'deployment_directory=%s\n' "$dest"
} > results/environment.txt

echo '=== hashes before chmod ===' > results/hashes.txt
sha256sum -c SHA256SUMS >> results/hashes.txt 2>&1 || exit 1
sha256sum edgeai_ncnn_video input/anlogic_arm_reference.avi \
  model/yolov5n.ncnn.param model/yolov5n.ncnn.bin \
  lib/libgomp.so.1 >> results/hashes.txt || exit 1
chmod 0755 edgeai_ncnn_video run.sh || exit 1
echo '=== hashes after chmod ===' >> results/hashes.txt
sha256sum -c SHA256SUMS >> results/hashes.txt 2>&1 || exit 1

LD_LIBRARY_PATH="$dest/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
ldd "$dest/edgeai_ncnn_video" > results/ldd.txt 2>&1 || exit 1
if grep -q 'not found' results/ldd.txt; then
  cat results/ldd.txt >&2
  exit 1
fi
file "$dest/edgeai_ncnn_video" > results/file.txt 2>&1 || true
readelf -h "$dest/edgeai_ncnn_video" > results/readelf-h.txt 2>&1 || true
readelf -d "$dest/edgeai_ncnn_video" > results/readelf-d.txt 2>&1 || true

set +e
sh "$dest/run.sh" > results/stdout.txt 2> results/stderr.txt
run_rc=$?
set -e
printf '%s\n' "$run_rc" > results/exit_code.txt
cat results/stdout.txt
cat results/stderr.txt >&2
printf 'exit_code=%s\n' "$run_rc"
if [ "$run_rc" -ne 0 ]; then
  exit "$run_rc"
fi
test -s results/video_frame_detections.json || exit 1
test -s results/anlogic_arm_ncnn_reference.avi || exit 1
sha256sum results/video_frame_detections.json \
  results/anlogic_arm_ncnn_reference.avi > results/output_hashes.txt || exit 1
printf '%s\n' "$dest" > results/deployment_directory.txt
REMOTE
board_rc=${PIPESTATUS[0]}
set -e

mkdir -p "$RETURN_LOCAL"
set +e
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" \
  "$BOARD_TARGET:$remote_dest/results/*" "$RETURN_WINDOWS/" \
  2>&1 | tee "$LOG_DIR/result_return_$RUN_ID.log"
return_rc=${PIPESTATUS[0]}
set -e
[[ "$return_rc" -eq 0 ]] || exit "$return_rc"
[[ "$board_rc" -eq 0 ]] || exit "$board_rc"

for required in \
  "$RETURN_LOCAL/video_frame_detections.json" \
  "$RETURN_LOCAL/anlogic_arm_ncnn_reference.avi" \
  "$RETURN_LOCAL/environment.txt" \
  "$RETURN_LOCAL/ldd.txt" \
  "$RETURN_LOCAL/hashes.txt" \
  "$RETURN_LOCAL/stdout.txt" \
  "$RETURN_LOCAL/stderr.txt" \
  "$RETURN_LOCAL/exit_code.txt" \
  "$RETURN_LOCAL/output_hashes.txt"; do
  [[ -f "$required" ]] || {
    printf 'returned Task 020 evidence is missing: %s\n' "$required" >&2
    exit 1
  }
done
[[ "$(tr -d '\r\n' < "$RETURN_LOCAL/exit_code.txt")" == "0" ]]
cp "$RETURN_LOCAL/video_frame_detections.json" "$OUTPUT_JSON"
cp "$RETURN_LOCAL/anlogic_arm_ncnn_reference.avi" "$OUTPUT_VIDEO"

python3 - \
  "$RETURN_LOCAL" \
  "$BUILD_OUTPUT/runtime_build_identity.json" \
  "$OUTPUT_ENVIRONMENT" \
  "$RUN_ID" <<'PY'
import hashlib
import json
import pathlib
import sys

returned = pathlib.Path(sys.argv[1])
identity = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
output = pathlib.Path(sys.argv[3])
run_id = sys.argv[4]

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

environment_text = (returned / "environment.txt").read_text(
    encoding="utf-8", errors="replace"
)
values = {}
for line in environment_text.splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        values[key] = value
ldd_text = (returned / "ldd.txt").read_text(encoding="utf-8", errors="replace")
stderr_text = (returned / "stderr.txt").read_text(
    encoding="utf-8", errors="replace"
)
payload = {
    "schema_version": 1,
    "task": "020",
    "recorded_by": "WSL collection script",
    "recorded_at_basis": "WSL run identifier; board clock retained separately and unsynchronized",
    "run_id": run_id,
    "board_model": "MLK-F3P-CZ02-DR1M90",
    "device_tree_model": values.get("device_tree_model"),
    "hostname": values.get("hostname"),
    "architecture": values.get("architecture"),
    "kernel": values.get("uname"),
    "glibc": values.get("glibc"),
    "board_clock": values.get("board_clock"),
    "load_average": values.get("load_average"),
    "memory": values.get("meminfo"),
    "deployment_directory": values.get("deployment_directory"),
    "runtime_profile": "recommended-dual-thread",
    "artifact_hashes": {
        "executable": identity["executable_sha256"],
        "libncnn_a": identity["libncnn_a_sha256"],
        "private_libgomp": identity["private_libgomp_so_1_sha256"],
    },
    "ldd": {
        "status": "PASS" if "not found" not in ldd_text else "FAIL",
        "sha256": sha(returned / "ldd.txt"),
    },
    "execution": {
        "exit_code": int((returned / "exit_code.txt").read_text().strip()),
        "stdout_sha256": sha(returned / "stdout.txt"),
        "stderr_sha256": sha(returned / "stderr.txt"),
        "stderr_empty": not bool(stderr_text.strip()),
    },
    "system_modified": False,
    "system_libraries_replaced": False,
    "governor_or_frequency_modified": False,
    "formal_benchmark": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

"$REPO_ROOT/.venv/bin/python" "$VALIDATOR" \
  --evidence-dir "$EVIDENCE_DIR" \
  --input-video "$INPUT_VIDEO" \
  --output-video "$OUTPUT_VIDEO" \
  --samples-dir "$REPO_ROOT/results/images/020"

cp "$RETURN_LOCAL/stdout.txt" "$LOG_DIR/board_video_stdout_$RUN_ID.log"
cp "$RETURN_LOCAL/stderr.txt" "$LOG_DIR/board_video_stderr_$RUN_ID.log"
cp "$RETURN_LOCAL/ldd.txt" "$LOG_DIR/board_video_ldd_$RUN_ID.log"
printf 'remote_deployment=%s\n' "$remote_dest"
printf 'returned_evidence=%s\n' "$RETURN_LOCAL"
printf 'video_automated_validation=PASS\n'
