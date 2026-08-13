#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
usage: run_task028_armnn_probe.sh --runner PATH --model PATH --config PATH \
  --image PATH --output-json PATH [--mode correctness|benchmark] \
  [--warmup N] [--repeats N] [--model-variant NAME] \
  [--expected-model-sha256 HEX] [--parse-only 0|1]
EOF
}

runner=
model=
config=
image=
output=
mode=correctness
warmup=0
repeats=1
model_variant=frozen
expected_model_sha256=
parse_only=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --runner) runner=$2; shift 2 ;;
        --model) model=$2; shift 2 ;;
        --config) config=$2; shift 2 ;;
        --image) image=$2; shift 2 ;;
        --output-json) output=$2; shift 2 ;;
        --mode) mode=$2; shift 2 ;;
        --warmup) warmup=$2; shift 2 ;;
        --repeats) repeats=$2; shift 2 ;;
        --model-variant) model_variant=$2; shift 2 ;;
        --expected-model-sha256) expected_model_sha256=$2; shift 2 ;;
        --parse-only) parse_only=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done
for required in runner model config image output; do
    [[ -n "${!required}" ]] || { echo "missing required argument: $required" >&2; usage; exit 2; }
done
[[ -x "$runner" ]] || { echo "runner is not executable: $runner" >&2; exit 1; }
[[ -f "$model" && -f "$config" && -f "$image" ]] || {
    echo "model, config, or image is missing" >&2
    exit 1
}
mkdir -p "$(dirname "$output")"
args=(--model "$model" --config "$config" --image "$image" \
    --output-json "$output" --mode "$mode" --warmup "$warmup" --repeats "$repeats" \
    --model-variant "$model_variant" --parse-only "$parse_only")
if [[ -n "$expected_model_sha256" ]]; then
    args+=(--expected-model-sha256 "$expected_model_sha256")
fi
exec "$runner" "${args[@]}"
