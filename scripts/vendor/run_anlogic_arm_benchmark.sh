#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"
case "$MODE" in
  --check|--dry-run|--execute) ;;
  *)
    printf 'usage: %s [--check|--dry-run|--execute]\n' "$0" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="$REPO_ROOT/configs/benchmark_anlogic_arm.json"
CONTRACT="$REPO_ROOT/results/evidence/017/benchmark_contract.json"
VALIDATOR="$REPO_ROOT/scripts/vendor/validate_anlogic_arm_benchmark.py"
PARAM="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.param"
BIN="$REPO_ROOT/models/yolov5n-v7.0/yolov5n.ncnn.bin"
MODEL_MANIFEST="$REPO_ROOT/models/yolov5n-v7.0/ncnn_manifest.json"
INFERENCE_CONFIG="$REPO_ROOT/configs/yolov5n_v7_inference.json"
INPUT="$REPO_ROOT/data/samples/images/pc_reference.jpg"
REFERENCE="$REPO_ROOT/results/acceptance/cpp_ncnn_reference.json"

EXPECTED_PARAM="72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
EXPECTED_BIN="658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
EXPECTED_INPUT="625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
EXPECTED_INFERENCE_CONFIG="82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d"
EXPECTED_REFERENCE="fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9"

SHARED_LOCAL="${ANLOGIC_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_benchmark}"
SHARED_WINDOWS="${ANLOGIC_SHARED_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_benchmark}"
TASK014_BUILD_OUTPUT="${ANLOGIC_ARM_BUILD_OUTPUT:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_yolov5n/build-output}"
PACKAGE_LOCAL="$SHARED_LOCAL/package"
PACKAGE_WINDOWS="$SHARED_WINDOWS/package"
RETURN_LOCAL="$SHARED_LOCAL/returned"
RETURN_WINDOWS="$SHARED_WINDOWS/returned"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
BOARD_SCP="${ANLOGIC_BOARD_SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
BOARD_KEY_WINDOWS="${ANLOGIC_BOARD_KEY_WINDOWS:-C:/Users/Administrator/.ssh/anlogic_board_ed25519}"
BOARD_TARGET="${ANLOGIC_BOARD_TARGET:-root@192.168.50.2}"
REMOTE_DEST="${ANLOGIC_ARM_BENCHMARK_REMOTE:-/root/edgeai/anlogic-arm-benchmark-task017}"
REMOTE_NEW="${REMOTE_DEST}.new"
FORMAL_EVIDENCE="$REPO_ROOT/results/evidence/017"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_benchmark"

sha256_of() {
  sha256sum "$1" | awk '{print $1}'
}

require_hash() {
  local path=$1
  local expected=$2
  local label=$3
  [[ -f "$path" ]] || {
    printf '%s missing: %s\n' "$label" "$path" >&2
    return 1
  }
  local observed
  observed="$(sha256_of "$path")"
  [[ "$observed" == "$expected" ]] || {
    printf '%s SHA256 mismatch: expected=%s observed=%s\n' \
      "$label" "$expected" "$observed" >&2
    return 1
  }
  printf '%s_sha256=%s\n' "$label" "$observed"
}

offline_check() {
  for required in \
    "$CONFIG" "$CONTRACT" "$VALIDATOR" "$MODEL_MANIFEST" \
    "$INFERENCE_CONFIG" "$INPUT" "$REFERENCE"; do
    [[ -f "$required" ]] || {
      printf 'required Task 017 input is missing: %s\n' "$required" >&2
      return 1
    }
  done
  python3 "$VALIDATOR" check-contract --config "$CONFIG" --contract "$CONTRACT"
  require_hash "$PARAM" "$EXPECTED_PARAM" "model_param"
  require_hash "$BIN" "$EXPECTED_BIN" "model_bin"
  require_hash "$INPUT" "$EXPECTED_INPUT" "fixed_input"
  require_hash "$INFERENCE_CONFIG" "$EXPECTED_INFERENCE_CONFIG" "inference_config"
  require_hash "$REFERENCE" "$EXPECTED_REFERENCE" "pc_ncnn_golden"
  if [[ -f "$TASK014_BUILD_OUTPUT/edgeai_benchmark_ncnn" ]]; then
    file "$TASK014_BUILD_OUTPUT/edgeai_benchmark_ncnn"
    printf 'arm_benchmark_elf=PRESENT_REQUIRES_FORMAL_PREFLIGHT\n'
  else
    printf 'arm_benchmark_elf=BUILD_REQUIRED_IN_FORMAL_COLLECTION_TURN\n'
  fi
  printf 'offline_check=PASS\n'
}

