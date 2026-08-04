#!/bin/sh
# Read-only board-side Task 022 audit.  This script never loads a module or
# writes a sysfs, device-tree, firmware, or system-library path.
set -eu

printf '%s\n' '[identity]'
uname -a
uname -m
cat /etc/os-release 2>/dev/null || true
getconf GNU_LIBC_VERSION 2>/dev/null || true
printf '%s\n' '[kernel_and_memory]'
cat /proc/cmdline 2>/dev/null || true
grep -iE '^(MemTotal|MemAvailable|CmaTotal|CmaFree):' /proc/meminfo 2>/dev/null || true
printf '%s\n' '[modules]'
lsmod 2>/dev/null || true
find /lib/modules -type f 2>/dev/null | grep -Ei '/(hard_npu|soft_npu|cma_mem).*\.ko$|npu|cma' || true
printf '%s\n' '[devices]'
find /dev -maxdepth 2 \( -iname '*npu*' -o -iname '*cma*' -o -iname '*acceler*' \) -print 2>/dev/null || true
printf '%s\n' '[sysfs_and_device_tree]'
find /sys -maxdepth 5 \( -iname '*npu*' -o -iname '*cma*' -o -iname '*acceler*' \) -print 2>/dev/null | head -200 || true
printf '%s\n' '[dmesg_matches]'
dmesg 2>/dev/null | grep -iE 'npu|cma|accelerator|soft_npu|hard_npu|video_npu' | tail -200 || true
printf '%s\n' '[rootfs_runtime_candidates]'
find /lib /usr/lib /usr/local/lib /opt /root /home -type f \( -iname '*npu*' -o -iname '*armnn*' -o -iname '*runtime*' -o -iname '*.ko' -o -iname 'rt.bin' -o -iname 'weight.bin' -o -iname 'model.bin' \) -print 2>/dev/null | head -300 || true
