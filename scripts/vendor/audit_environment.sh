#!/usr/bin/env bash

# Read-only environment audit for the Anlogic DR1 private knowledge workflow.
# It intentionally writes only to stdout and does not inspect credentials.
set -u

readonly MILIANKE_SOURCE_ROOT="/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA"
readonly PRIVATE_WORKSPACE_ROOT="/home/dministrator/vendor/anlogic-dr1-knowledge"

section() {
  printf '\n===== %s =====\n' "$1"
}

run_check() {
  local label="$1"
  shift
  printf 'check=%s\n' "$label"
  if [ "$#" -eq 0 ] || ! command -v "$1" >/dev/null 2>&1; then
    printf 'status=NOT_AVAILABLE\nexit_code=127\n'
    return 0
  fi
  printf 'resolved_path=%s\n' "$(command -v "$1")"
  "$@" 2>&1
  local exit_code=$?
  printf 'exit_code=%s\n' "$exit_code"
  return 0
}

path_check() {
  local label="$1"
  local path="$2"
  printf 'check=%s\npath=%s\n' "$label" "$path"
  if [ -e "$path" ]; then
    printf 'status=EXISTS\n'
  else
    printf 'status=NOT_FOUND\n'
  fi
}

section "Identity"
run_check "date" date
run_check "hostname" hostname
run_check "whoami" whoami
run_check "id" id
run_check "pwd" pwd

section "Kernel and WSL"
run_check "uname -a" uname -a
if [ -r /proc/version ]; then
  if command -v grep >/dev/null 2>&1 && grep -qiE 'microsoft|wsl' /proc/version; then
    printf 'wsl_detected=YES\n'
  else
    printf 'wsl_detected=NO_OR_UNKNOWN\n'
  fi
  printf 'proc_version_present=YES\n'
else
  printf 'proc_version_present=NOT_AVAILABLE\nwsl_detected=UNKNOWN\n'
fi

section "Node and retrieval tools"
run_check "node --version" node --version
run_check "npm --version" npm --version
run_check "npx --version" npx --version
run_check "python --version" python --version
run_check "python3 --version" python3 --version
run_check "pip --version" pip --version
run_check "pip3 --version" pip3 --version
run_check "git --version" git --version
run_check "codex --version" codex --version
run_check "qmd --version" qmd --version

section "Source and private workspace paths"
path_check "Milianke source root" "$MILIANKE_SOURCE_ROOT"
path_check "Private knowledge workspace" "$PRIVATE_WORKSPACE_ROOT"

section "Disk space"
run_check "df -h current directory" df -h -- "$PWD"

printf '\nprobe_complete=YES\n'