print_plan() {
  cat <<'PLAN'
Task 017 dry-run; no VM, board, SSH, SCP, inference, or benchmark command is executed.
Stages:
  1. check             validate frozen config, contract, and asset SHA256 values
  2. build             use the existing VM ARM build entry to produce edgeai_benchmark_ncnn
  3. deploy            create a hash manifest and isolated board package
  4. validate-before   capture board environment and run embedded golden correctness
  5. benchmark         launch 5 new processes; each runs 10 warmups and 20 measurements
  6. validate-after    run embedded golden correctness and capture environment again
  7. collect           return raw JSON, stdout, stderr, exit codes, hashes, and environment
  8. summarize         independently recompute nearest-rank statistics, sample stddev, and FPS
Formal result paths are reserved under results/evidence/017.
No governor, frequency, affinity, system library, service, boot, or model change is permitted.
PLAN
}

if [[ "$MODE" == "--check" ]]; then
  offline_check
  exit 0
fi
if [[ "$MODE" == "--dry-run" ]]; then
  offline_check
  print_plan
  exit 0
fi

offline_check
[[ -x "$BOARD_SSH" ]] || {
  printf 'board SSH wrapper is missing or not executable: %s\n' "$BOARD_SSH" >&2
  exit 1
}
[[ -x "$BOARD_SCP" ]] || {
  printf 'Windows SCP is missing or not executable: %s\n' "$BOARD_SCP" >&2
  exit 1
}
for required in \
  "$TASK014_BUILD_OUTPUT/edgeai_benchmark_ncnn" \
  "$TASK014_BUILD_OUTPUT/lib/libopencv_core.so.407" \
  "$TASK014_BUILD_OUTPUT/lib/libopencv_imgproc.so.407" \
  "$TASK014_BUILD_OUTPUT/lib/libopencv_imgcodecs.so.407"; do
  [[ -f "$required" ]] || {
    printf 'formal collection build input is missing: %s\n' "$required" >&2
    printf 'run the approved ARM build script in its separately authorized VM turn\n' >&2
    exit 1
  }
done

mkdir -p "$LOG_DIR" "$SHARED_LOCAL"
if [[ ! -d "$PACKAGE_LOCAL" ]]; then
  mkdir -p \
    "$PACKAGE_LOCAL/bin" \
    "$PACKAGE_LOCAL/config" \
    "$PACKAGE_LOCAL/input" \
    "$PACKAGE_LOCAL/lib" \
    "$PACKAGE_LOCAL/model" \
    "$PACKAGE_LOCAL/reference"
  cp "$TASK014_BUILD_OUTPUT/edgeai_benchmark_ncnn" "$PACKAGE_LOCAL/bin/"
  cp "$TASK014_BUILD_OUTPUT/lib/"*.so.407 "$PACKAGE_LOCAL/lib/"
  cp "$CONFIG" "$PACKAGE_LOCAL/config/benchmark_anlogic_arm.json"
  cp "$INFERENCE_CONFIG" "$PACKAGE_LOCAL/config/yolov5n_v7_inference.json"
  cp "$INPUT" "$PACKAGE_LOCAL/input/pc_reference.jpg"
  cp "$MODEL_MANIFEST" "$PACKAGE_LOCAL/model/ncnn_manifest.json"
  cp "$PARAM" "$PACKAGE_LOCAL/model/yolov5n.ncnn.param"
  cp "$BIN" "$PACKAGE_LOCAL/model/yolov5n.ncnn.bin"
  cp "$REFERENCE" "$PACKAGE_LOCAL/reference/cpp_ncnn_reference.json"
  cat > "$PACKAGE_LOCAL/run_round.sh" <<'RUN'
#!/bin/sh
set -u
round=$1
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$root" || exit 1
mkdir -p results/logs
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
LD_LIBRARY_PATH="$root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
exec "$root/bin/edgeai_benchmark_ncnn" \
  --benchmark-config "$root/config/benchmark_anlogic_arm.json" \
  --ncnn-manifest "$root/model/ncnn_manifest.json" \
  --model-param "$root/model/yolov5n.ncnn.param" \
  --model-bin "$root/model/yolov5n.ncnn.bin" \
  --reference-detections "$root/reference/cpp_ncnn_reference.json" \
  --round "$round" \
  --output "$root/results/benchmark_raw_samples.json"
