#!/usr/bin/env bash

# Create only the external private workspace tree. No copy, network, or install
# operation is performed by this script.
set -u

readonly WORKSPACE_ROOT="/home/dministrator/vendor/anlogic-dr1-knowledge"
readonly RELATIVE_PATHS=(
  "milianke/p0"
  "milianke/archive"
  "anlogic/wiki/snapshots"
  "anlogic/repos"
  "mineru/wiki"
  "mineru/cache"
  "logs"
)

failed=0
for relative_path in "${RELATIVE_PATHS[@]}"; do
  target="${WORKSPACE_ROOT}/${relative_path}"
  if mkdir -p -- "$target"; then
    printf 'created_or_exists=%s\n' "$target"
  else
    printf 'create_failed=%s\n' "$target" >&2
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'bootstrap_complete=YES\n'
