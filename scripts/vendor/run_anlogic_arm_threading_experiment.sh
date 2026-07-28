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
CONFIG="$REPO_ROOT/configs/benchmark_anlogic_arm_threading_openmp.json"
CONTRACT="$REPO_ROOT/results/evidence/018/openmp/experiment_contract.json"
ORDER="$REPO_ROOT/results/evidence/018/execution_order.json"
VALIDATOR="$REPO_ROOT/scripts/vendor/validate_anlogic_arm_threading_experiment.py"
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

SHARED_LOCAL="${ANLOGIC_THREADING_SHARED_LOCAL:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_threading_task018_openmp_session1}"
SHARED_WINDOWS="${ANLOGIC_THREADING_SHARED_WINDOWS:-C:/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_threading_task018_openmp_session1}"
BUILD_OUTPUT="${ANLOGIC_ARM_BUILD_OUTPUT:-/mnt/c/Users/Administrator/Desktop/fpga_info/_generated/edgeai_arm_threading_task018_openmp/build-output-libgomp-01b70259586931e86d0bc071030aea10674b09f80f28d80fc09857001ebd8f8e}"
BENCHMARK_ELF="$BUILD_OUTPUT/bin/edgeai_benchmark_ncnn"
PACKAGE_LOCAL="$SHARED_LOCAL/package"
PACKAGE_WINDOWS="$SHARED_WINDOWS/package"
RETURN_LOCAL="$SHARED_LOCAL/returned"
RETURN_WINDOWS="$SHARED_WINDOWS/returned"
BOARD_SSH="${ANLOGIC_BOARD_SSH:-/home/dministrator/bin/anlogic-board-ssh}"
BOARD_SCP="${ANLOGIC_BOARD_SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
BOARD_KEY_WINDOWS="${ANLOGIC_BOARD_KEY_WINDOWS:-C:/Users/Administrator/.ssh/anlogic_board_ed25519}"
BOARD_TARGET="${ANLOGIC_BOARD_TARGET:-root@192.168.50.2}"
REMOTE_DEST="${ANLOGIC_THREADING_REMOTE:-/root/edgeai/anlogic-arm-threading-task018-openmp-session1}"
REMOTE_NEW="${REMOTE_DEST}.new"
FORMAL_EVIDENCE="${ANLOGIC_THREADING_EVIDENCE_DIR:-$REPO_ROOT/results/evidence/018/openmp}"
LOG_DIR="$REPO_ROOT/results/logs/vendor/arm_threading"

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
  local required
  for required in \
    "$CONFIG" "$CONTRACT" "$ORDER" "$VALIDATOR" "$MODEL_MANIFEST" \
    "$INFERENCE_CONFIG" "$INPUT" "$REFERENCE"; do
    [[ -f "$required" ]] || {
      printf 'required Task 018 input is missing: %s\n' "$required" >&2
      return 1
    }
  done
  python3 "$VALIDATOR" check-contract \
    --config "$CONFIG" \
    --contract "$CONTRACT" \
    --execution-order "$ORDER"
  require_hash "$PARAM" "$EXPECTED_PARAM" "model_param"
  require_hash "$BIN" "$EXPECTED_BIN" "model_bin"
  require_hash "$INPUT" "$EXPECTED_INPUT" "fixed_input"
  require_hash "$INFERENCE_CONFIG" "$EXPECTED_INFERENCE_CONFIG" "inference_config"
  require_hash "$REFERENCE" "$EXPECTED_REFERENCE" "pc_ncnn_golden"
  if [[ -f "$BENCHMARK_ELF" ]]; then
    file "$BENCHMARK_ELF"
    if [[ -f "$BUILD_OUTPUT/SHA256SUMS" ]]; then
      (
        cd "$BUILD_OUTPUT"
        sha256sum -c SHA256SUMS
      )
      printf 'arm_benchmark_elf=PRESENT_BUILD_OUTPUT_HASH_VERIFIED\n'
      printf 'arm_benchmark_elf_sha256=%s\n' \
        "$(sha256_of "$BENCHMARK_ELF")"
    else
      printf 'arm_benchmark_elf=PRESENT_WITHOUT_BUILD_OUTPUT_MANIFEST\n'
    fi
  else
    printf 'arm_benchmark_elf=BUILD_REQUIRED_IN_FORMAL_COLLECTION_TURN\n'
  fi
  printf 'task017_evidence=UNCHANGED_AND_HASH_VERIFIED\n'
  printf 'offline_check=PASS\n'
}

