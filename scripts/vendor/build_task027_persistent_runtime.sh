#!/usr/bin/env bash
set -euo pipefail

# Run inside the approved Anlogic VM. This creates a new user-space Buildroot
# output and never partitions, mounts, or writes a block device.

MODE=check
ROOT=${TASK027_ROOT:-/home/uisrc/task027-repro}
SOURCE_ROOT=${TASK025_SOURCE_ROOT:-/home/uisrc/task025-repro/uisrc-lab-anlogic-pdf-20260805}
OVERLAY_SRC=${TASK027_OVERLAY_SRC:-}
PUBLIC_KEY_FILE=${TASK027_PUBLIC_KEY_FILE:-}
BUILD_ROOT=${TASK027_BUILD_ROOT:-$ROOT/uisrc-lab-anlogic-task027}
BUILDROOT_SRC=${TASK027_BUILDROOT_SRC:-$SOURCE_ROOT/sources/buildroot}
BASE_OUTPUT=${TASK025_OUTPUT:-$SOURCE_ROOT/results/task025-buildroot-output-20260806}
MODULE_SOURCE_ROOT=${TASK025_FORMAL_ROOTFS:-$SOURCE_ROOT/results/task025-formal-rootfs-extract-20260806}
FORMAL_OVERLAY_ROOT=${TASK025_FORMAL_OVERLAY:-$SOURCE_ROOT/results/task025-formal-rootfs-overlay-20260806}
OUTPUT=${TASK027_OUTPUT:-$BUILD_ROOT/results/task027-buildroot-output}
OVERLAY=${TASK027_OVERLAY:-$BUILD_ROOT/rootfs_overlay}

