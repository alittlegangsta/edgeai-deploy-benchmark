#!/usr/bin/env bash
set -euo pipefail

OVERLAY=${1:-configs/task027/rootfs_overlay}
[ -d "$OVERLAY" ] || { echo "overlay not found: $OVERLAY" >&2; exit 1; }

for f in "$OVERLAY/etc/init.d/S41edgeai-network" \
         "$OVERLAY/etc/init.d/S49edgeai-ssh-keys" \
         "$OVERLAY/etc/init.d/S98edgeai-npu" \
         "$OVERLAY/usr/bin/edgeai-npu-healthcheck" \
         "$OVERLAY/usr/bin/edgeai-camera-demo-manual"; do
    sh -n "$f"
done

grep -q '192\.168\.50\.2/24' "$OVERLAY/etc/edgeai/runtime.conf"
grep -q 'fmask=0177,dmask=0077' "$OVERLAY/etc/edgeai/runtime.conf"
grep -q 'ssh-keygen -y' "$OVERLAY/etc/init.d/S49edgeai-ssh-keys"
grep -q 'sshd -t' "$OVERLAY/etc/init.d/S49edgeai-ssh-keys"
grep -q 'secure_mount_active' "$OVERLAY/etc/init.d/S49edgeai-ssh-keys"
grep -q 'umount "\$EDGEAI_SD_BOOT_MOUNT"' "$OVERLAY/etc/init.d/S49edgeai-ssh-keys"
grep -q 'cma_mem.*hard_npu.*soft_npu' "$OVERLAY/etc/init.d/S98edgeai-npu"
grep -q 'no automatic camera start' "$OVERLAY/usr/bin/edgeai-camera-demo-manual"
grep -q 'fingerprint_from_private' "$OVERLAY/usr/bin/edgeai-npu-healthcheck"
! grep -RIl 'BEGIN .* PRIVATE KEY' "$OVERLAY" >/dev/null 2>&1

printf 'overlay_static_check=PASS\n'