print_plan() {
  cat <<'PLAN'
Task 018 dry-run; no VM, board, SSH, SCP, inference, or benchmark command is executed.
Only experimental variable: configured_threads=1 or configured_threads=2.
Alternating independent-process order:
  pair 1: threads=1 -> threads=2
  pair 2: threads=2 -> threads=1
  pair 3: threads=1 -> threads=2
  pair 4: threads=2 -> threads=1
  pair 5: threads=1 -> threads=2
Each process: correctness before, 10 warmups, 20 measured samples, correctness after.
Formal totals: 5 processes/100 samples per condition; 10 processes/200 samples overall.
Execute-mode stages (not run by --dry-run):
  1. rebuild       rebuild the shared AArch64 producer from the Task 018 source
  2. package       hash one ELF, frozen assets, config, reference, and private OpenCV libs
  3. deploy        transfer into a new isolated board directory without overwrite
  4. collect       execute the frozen alternating schedule and preserve failed attempts
  5. return        verify returned SHA256 files without touching Task 017 evidence
  6. validate      independently recompute condition statistics and comparison/classification
No governor, frequency, affinity, service, system library, model, or Task 017 change is permitted.
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
  "$BENCHMARK_ELF" \
  "$BUILD_OUTPUT/lib/libopencv_core.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgproc.so.407" \
  "$BUILD_OUTPUT/lib/libopencv_imgcodecs.so.407" \
  "$BUILD_OUTPUT/lib/libgomp.so.1"; do
  [[ -f "$required" ]] || {
    printf 'formal collection build input is missing: %s\n' "$required" >&2
    exit 1
  }
done
[[ ! -e "$PACKAGE_LOCAL" && ! -e "$RETURN_LOCAL" ]] || {
  printf 'refusing to overwrite existing Task 018 shared evidence tree: %s\n' \
    "$SHARED_LOCAL" >&2
  exit 1
}

mkdir -p "$LOG_DIR" "$PACKAGE_LOCAL"/{bin,config,input,lib,model,reference}
cp "$BENCHMARK_ELF" "$PACKAGE_LOCAL/bin/"
cp "$BUILD_OUTPUT/lib/"*.so.407 "$PACKAGE_LOCAL/lib/"
cp "$BUILD_OUTPUT/lib/libgomp.so.1" "$PACKAGE_LOCAL/lib/"
cp "$CONFIG" "$PACKAGE_LOCAL/config/benchmark_anlogic_arm_threading_openmp.json"
cp "$INFERENCE_CONFIG" "$PACKAGE_LOCAL/config/yolov5n_v7_inference.json"
cp "$INPUT" "$PACKAGE_LOCAL/input/pc_reference.jpg"
cp "$MODEL_MANIFEST" "$PACKAGE_LOCAL/model/ncnn_manifest.json"
cp "$PARAM" "$PACKAGE_LOCAL/model/yolov5n.ncnn.param"
cp "$BIN" "$PACKAGE_LOCAL/model/yolov5n.ncnn.bin"
cp "$REFERENCE" "$PACKAGE_LOCAL/reference/cpp_ncnn_reference.json"

cat > "$PACKAGE_LOCAL/run_condition.sh" <<'RUN'
#!/bin/sh
set -u
threads=$1
pair=$2
order=$3
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$threads:$pair:$order" in
  1:1:1|2:1:2|2:2:1|1:2:2|1:3:1|2:3:2|2:4:1|1:4:2|1:5:1|2:5:2) ;;
  *) echo "Task 018 condition identity differs" >&2; exit 2 ;;
