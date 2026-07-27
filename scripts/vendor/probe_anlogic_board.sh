#!/bin/sh
# Read-only probe intended to run on an Anlogic DR1 board.
# It is deliberately tolerant of missing commands for BusyBox-style systems.
set -u

section() {
  printf '\n=== %s ===\n' "$1"
}

run_cmd() {
  label=$1
  shift
  section "$label"
  if command -v "$1" >/dev/null 2>&1; then
    "$@" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$1"
  fi
}

run_path() {
  label=$1
  path=$2
  section "$label"
  if [ -e "$path" ] || [ -L "$path" ]; then
    ls -l "$path" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$path"
  fi
}

section 'identity'
run_cmd date date
run_cmd hostname hostname

section 'kernel and operating system'
run_cmd uname uname -a
run_cmd architecture uname -m
run_cmd os_release cat /etc/os-release
run_cmd proc_version cat /proc/version

section 'cpu summary'
if command -v awk >/dev/null 2>&1; then
  awk '
    /^processor[[:space:]]*:/ || /^model name[[:space:]]*:/ || /^CPU implementer[[:space:]]*:/ || /^CPU architecture[[:space:]]*:/ || /^CPU part[[:space:]]*:/ || /^Features[[:space:]]*:/ { print }
  ' /proc/cpuinfo 2>&1 || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: awk\n'
fi
run_cmd cpu_count getconf _NPROCESSORS_ONLN

section 'libc and loader'
run_cmd libc_version getconf GNU_LIBC_VERSION
run_cmd ldd_version ldd --version
run_path dynamic_loader /lib/ld-linux-aarch64.so.1
run_path libstdcxx /usr/lib/libstdc++.so
run_path libgcc /usr/lib/libgcc_s.so

section 'memory and storage'
run_cmd free free -h
run_cmd disk df -h
section 'mounts (credential fields redacted)'
if command -v mount >/dev/null 2>&1; then
  mount 2>&1 | sed \
    -e 's/password=[^, ]*/password=<redacted>/g' \
    -e 's/passwd=[^, ]*/passwd=<redacted>/g' \
    -e 's/credentials=[^, ]*/credentials=<redacted>/g' \
    -e 's/username=[^, ]*/username=<redacted>/g' \
    -e 's/user=[^, ]*/user=<redacted>/g' \
    || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: mount\n'
fi

section 'network'
run_cmd ipv4 ip -4 addr
if command -v ss >/dev/null 2>&1; then
  section 'tcp 22 listener'
  ss -ltn 2>&1 | awk '$4 ~ /(^|:)22$/ { print }' || printf 'exit_code=%s\n' "$?"
elif command -v netstat >/dev/null 2>&1; then
  section 'tcp 22 listener'
  netstat -ltn 2>&1 | awk '$4 ~ /(^|:)22$/ { print }' || printf 'exit_code=%s\n' "$?"
else
  section 'tcp 22 listener'
  printf 'NOT_AVAILABLE: ss/netstat\n'
fi

section 'process access services'
if command -v ps >/dev/null 2>&1; then
  ps 2>&1 | grep -E '[s]shd|[d]ropbear' || printf 'no sshd/dropbear process found\n'
else
  printf 'NOT_AVAILABLE: ps\n'
fi

section 'npu device nodes'
for path in /dev/hard_npu /dev/soft_npu; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    ls -l "$path" 2>&1 || printf 'exit_code=%s\n' "$?"
  else
    printf 'NOT_AVAILABLE: %s\n' "$path"
  fi
done

section 'loaded modules'
run_cmd lsmod lsmod

section 'npu kernel modules on disk'
if command -v find >/dev/null 2>&1 && [ -d /lib/modules ]; then
  find /lib/modules -type f \( -iname '*npu*.ko' -o -iname '*cma*.ko' \) -print 2>&1 || printf 'exit_code=%s\n' "$?"
else
  printf 'NOT_AVAILABLE: /lib/modules or find\n'
fi
