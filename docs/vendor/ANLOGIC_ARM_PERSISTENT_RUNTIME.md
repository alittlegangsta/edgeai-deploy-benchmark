# Anlogic DR1 persistent runtime (Task 027)

Task 027 adds a Buildroot overlay for the already approved Task 025 SD
candidate. It is deliberately a boot-time configuration change, not a new
inference implementation or a performance benchmark.

The overlay configures `eth0` to `192.168.50.2/24`, leaves the existing
OpenSSH `S50sshd` service in charge of starting `sshd`, and installs the
approved public key before that service starts. Host keys are generated on the
first boot and copied to `/mnt/mmcblk0p1/edgeai-runtime/ssh`; later boots
restore them before `sshd`. If the boot partition cannot be mounted, the
startup log explicitly reports that the current boot's host keys are
ephemeral.

NPU startup follows the source-derived Task 026 order:

```text
cma_mem -> hard_npu -> soft_npu
```

The sequence stops on the first failure and writes a health report to `/run`.
`/usr/bin/edgeai-npu-healthcheck` checks the module state, device nodes,
HardNPU/SoftNPU platform bindings, CMA size, the static address, `sshd`, and
the persisted host-key location. The camera Demo is not referenced by an init
script. It is available only through the explicit manual wrapper
`/usr/bin/edgeai-camera-demo-manual`.

The first candidate `uInitrd.lz4` was separately approved, written as a
single-file SD update, and booted. That running candidate restored all four
private host keys, kept the expected ed25519 identity across the
user-observed reboot, configured `eth0`, started `sshd`, and loaded the three
NPU modules. Its FAT mount used `fmask=0022,dmask=0022`, however, so persisted
private keys were physically readable through the mounted FAT view and the
`.pub` sidecars were absent. The running health check therefore remains useful
for network/NPU status but is not evidence that the sidecar repair is present.

The repair overlay now restores every private key with mode 600, derives a
missing public sidecar with `ssh-keygen -y`, applies `sshd -t` before service
startup, and computes the health-check fingerprint from the private key rather
than requiring a sidecar. It requests `fmask=0177,dmask=0077` for the FAT boot
partition. The offline key-fix Buildroot candidate is:

```text
uInitrd.lz4: 358048b9aa73edeed6c3ee8e50b67bb4bde1cd062c1217d37ccbc06cd8442028
rootfs.tar.gz: dcd96fb90af07d34d7e988478cb9ca30d919c233ce83f7e7a8a1fb7dd7c509ea
rootfs.cpio.lz4: 723699855b09ee34507e5896d6ecd4d7b7293b55d76783ea5617b55877849587
ed25519 fingerprint: SHA256:4Dz+I9j354/XGF2bCFAUTz1qrSGqGQhHJoVCEos3hi8
```

The key-fix2 `uInitrd.lz4` was then written as the only changed FAT-root file
after stable-device guards. The old candidate was backed up, the new hash was
read back, all other root files were unchanged, and the filesystem was synced
and safely unmounted. Cold boot and one reboot both kept the network, sshd and
NPU stack healthy, but the FAT mount remained `fmask=0022,dmask=0022`; the
health-check therefore failed the persisted-key fingerprint gate even though
the private-key SHA matched. This candidate is retained as a real failed
validation, not deleted or reclassified.

Key-fix3 replaces the ineffective remount with a verified unmount followed by
a secure `fmask=0177,dmask=0077` mount. Its `uInitrd.lz4` SHA256 is
`0da5cad9ed0ec4f2987f250ff5d7d60f037cd6e3d99bc409503e4a44a54366c7`. After the
new explicit one-file approval it replaced only the FAT-root `uInitrd.lz4`,
passed readback and safe unmount, and passed cold boot plus one reboot. The
runtime mount retained `fmask=0177,dmask=0077`, `/etc/ssh` private keys were
mode 600, public sidecars were present, and the health-check passed. No eMMC
change or camera-demo autostart is part of this work.
