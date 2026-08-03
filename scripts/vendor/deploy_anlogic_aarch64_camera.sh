#!/usr/bin/env bash
set -euo pipefail
MODE="--check"
if [[ "$#" -gt 1 ]]; then printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2; fi
if [[ "$#" -eq 1 ]]; then MODE="$1"; fi
case "$MODE" in --check|--execute) ;; *) printf 'usage: %s [--check|--execute]\n' "$0" >&2; exit 2 ;; esac
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
BOARD_SCP="${ANLOGIC_BOARD_SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
BOARD_KEY_WINDOWS="${ANLOGIC_BOARD_KEY_WINDOWS:-C:/Users/Administrator/.ssh/anlogic_board_ed25519}"
BOARD_TARGET="${ANLOGIC_BOARD_TARGET:-root@192.168.50.2}"
SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_camera_task021}"
SHARED_WINDOWS="${ANLOGIC_SHARED_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_camera_task021}"
BUILD_OUTPUT="$SHARED_LOCAL/build-output"; RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
PACKAGE_LOCAL="$SHARED_LOCAL/package-$RUN_ID"; PACKAGE_WINDOWS="$SHARED_WINDOWS/package-$RUN_ID"
RETURN_LOCAL="$SHARED_LOCAL/returned-$RUN_ID"; RETURN_WINDOWS="$SHARED_WINDOWS/returned-$RUN_ID"
REMOTE_NEW="/root/edgeai/yolov5n-ncnn-uvc-camera-$RUN_ID.new"; REMOTE_DEST="/root/edgeai/yolov5n-ncnn-uvc-camera-$RUN_ID"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_uvc_camera"; EVIDENCE_DIR="$REPO_ROOT/results/evidence/021"
PARAM="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param"; BIN="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin"
MODEL_MANIFEST="$REPO_ROOT/models/yolov5n-v7.0/ncnn_manifest.json"; CONFIG="$REPO_ROOT/configs/yolov5n_v7_inference.json"
PROFILE="$REPO_ROOT/configs/runtime_profiles/anlogic-dr1-recommended-dual-thread.json"
EXPECTED_PARAM="72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"; EXPECTED_BIN="658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"; EXPECTED_LIBGOMP="87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"
CAMERA_DEVICE="${ANLOGIC_CAMERA_DEVICE:-/dev/video0}"; CAMERA_WIDTH="${ANLOGIC_CAMERA_WIDTH:-640}"; CAMERA_HEIGHT="${ANLOGIC_CAMERA_HEIGHT:-480}"; CAMERA_FPS="${ANLOGIC_CAMERA_FPS:-5}"; CAMERA_FORMAT="${ANLOGIC_CAMERA_FORMAT:-YUYV}"
[[ -x "$BOARD_SSH" ]] || { printf 'board SSH wrapper is missing: %s\n' "$BOARD_SSH" >&2; exit 1; }; [[ -x "$BOARD_SCP" ]] || { printf 'Windows scp is missing: %s\n' "$BOARD_SCP" >&2; exit 1; }
for required in "$PARAM" "$BIN" "$MODEL_MANIFEST" "$CONFIG" "$PROFILE" "$BUILD_OUTPUT/edgeai_ncnn_camera" "$BUILD_OUTPUT/runtime_build_identity.json" "$BUILD_OUTPUT/BUILD_OUTPUT_SHA256SUMS"; do [[ -f "$required" ]] || { printf 'missing Task 021 input: %s\n' "$required" >&2; exit 1; }; done
[[ "$(sha256sum "$PARAM" | awk '{print $1}')" == "$EXPECTED_PARAM" ]]; [[ "$(sha256sum "$BIN" | awk '{print $1}')" == "$EXPECTED_BIN" ]]; [[ "$(sha256sum "$BUILD_OUTPUT/lib/libgomp.so.1" | awk '{print $1}')" == "$EXPECTED_LIBGOMP" ]]
( cd "$BUILD_OUTPUT"; sha256sum -c BUILD_OUTPUT_SHA256SUMS )
mkdir -p "$LOG_DIR" "$EVIDENCE_DIR" "$REPO_ROOT/results/images/021"
"$BOARD_SSH" 'echo board_ssh=PASS; hostname; uname -a; uname -m; ldd --version 2>&1 | head -1; ls -l /dev/video* 2>&1; for d in /sys/class/video4linux/*; do [ -e "$d" ] || continue; printf "video_node=%s name=" "$d"; cat "$d/name" 2>/dev/null || true; done; cat /proc/loadavg; free -h; df -h /tmp' 2>&1 | tee "$LOG_DIR/board_camera_preflight_$(date -u +%Y%m%dT%H%M%SZ).log"
if [[ "$MODE" == "--check" ]]; then printf 'camera_deployment_check=PASS\n'; exit 0; fi
rm -rf "$PACKAGE_LOCAL" "$RETURN_LOCAL"; mkdir -p "$PACKAGE_LOCAL/model" "$PACKAGE_LOCAL/config" "$PACKAGE_LOCAL/lib"
cp "$BUILD_OUTPUT/edgeai_ncnn_camera" "$PACKAGE_LOCAL/edgeai_ncnn_camera"; cp "$PARAM" "$PACKAGE_LOCAL/model/yolov5n.ncnn.param"; cp "$BIN" "$PACKAGE_LOCAL/model/yolov5n.ncnn.bin"; cp "$MODEL_MANIFEST" "$PACKAGE_LOCAL/model/ncnn_manifest.json"; cp "$CONFIG" "$PACKAGE_LOCAL/config/yolov5n_v7_inference.json"; cp "$PROFILE" "$PACKAGE_LOCAL/config/runtime_profile.json"; cp "$BUILD_OUTPUT/runtime_build_identity.json" "$PACKAGE_LOCAL/runtime_build_identity.json"; cp "$BUILD_OUTPUT/lib/"* "$PACKAGE_LOCAL/lib/"
cat > "$PACKAGE_LOCAL/run.sh" <<RUN
#!/bin/sh
set -u
ROOT=\$(CDPATH= cd -- "\$(dirname -- "\$0")" && pwd)
mkdir -p "\$ROOT/results/frames"
export LD_LIBRARY_PATH="\$ROOT/lib"
export OMP_NUM_THREADS=2
set -- --manifest "\$ROOT/model/ncnn_manifest.json" --model-param "\$ROOT/model/yolov5n.ncnn.param" --model-bin "\$ROOT/model/yolov5n.ncnn.bin" --config "\$ROOT/config/yolov5n_v7_inference.json" --camera-device "$CAMERA_DEVICE" --runtime-profile recommended-dual-thread --max-processed-frames 10 --max-duration-seconds 60 --output-json "\$ROOT/results/camera_run.json" --capabilities-json "\$ROOT/results/camera_capabilities.json" --output-frames-dir "\$ROOT/results/frames" --no-display 1
if [ "$CAMERA_WIDTH" -gt 0 ] 2>/dev/null; then set -- "\$@" --capture-width "$CAMERA_WIDTH"; fi
if [ "$CAMERA_HEIGHT" -gt 0 ] 2>/dev/null; then set -- "\$@" --capture-height "$CAMERA_HEIGHT"; fi
if [ "$CAMERA_FPS" != "0" ] && [ -n "$CAMERA_FPS" ]; then set -- "\$@" --capture-fps "$CAMERA_FPS"; fi
if [ -n "$CAMERA_FORMAT" ]; then set -- "\$@" --camera-format "$CAMERA_FORMAT"; fi
exec "\$ROOT/edgeai_ncnn_camera" "\$@"
RUN
python3 - "$PACKAGE_LOCAL" <<'PY'
import hashlib, json, pathlib, sys
root=pathlib.Path(sys.argv[1]); files={}
for path in sorted(p for p in root.rglob("*") if p.is_file()):
    rel=path.relative_to(root).as_posix(); files[rel]={"size_bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
(root/"deployment_manifest.json").write_text(json.dumps({"schema_version":1,"task":"021","runtime_profile":"recommended-dual-thread","configured_threads":2,"effective_parallel_backend":"openmp","files":files},indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY
( cd "$PACKAGE_LOCAL"; find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS; sha256sum -c SHA256SUMS )
mkdir -p "$SHARED_LOCAL"; "$BOARD_SSH" "test ! -e '$REMOTE_NEW'; mkdir -p /root/edgeai"
set +e; "$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$PACKAGE_WINDOWS" "$BOARD_TARGET:$REMOTE_NEW" > "$LOG_DIR/board_camera_transfer_$RUN_ID.log" 2>&1; transfer_rc=$?; set -e; [[ "$transfer_rc" -eq 0 ]] || { cat "$LOG_DIR/board_camera_transfer_$RUN_ID.log" >&2; exit "$transfer_rc"; }
set +e
"$BOARD_SSH" 'sh -s -- '"$REMOTE_NEW"' '"$REMOTE_DEST" <<'REMOTE' > "$LOG_DIR/board_camera_execution_$RUN_ID.log" 2>&1
set -u
new=$1; dest=$2; test -d "$new"; test ! -e "$dest"; mv "$new" "$dest"; cd "$dest"; mkdir -p results
{ printf 'board_clock='; date; printf 'hostname='; hostname; printf 'uname='; uname -a; printf 'architecture='; uname -m; printf 'glibc='; ldd --version 2>&1 | head -1; printf 'load_average='; cat /proc/loadavg; printf 'deployment_directory=%s\n' "$dest"; } > results/environment.txt
echo '=== before chmod ===' > results/hashes.txt; sha256sum -c SHA256SUMS >> results/hashes.txt 2>&1 || exit 1; chmod 0755 edgeai_ncnn_camera run.sh || exit 1; echo '=== after chmod ===' >> results/hashes.txt; sha256sum -c SHA256SUMS >> results/hashes.txt 2>&1 || exit 1
export LD_LIBRARY_PATH="$dest/lib"; ldd "$dest/edgeai_ncnn_camera" > results/ldd.txt 2>&1 || exit 1; if grep -q 'not found' results/ldd.txt; then exit 1; fi
file "$dest/edgeai_ncnn_camera" > results/file.txt 2>&1 || true; readelf -h "$dest/edgeai_ncnn_camera" > results/readelf-h.txt 2>&1 || true; readelf -d "$dest/edgeai_ncnn_camera" > results/readelf-d.txt 2>&1 || true
set +e; sh "$dest/run.sh" > results/stdout.txt 2> results/stderr.txt; run_rc=$?; set -e; printf '%s\n' "$run_rc" > results/exit_code.txt; printf '%s\n' "$dest" > results/deployment_directory.txt; cat results/stdout.txt; cat results/stderr.txt >&2; printf 'exit_code=%s\n' "$run_rc"; exit "$run_rc"
REMOTE
board_rc=$?; set -e
mkdir -p "$RETURN_LOCAL"; set +e; "$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$BOARD_TARGET:$REMOTE_DEST/results" "$RETURN_WINDOWS/" > "$LOG_DIR/board_camera_return_$RUN_ID.log" 2>&1; return_rc=$?; set -e
[[ "$return_rc" -eq 0 ]] || { cat "$LOG_DIR/board_camera_return_$RUN_ID.log" >&2; exit "$return_rc"; }
results_root="$RETURN_LOCAL/results"
for required in "$results_root/camera_run.json" "$results_root/camera_capabilities.json" "$results_root/environment.txt" "$results_root/ldd.txt" "$results_root/hashes.txt" "$results_root/stdout.txt" "$results_root/stderr.txt" "$results_root/exit_code.txt"; do [[ -f "$required" ]] || { printf 'returned camera evidence missing: %s\n' "$required" >&2; exit 1; }; done
cp "$results_root/camera_run.json" "$EVIDENCE_DIR/camera_run.json"; cp "$results_root/camera_run.json" "$EVIDENCE_DIR/camera_frame_detections.json"; cp "$results_root/camera_capabilities.json" "$EVIDENCE_DIR/camera_capabilities.json"
cp "$results_root/stdout.txt" "$LOG_DIR/board_stdout_$RUN_ID.log"; cp "$results_root/stderr.txt" "$LOG_DIR/board_stderr_$RUN_ID.log"; cp "$results_root/environment.txt" "$LOG_DIR/board_environment_$RUN_ID.log"; cp "$results_root/ldd.txt" "$LOG_DIR/board_ldd_$RUN_ID.log"; cp "$results_root/hashes.txt" "$LOG_DIR/board_hashes_$RUN_ID.log"
replay_root="$LOG_DIR/replay_frames/$RUN_ID"; mkdir -p "$replay_root"; cp "$results_root/frames/"*_raw.png "$replay_root/"
for pair in "first 0" "middle 5" "last 9"; do set -- $pair; label=$1; index=$2; cp "$results_root/frames/processed_"$index"_raw.png" "$REPO_ROOT/results/images/021/"$label"_raw.png"; cp "$results_root/frames/processed_"$index"_annotated.png" "$REPO_ROOT/results/images/021/"$label"_annotated.png"; done
python3 - "$EVIDENCE_DIR/camera_environment.json" "$results_root/environment.txt" "$RUN_ID" <<'PY'
import json, pathlib, sys
values={}
for line in pathlib.Path(sys.argv[2]).read_text(encoding="utf-8",errors="replace").splitlines():
    if "=" in line: key,value=line.split("=",1); values[key]=value
payload={"schema_version":1,"task":"021","run_id":sys.argv[3],"recorded_at_basis":"WSL collection time; board clock retained and may be unsynchronized","board_clock":values.get("board_clock"),"hostname":values.get("hostname"),"uname":values.get("uname"),"architecture":values.get("architecture"),"glibc":values.get("glibc"),"load_average":values.get("load_average"),"deployment_directory":values.get("deployment_directory"),"system_modified":False}
pathlib.Path(sys.argv[1]).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY
python3 - "$EVIDENCE_DIR/camera_contract.json" "$BUILD_OUTPUT/runtime_build_identity.json" "$RUN_ID" <<'PY'
import json, pathlib, sys
identity=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
payload={"schema_version":1,"task":"021","status":"In Progress","automated_validation":"PENDING_OFFLINE_REPLAY","human_camera_review":"PENDING","candidate_approved":False,"run_id":sys.argv[3],"runtime_profile":"recommended-dual-thread","configured_threads":2,"effective_parallel_backend":"openmp","build_identity":identity,"frozen_model_param_sha256":"72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4","frozen_model_bin_sha256":"658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0","bounded_latency_policy":"latest-frame-wins; capacity=1; overwrite old unprocessed frame","formal_realtime_benchmark":False}
pathlib.Path(sys.argv[1]).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY
printf 'camera_deployment_run=%s\nboard_destination=%s\n' "$RUN_ID" "$REMOTE_DEST"; cat "$LOG_DIR/board_camera_execution_$RUN_ID.log"; [[ "$board_rc" -eq 0 ]]
