#!/bin/sh
# Task 024 read-only board mapping probe. It never writes media, sysfs,
# firmware, Device Tree, modules, or system libraries.
set -eu

printf '%s\n' '[identity]'
uname -a
uname -m
cat /etc/os-release 2>/dev/null || true
getconf GNU_LIBC_VERSION 2>/dev/null || true

printf '%s\n' '[boot_and_mounts]'
cat /proc/cmdline 2>/dev/null || true
mount 2>/dev/null || true
find /boot /mnt /media -maxdepth 3 -type f \( -name 'BOOT.bin' -o -name 'boot.scr' -o -name '*.dtb' -o -name 'Image' -o -name 'uImage*' -o -name '*.bit' \) -print 2>/dev/null | sort || true
for f in /mnt/mmcblk1p1/BOOT.bin /mnt/mmcblk1p1/boot.scr /mnt/mmcblk1p1/system.dtb /mnt/mmcblk1p1/uImage.lz4; do
    if [ -f "$f" ]; then sha256sum "$f"; file "$f" 2>/dev/null || true; fi
done

printf '%s\n' '[device_tree]'
find /proc/device-tree /sys/firmware/devicetree/base -maxdepth 4 -type f \( -name compatible -o -name reg -o -name interrupts -o -name status -o -name name \) -print 2>/dev/null | sort | head -400 || true
if [ -e /sys/class/fpga_manager/fpga0/name ]; then
    printf '%s\n' '[fpga_manager]'
    cat /sys/class/fpga_manager/fpga0/name
    cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || true
fi
if [ -e /sys/bus/platform/devices/63f00000.hard_npu ]; then
    printf '%s\n' '[hard_npu_binding]'
    readlink /sys/bus/platform/devices/63f00000.hard_npu/driver 2>/dev/null || true
fi

printf '%s\n' '[kernel_and_memory]'
grep -iE '^(MemTotal|MemAvailable|CmaTotal|CmaFree):' /proc/meminfo 2>/dev/null || true
cat /proc/iomem 2>/dev/null || true
for p in /proc/config.gz /boot/config-$(uname -r) /boot/config; do
    if [ -f "$p" ]; then printf 'kernel_config=%s\n' "$p"; break; fi
done

printf '%s\n' '[modules_and_devices]'
lsmod 2>/dev/null || true
find /lib/modules -type f 2>/dev/null | sort || true
find /dev -maxdepth 2 \( -iname '*npu*' -o -iname '*cma*' -o -iname '*fpga*' \) -print 2>/dev/null | sort || true

printf '%s\n' '[logs_and_firmware]'
dmesg 2>/dev/null | grep -iE 'npu|cma|fpga|firmware|device.tree|hard_npu|soft_npu' | tail -300 || true
find /sys/firmware /sys/devices -maxdepth 5 -iname '*fpga*' -o -iname '*firmware*' 2>/dev/null | sort | head -300 || true