esac
cd "$root" || exit 1
mkdir -p results/logs
export OMP_NUM_THREADS="$threads"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
LD_LIBRARY_PATH="$root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
exec "$root/bin/edgeai_benchmark_ncnn" \
  --benchmark-config "$root/config/benchmark_anlogic_arm_threading_openmp.json" \
  --ncnn-manifest "$root/model/ncnn_manifest.json" \
  --model-param "$root/model/yolov5n.ncnn.param" \
  --model-bin "$root/model/yolov5n.ncnn.bin" \
  --reference-detections "$root/reference/cpp_ncnn_reference.json" \
  --threads "$threads" \
  --pair-index "$pair" \
  --execution-order "$order" \
  --round "$pair" \
  --output "$root/results/threads${threads}_raw_samples.json"
RUN
(
  cd "$PACKAGE_LOCAL"
  find . -type f ! -name SHA256SUMS -print0 |
    sort -z |
    xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS
)

"$BOARD_SSH" 'echo board_ssh=PASS; uname -a; uname -m; ldd --version 2>&1 | head -1' \
  2>&1 | tee "$LOG_DIR/board_preflight.log"
remote_state="$("$BOARD_SSH" "
if [ -e '$REMOTE_DEST' ] || [ -e '$REMOTE_NEW' ]; then
  printf conflict
else
  printf transfer
fi
")"
[[ "$remote_state" == "transfer" ]] || {
  printf 'refusing to overwrite Task 018 board path: %s\n' "$REMOTE_DEST" >&2
  exit 1
}
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r "$PACKAGE_WINDOWS" \
  "$BOARD_TARGET:$REMOTE_NEW" 2>&1 | tee "$LOG_DIR/package_transfer.log"

set +e
"$BOARD_SSH" "sh -s -- '$REMOTE_NEW' '$REMOTE_DEST'" <<'REMOTE' \
  2>&1 | tee "$LOG_DIR/formal_collection.log"
set -u
new=$1
dest=$2
test -d "$new" || exit 1
test ! -e "$dest" || exit 1
mv "$new" "$dest" || exit 1
cd "$dest" || exit 1
sha256sum -c SHA256SUMS || exit $?
chmod 0755 bin/edgeai_benchmark_ncnn run_condition.sh
sha256sum -c SHA256SUMS || exit $?
mkdir -p results/logs results/invalid
LD_LIBRARY_PATH="$dest/lib" ldd "$dest/bin/edgeai_benchmark_ncnn" \
  > results/ldd.txt 2>&1
ldd_rc=$?
cat results/ldd.txt
if [ "$ldd_rc" -ne 0 ] || grep -q 'not found' results/ldd.txt; then
  exit 1
fi

maximum_readable() {
  maximum=
  for path in "$@"; do
    [ -r "$path" ] || continue
    value=$(cat "$path")
    case "$value" in
      ''|*[!0-9]*) continue ;;
    esac
    if [ -z "$maximum" ] || [ "$value" -gt "$maximum" ]; then
      maximum=$value
    fi
  done
  if [ -n "$maximum" ]; then
    printf '%s' "$maximum"
  else
    printf 'null'
  fi
}

capture_event() {
  pair=$1
  order=$2
  threads=$3
  phase=$4
  output=$5
  architecture=$(uname -m 2>/dev/null)
  load=$(awk '{print $1 "," $2 "," $3}' /proc/loadavg 2>/dev/null)
  frequency=$(maximum_readable /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq)
  temperature=$(maximum_readable /sys/class/thermal/thermal_zone*/temp)
  printf '{"pair_index":%s,"execution_order":%s,"configured_threads":%s,' \
    "$pair" "$order" "$threads" > "$output"
  printf '"phase":"%s","board_model":"MLK-F3P-CZ02-DR1M90",' "$phase" >> "$output"
  printf '"architecture":"%s","load_average":[%s],' "$architecture" "$load" >> "$output"
  printf '"cpu_frequency_khz":%s,"temperature_millicelsius":%s}\n' \
    "$frequency" "$temperature" >> "$output"
}