RUN
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

"$BOARD_SSH" '
set -u
echo board_ssh=PASS
uname -a
uname -m
cat /etc/os-release
ldd --version 2>&1 | head -1
df -h /root
' 2>&1 | tee "$LOG_DIR/board_preflight.log"

remote_mode="$("$BOARD_SSH" "
if [ -d '$REMOTE_DEST' ]; then
  printf reuse
elif [ -e '$REMOTE_DEST' ] || [ -e '$REMOTE_NEW' ]; then
  printf conflict
else
  printf transfer
fi
")"
if [[ "$remote_mode" == "transfer" ]]; then
  "$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$PACKAGE_WINDOWS" \
    "$BOARD_TARGET:$REMOTE_NEW" 2>&1 | tee "$LOG_DIR/package_transfer.log"
elif [[ "$remote_mode" == "conflict" ]]; then
  printf 'refusing to overwrite task-owned remote path\n' >&2
  exit 1
fi

set +e
"$BOARD_SSH" "sh -s -- '$remote_mode' '$REMOTE_NEW' '$REMOTE_DEST'" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/formal_collection.log"
set -u
mode=$1
new=$2
dest=$3
if [ "$mode" = transfer ]; then
  test -d "$new" || exit 1
  test ! -e "$dest" || exit 1
  mv "$new" "$dest" || exit 1
fi
cd "$dest" || exit 1
sha256sum -c SHA256SUMS || exit $?
chmod 0755 bin/edgeai_benchmark_ncnn run_round.sh
sha256sum -c SHA256SUMS || exit $?
mkdir -p results/logs
LD_LIBRARY_PATH="$dest/lib" ldd "$dest/bin/edgeai_benchmark_ncnn" \
  > results/ldd.txt 2>&1
ldd_rc=$?
cat results/ldd.txt
if [ "$ldd_rc" -ne 0 ] || grep -q 'not found' results/ldd.txt; then
  exit 1
fi

capture_environment() {
  phase=$1
  output=$2
  architecture=$(uname -m 2>/dev/null || printf unknown)
  kernel=$(uname -r 2>/dev/null || printf unknown)
  os_name=$(sed -n 's/^NAME=//p' /etc/os-release 2>/dev/null | tr -d '"' | head -1)
  os_version=$(sed -n 's/^VERSION=//p' /etc/os-release 2>/dev/null | tr -d '"' | head -1)
  glibc=$(ldd --version 2>&1 | head -1 | sed 's/.* //')
  cpu_count=$(grep -c '^processor' /proc/cpuinfo 2>/dev/null || printf 0)
  mem_total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null)
  mem_available=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null)
  uptime_value=$(awk '{print $1}' /proc/uptime 2>/dev/null)
  load_values=$(cat /proc/loadavg 2>/dev/null | awk '{print $1 "," $2 "," $3}')
  {
    printf '{\n'
    printf '  "schema_version": 1,\n'
    printf '  "evidence_type": "task017_board_environment",\n'
    printf '  "phase": "%s",\n' "$phase"
    printf '  "board": {"model": "MLK-F3P-CZ02-DR1M90", "architecture": "%s", ' "$architecture"
    printf '"os": "%s %s", "kernel": "%s", "glibc": "%s", "cpu_count": %s},\n' \
      "$os_name" "$os_version" "$kernel" "$glibc" "$cpu_count"
    printf '  "memory": {"mem_total_kib": %s, "mem_available_kib": %s},\n' \
      "${mem_total:-null}" "${mem_available:-null}"
    printf '  "uptime_seconds": %s,\n' "${uptime_value:-null}"
    printf '  "load_average": [%s],\n' "${load_values:-null,null,null}"
    printf '  "governors": ['
    separator=
    for path in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
      [ -r "$path" ] || continue
      value=$(cat "$path")
      printf '%s{"path":"%s","value":"%s"}' "$separator" "$path" "$value"
      separator=,
    done
    printf '],\n  "available_frequencies_khz": ['
    separator=
    for path in /sys/devices/system/cpu/cpu*/cpufreq/scaling_available_frequencies; do
      [ -r "$path" ] || continue
      value=$(cat "$path")
      printf '%s{"path":"%s","value":"%s"}' "$separator" "$path" "$value"
      separator=,
    done
    printf '],\n  "current_frequencies_khz": ['
    separator=
    for path in /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do
      [ -r "$path" ] || continue
      value=$(cat "$path")
      printf '%s{"path":"%s","value":%s}' "$separator" "$path" "$value"
      separator=,
    done
    printf '],\n  "thermal_zones": ['
    separator=
    for path in /sys/class/thermal/thermal_zone*/temp; do
      [ -r "$path" ] || continue
      value=$(cat "$path")
      printf '%s{"path":"%s","temperature_millicelsius":%s}' \
        "$separator" "$path" "$value"
      separator=,
    done
    printf ']\n}\n'
  } > "$output"
}