usage() {
    cat <<EOF
Usage: $0 [--check|--build]

Environment overrides are TASK027_ROOT, TASK025_SOURCE_ROOT,
TASK027_OVERLAY_SRC, TASK027_PUBLIC_KEY_FILE, TASK027_BUILD_ROOT,
TASK027_BUILDROOT_SRC, TASK025_OUTPUT, TASK027_OUTPUT and TASK027_OVERLAY.
TASK025_FORMAL_ROOTFS may point at the Task 025 same-source module staging.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check|--build) MODE=${1#--}; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "$OVERLAY_SRC" ]; then
    echo "TASK027_OVERLAY_SRC is required" >&2
    exit 2
fi

required_overlay=(
    etc/network/interfaces
    etc/dhcpcd.conf
    etc/edgeai/runtime.conf
    etc/edgeai/authorized_keys
    etc/init.d/S41edgeai-network
    etc/init.d/S49edgeai-ssh-keys
    etc/init.d/S98edgeai-npu
    usr/bin/edgeai-npu-healthcheck
    usr/bin/edgeai-camera-demo-manual
)

for rel in "${required_overlay[@]}"; do
    [ -e "$OVERLAY_SRC/$rel" ] || { echo "overlay missing: $rel" >&2; exit 1; }
done

if grep -RIl --exclude='*.pub' 'BEGIN .* PRIVATE KEY' "$OVERLAY_SRC" >/dev/null 2>&1; then
    echo "private key material found in overlay" >&2
    exit 1
fi

if [ -n "$PUBLIC_KEY_FILE" ]; then
    [ -f "$PUBLIC_KEY_FILE" ] || { echo "public key file missing: $PUBLIC_KEY_FILE" >&2; exit 1; }
    grep -qE '^(ssh-(ed25519|rsa)|ecdsa-sha2-)' "$PUBLIC_KEY_FILE" || {
        echo "public key file is not an OpenSSH public key" >&2
        exit 1
    }
    if grep -q 'BEGIN .* PRIVATE KEY' "$PUBLIC_KEY_FILE"; then
        echo "private key was supplied where a public key is required" >&2
        exit 1
    fi
fi

if [ "$MODE" = check ]; then
    printf 'TASK027_OVERLAY=PASS\n'
    printf 'BUILDROOT_SOURCE=%s\n' "$BUILDROOT_SRC"
    printf 'BASE_OUTPUT=%s\n' "$BASE_OUTPUT"
    printf 'NETWORK=eth0:192.168.50.2/24\n'
    printf 'NPU_ORDER=cma_mem,hard_npu,soft_npu\n'
    printf 'CAMERA_AUTOSTART=false\n'
    exit 0
fi

[ -d "$BUILDROOT_SRC" ] || { echo "Buildroot source missing: $BUILDROOT_SRC" >&2; exit 1; }
[ -d "$BASE_OUTPUT" ] || { echo "Task 025 output missing: $BASE_OUTPUT" >&2; exit 1; }
[ -d "$MODULE_SOURCE_ROOT/lib/modules/6.1.111-rt42/extra" ] || { echo "Task 025 module staging missing: $MODULE_SOURCE_ROOT" >&2; exit 1; }
[ -d "$FORMAL_OVERLAY_ROOT" ] || { echo "Task 025 formal overlay missing: $FORMAL_OVERLAY_ROOT" >&2; exit 1; }
[ ! -e "$BUILD_ROOT" ] || { echo "refusing to overwrite existing build root: $BUILD_ROOT" >&2; exit 1; }

mkdir -p "$BUILD_ROOT"
mkdir -p "$(dirname "$OUTPUT")"
cp -a "$BASE_OUTPUT" "$OUTPUT"
mkdir -p "$OVERLAY"
# Reuse only the already audited Task 025 customdata/runtime overlay. The
# Task 027 files below intentionally override its init/network policy.
cp -a "$FORMAL_OVERLAY_ROOT"/. "$OVERLAY"/
cp -a "$OVERLAY_SRC"/. "$OVERLAY"/
if [ -n "$PUBLIC_KEY_FILE" ]; then
    install -m 0600 "$PUBLIC_KEY_FILE" "$OVERLAY/etc/edgeai/authorized_keys"
fi
mkdir -p "$OVERLAY/lib/modules/6.1.111-rt42/extra"
for module in cma_mem hard_npu soft_npu; do
    source_module="$MODULE_SOURCE_ROOT/lib/modules/6.1.111-rt42/extra/$module.ko"
    [ -f "$source_module" ] || { echo "same-source module missing: $source_module" >&2; exit 1; }
    install -m 0644 "$source_module" "$OVERLAY/lib/modules/6.1.111-rt42/extra/$module.ko"
done
if grep -RIl 'BEGIN .* PRIVATE KEY' "$OVERLAY" >/dev/null 2>&1; then
    echo "private key material found in generated overlay" >&2
    exit 1
fi

CONFIG="$OUTPUT/.config"
[ -f "$CONFIG" ] || { echo "Buildroot output .config missing: $CONFIG" >&2; exit 1; }
if grep -q '^BR2_ROOTFS_OVERLAY=' "$CONFIG"; then
    sed -i "s|^BR2_ROOTFS_OVERLAY=.*|BR2_ROOTFS_OVERLAY=\"$OVERLAY\"|" "$CONFIG"
else
    printf '\nBR2_ROOTFS_OVERLAY="%s"\n' "$OVERLAY" >> "$CONFIG"
fi

# A missing file in this primary-site-only directory is a hard failure rather
# than permission to contact the network.
make -C "$BUILDROOT_SRC" O="$OUTPUT" \
    BR2_PRIMARY_SITE=file:///__task027_no_network__ BR2_BACKUP_SITE= olddefconfig
make -C "$BUILDROOT_SRC" O="$OUTPUT" \
    BR2_PRIMARY_SITE=file:///__task027_no_network__ BR2_BACKUP_SITE=

MKIMAGE="$OUTPUT/host/bin/mkimage"
[ -x "$MKIMAGE" ] || MKIMAGE=$(command -v mkimage || true)
[ -x "$MKIMAGE" ] || MKIMAGE=$(find "$SOURCE_ROOT" -type f -path '*/u-boot/tools/mkimage' -perm -0100 | head -1)
[ -x "$MKIMAGE" ] || { echo "mkimage not found in Buildroot host output" >&2; exit 1; }
"$MKIMAGE" -A arm64 -T ramdisk -C lz4 -n Initrd \
    -d "$OUTPUT/images/rootfs.cpio.lz4" "$OUTPUT/images/uInitrd.lz4"

sha256sum "$OUTPUT/images/rootfs.tar.gz" "$OUTPUT/images/rootfs.cpio.lz4" \
    "$OUTPUT/images/uInitrd.lz4" > "$BUILD_ROOT/task027-rootfs-sha256sums.txt"
printf 'TASK027_BUILD=PASS\nOUTPUT=%s\nOVERLAY=%s\n' "$OUTPUT" "$OVERLAY"
