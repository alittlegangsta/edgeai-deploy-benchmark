#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: sync_anlogic_repos.sh [--check|--fetch]

  --check  report repository identity, branch, commit, and dirty state (default)
  --fetch  after the same checks, run only `git fetch --prune --tags origin`
USAGE
}

mode="--check"
if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
elif [[ $# -eq 1 ]]; then
  case "$1" in
    --check|--fetch) mode="$1" ;;
    -h|--help) usage ; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
config_path="${EDGEAI_VENDOR_LOCAL_PATHS:-$repo_root/.knowledge/local_paths.yaml}"

if [[ ! -f "$config_path" ]]; then
  echo "error: local paths configuration not found: $config_path" >&2
  exit 1
fi

anlogic_repo_root=$(awk -F'"' '/^anlogic_repo_root:[[:space:]]*/ {print $2; exit}' "$config_path")
if [[ -z "$anlogic_repo_root" ]]; then
  echo "error: anlogic_repo_root is missing or not double-quoted in $config_path" >&2
  exit 1
fi

declare -a names=(dr1_demo_prjs dr1m90_npu)
declare -a urls=(
  "https://gitee.com/anlogic/dr1_demo_prjs.git"
  "https://gitee.com/anlogic/dr1m90_npu.git"
)

for i in "${!names[@]}"; do
  name=${names[$i]}
  expected_url=${urls[$i]}
  path="$anlogic_repo_root/$name"

  echo "=== $name ==="
  if [[ ! -d "$path/.git" ]]; then
    echo "error: repository is missing or not a worktree: $path" >&2
    exit 1
  fi

  actual_url=$(git -C "$path" remote get-url origin 2>/dev/null || true)
  if [[ "$actual_url" != "$expected_url" ]]; then
    echo "error: origin mismatch for $name" >&2
    echo "expected: $expected_url" >&2
    echo "actual:   ${actual_url:-<missing>}" >&2
    exit 1
  fi

  dirty=$(git -C "$path" status --short)
  branch=$(git -C "$path" branch --show-current)
  commit=$(git -C "$path" rev-parse HEAD)
  echo "path: $path"
  echo "origin: $actual_url"
  echo "branch: ${branch:-<detached>}"
  echo "commit: $commit"
  if [[ -n "$dirty" ]]; then
    echo "dirty: yes" >&2
    printf '%s\n' "$dirty" >&2
    exit 1
  fi
  echo "dirty: no"

  if [[ "$mode" == "--fetch" ]]; then
    git -C "$path" fetch --prune --tags origin
    echo "fetch: completed"
    echo "commit_after_fetch: $(git -C "$path" rev-parse HEAD)"
  fi
done