if [ ! -e results/benchmark_environment_before.json ]; then
  capture_environment before results/benchmark_environment_before.json
fi
round=1
while [ "$round" -le 5 ]; do
  if [ -f "results/logs/round_${round}.accepted" ]; then
    echo "round_${round}=ALREADY_ACCEPTED"
    round=$((round + 1))
    continue
  fi
  if [ -f results/benchmark_raw_samples.json ] &&
     grep -q "\"round\":${round}," results/benchmark_raw_samples.json; then
    echo "round_${round}=RAW_PRESENT_WITHOUT_ACCEPTANCE_MARKER" >&2
    exit 1
  fi
  attempt=1
  while [ -e "results/logs/round_${round}_attempt_${attempt}.exit_code.txt" ]; do
    attempt=$((attempt + 1))
  done
  printf 'round=%s\n' "$round"
  printf 'attempt=%s\n' "$attempt"
  set +e
  sh "$dest/run_round.sh" "$round" \
    > "results/logs/round_${round}_attempt_${attempt}.stdout.txt" \
    2> "results/logs/round_${round}_attempt_${attempt}.stderr.txt"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "results/logs/round_${round}_attempt_${attempt}.exit_code.txt"
  cat "results/logs/round_${round}_attempt_${attempt}.stdout.txt"
  cat "results/logs/round_${round}_attempt_${attempt}.stderr.txt" >&2
  if [ "$rc" -ne 0 ]; then
    echo "round_${round}=INVALID_NONZERO_EXIT" >&2
    exit "$rc"
  fi
  printf 'attempt=%s\nexit_code=0\n' "$attempt" \
    > "results/logs/round_${round}.accepted"
  round=$((round + 1))
done
if [ ! -e results/benchmark_environment_after.json ]; then
  capture_environment after results/benchmark_environment_after.json
fi
(
  cd results || exit 1
  sha256sum \
    benchmark_environment_before.json \
    benchmark_environment_after.json \
    benchmark_raw_samples.json > RETURNED_SHA256SUMS
)
cat results/RETURNED_SHA256SUMS
REMOTE
board_rc=${PIPESTATUS[0]}
set -e
[[ "$board_rc" -eq 0 ]] || exit "$board_rc"

[[ ! -e "$RETURN_LOCAL" ]] || {
  printf 'refusing to overwrite existing returned benchmark evidence: %s\n' "$RETURN_LOCAL" >&2
  exit 1
}
mkdir -p "$RETURN_LOCAL"
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r \
  "$BOARD_TARGET:$REMOTE_DEST/results/." "$RETURN_WINDOWS" \
  2>&1 | tee "$LOG_DIR/result_transfer.log"
(
  cd "$RETURN_LOCAL"
  sha256sum -c RETURNED_SHA256SUMS
)

mkdir -p "$FORMAL_EVIDENCE"
cp "$RETURN_LOCAL/benchmark_environment_before.json" "$FORMAL_EVIDENCE/"
cp "$RETURN_LOCAL/benchmark_environment_after.json" "$FORMAL_EVIDENCE/"
cp "$RETURN_LOCAL/benchmark_raw_samples.json" "$FORMAL_EVIDENCE/"
python3 "$VALIDATOR" summarize \
  --config "$CONFIG" \
  --contract "$CONTRACT" \
  --raw "$FORMAL_EVIDENCE/benchmark_raw_samples.json" \
  --environment-before "$FORMAL_EVIDENCE/benchmark_environment_before.json" \
  --environment-after "$FORMAL_EVIDENCE/benchmark_environment_after.json" \
  --summary "$FORMAL_EVIDENCE/benchmark_summary.json" \
  --validation "$FORMAL_EVIDENCE/benchmark_validation.json"
printf 'formal_collection=PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW\n'