: > results/process_environment.ndjson
for identity in \
  1:1:1 1:2:2 \
  2:1:2 2:2:1 \
  3:1:1 3:2:2 \
  4:1:2 4:2:1 \
  5:1:1 5:2:2; do
  old_ifs=$IFS
  IFS=:
  set -- $identity
  IFS=$old_ifs
  pair=$1
  order=$2
  threads=$3
  attempt=1
  accepted=0
  while [ "$attempt" -le 3 ]; do
    prefix="pair_${pair}_order_${order}_threads_${threads}_attempt_${attempt}"
    capture_event "$pair" "$order" "$threads" before \
      "results/logs/${prefix}.environment_before.json"
    set +e
    sh "$dest/run_condition.sh" "$threads" "$pair" "$order" \
      > "results/logs/${prefix}.stdout.txt" \
      2> "results/logs/${prefix}.stderr.txt"
    rc=$?
    set -e
    printf '%s\n' "$rc" > "results/logs/${prefix}.exit_code.txt"
    if [ "$rc" -eq 0 ]; then
      capture_event "$pair" "$order" "$threads" after \
        "results/logs/${prefix}.environment_after.json"
      cat "results/logs/${prefix}.environment_before.json" \
        >> results/process_environment.ndjson
      cat "results/logs/${prefix}.environment_after.json" \
        >> results/process_environment.ndjson
      printf 'attempt=%s\nexit_code=0\n' "$attempt" \
        > "results/logs/pair_${pair}_order_${order}_threads_${threads}.accepted"
      accepted=1
      break
    fi
    cp "results/logs/${prefix}.environment_before.json" results/invalid/
    cp "results/logs/${prefix}.stdout.txt" results/invalid/
    cp "results/logs/${prefix}.stderr.txt" results/invalid/
    cp "results/logs/${prefix}.exit_code.txt" results/invalid/
    attempt=$((attempt + 1))
  done
  if [ "$accepted" -ne 1 ]; then
    echo "Task 018 condition failed after three preserved attempts: $identity" >&2
    exit 1
  fi
done
(
  cd results || exit 1
  sha256sum \
    threads1_raw_samples.json \
    threads2_raw_samples.json \
    process_environment.ndjson \
    ldd.txt > RETURNED_SHA256SUMS
)
cat results/RETURNED_SHA256SUMS
REMOTE
board_rc=${PIPESTATUS[0]}
set -e
[[ "$board_rc" -eq 0 ]] || exit "$board_rc"

mkdir -p "$RETURN_LOCAL"
"$BOARD_SCP" -i "$BOARD_KEY_WINDOWS" -r \
  "$BOARD_TARGET:$REMOTE_DEST/results/." "$RETURN_WINDOWS" \
  2>&1 | tee "$LOG_DIR/result_transfer.log"
(
  cd "$RETURN_LOCAL"
  sha256sum -c RETURNED_SHA256SUMS
)

mkdir -p "$FORMAL_EVIDENCE"
cp "$RETURN_LOCAL/threads1_raw_samples.json" "$FORMAL_EVIDENCE/"
cp "$RETURN_LOCAL/threads2_raw_samples.json" "$FORMAL_EVIDENCE/"
python3 "$VALIDATOR" assemble-environment \
  --ndjson "$RETURN_LOCAL/process_environment.ndjson" \
  --output "$FORMAL_EVIDENCE/process_environment.json"
python3 "$VALIDATOR" summarize \
  --config "$CONFIG" \
  --contract "$CONTRACT" \
  --execution-order "$ORDER" \
  --threads1-raw "$FORMAL_EVIDENCE/threads1_raw_samples.json" \
  --threads2-raw "$FORMAL_EVIDENCE/threads2_raw_samples.json" \
  --process-environment "$FORMAL_EVIDENCE/process_environment.json" \
  --threads1-summary "$FORMAL_EVIDENCE/threads1_summary.json" \
  --threads2-summary "$FORMAL_EVIDENCE/threads2_summary.json" \
  --comparison-summary "$FORMAL_EVIDENCE/comparison_summary.json" \
  --validation "$FORMAL_EVIDENCE/experiment_validation.json"
printf 'formal_collection=PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW\n'
