# Task 027

## Title

Anlogic DR1 persistent board runtime.

## Status

Completed

## Dependency and branch

Depends on Task 026 (`Completed`). Work continues on the current controlled-SD
deployment branch. The initial single-file update and boot validation passed.
The key-fix2 single-file update was then deployed and tested, but its cold boot
and reboot failed the FAT permission-mask health gate. Key-fix3 was then
approved, written and validated through cold boot and one reboot.

## Scope

Create a reproducible Buildroot overlay for the approved MLK-F3P-CZ02 candidate
system. The overlay configures `eth0` as `192.168.50.2/24`, prepares OpenSSH
key and host-key persistence on the SD boot partition, loads the already
validated NPU modules in source-derived order `cma_mem -> hard_npu -> soft_npu`,
and exposes a read-only health-check command. The camera Demo remains manual;
no init script invokes it. A first single-file `uInitrd.lz4` update was completed.
The key-fix2 candidate (`358048…`) replaced only that same FAT-root file and
was booted, but failed the health gate; key-fix3 (`0da5…`) has now replaced
only that same FAT-root file and passed cold-boot and reboot validation.

The existing public key is an OpenSSH public key only. No private key is copied
to the image, repository, VM evidence, or Git. Host private keys are generated
at first boot and persisted on the writable SD boot partition, outside Git.

## Fixed runtime contract

- Board: MLK-F3P-CZ02-DR1M90, AArch64, Buildroot 2022.02.6, Linux
  6.1.111-rt42, glibc 2.25.
- Network: `eth0`, static `192.168.50.2/24`, no default route added.
- SSH: existing OpenSSH `S50sshd` remains the service entry point; `S49` only
  installs authorized keys and restores/generates host keys before it.
- Host-key persistence: `/mnt/mmcblk0p1/edgeai-runtime/ssh`; if the boot
  partition is unavailable, the script reports an explicit ephemeral-key
  warning rather than silently claiming persistence.
- Host-key identity: the ed25519 private key fingerprint is computed directly
  from `/etc/ssh/ssh_host_ed25519_key` and must match the persisted private key
  and `SHA256:4Dz+I9j354/XGF2bCFAUTz1qrSGqGQhHJoVCEos3hi8`.
- FAT key storage: the repair candidate requests `fmask=0177,dmask=0077`;
  private keys remain mode 600 and missing `.pub` sidecars are derived with
  `ssh-keygen -y` at boot.
- NPU modules: `cma_mem`, then `hard_npu`, then `soft_npu`; stop the sequence
  on the first `insmod` failure.
- Camera: `edgeai-camera-demo-manual` is an explicit manual wrapper only;
  `camera_autostart=false` is part of the evidence contract.
- No eMMC change, FPGA or Device Tree write is part of this phase. The initial
  and key-fix single-file updates and their separate boot evidence remain
  distinct.

## Acceptance criteria

1. Overlay static audit passes shell syntax and required-file checks.
2. Existing public-key fingerprint is recorded without any private-key file.
3. Offline Buildroot output is built in a new VM directory using the Task 025
   output and download cache; no network request occurs.
4. Formal `rootfs.tar.gz`, `rootfs.cpio.lz4`, and `uInitrd.lz4` hashes are
   recorded, and all supplied target ELF files remain AArch64 with no missing
   `DT_NEEDED` names.
5. Candidate rootfs contains the three same-source NPU modules and all startup
   scripts; static evidence shows no camera autostart.
6. A health-check contract covers modules, device nodes, platform binding, CMA,
   eth0, sshd and persisted host keys.
7. Task 026 evidence is immutable. The initial, key-fix2 and key-fix3
   single-file SD updates are separately recorded; only the explicitly
   approved FAT-root file was written and no eMMC change occurred.
8. After explicit approval, key-fix3 is written as the sole FAT-root update,
   passes cold-boot and reboot validation, and the task is marked `Completed`
   with `deployment_readiness=COMPLETED_VALIDATED`.

## Allowed files

- `tasks/027_anlogic_dr1_persistent_board_runtime.md`
- `TASKS.md`
- `ROADMAP.md`
- `docs/vendor/ANLOGIC_ARM_PERSISTENT_RUNTIME.md`
- `.knowledge/manifests/anlogic_arm_persistent_runtime.yaml`
- `configs/task027/rootfs_overlay/**`
- `scripts/vendor/build_task027_persistent_runtime.sh`
- `scripts/vendor/audit_task027_overlay.sh`
- `scripts/vendor/validate_task027_persistent_runtime.py`
- `results/evidence/027/*.json`

## Forbidden changes

- No SD/eMMC formatting or partitioning. The user-authorized key-fix2
  single-file replacement and its cold-boot/reboot observation are retained;
  no further replacement or reboot is allowed without a new approval.
  No FPGA or Device Tree write is permitted.
- No network package installation or dependency download.
- No private key, SDK, model, module, rootfs, uInitrd, ELF or other binary in
  Git. The public key in the overlay is not a private credential; its fingerprint
  is the only key identity repeated in evidence.
- Do not modify Task 017--026 task files, manifests or evidence.
- Do not push, create a PR, merge, rebase or reset.

## Execution record

- Start: 2026-08-07 Asia/Shanghai after Task 026 local commit `58f5e8c`.
- The Task 025 VM workspace is available through the read-only/build VM wrapper;
  its formal Buildroot output, AArch64 toolchain, OpenSSH/ifupdown/dhcpcd and
  141-entry download cache are the only build inputs.
- The formal build, static rootfs audit, hashes, and final readiness decision
  are recorded in `results/evidence/027/`.

### Build execution record

- VM identity was read as Ubuntu 18.04.4, x86_64, kernel 4.15.0-91-generic.
- The first isolated attempt stopped before copying the output parent; the
  build script was repaired to create that directory. A second static audit
  found that the copied Buildroot target did not contain the same-source NPU
  modules, so the module staging was injected. A third audit found that the
  customdata Arm NN overlay was outside the copied target; the already audited
  Task 025 formal overlay was then copied before the Task 027 overlay.
- The final clean output is
  `/home/uisrc/task027-repro/uisrc-lab-anlogic-task027-final3-20260807`.
  Buildroot `olddefconfig` and the normal target build both used
  `BR2_PRIMARY_SITE=file:///__task027_no_network__` and an empty backup site.
  The rootfs and uInitrd were generated successfully, with zero network
  requests. `/usr/bin/mkimage` wrapped the final `rootfs.cpio.lz4`.
- Final hashes and the static `353`-ELF / `0`-x86_64 / `78`-DT_NEEDED with no
  missing-name result are in `formal_rootfs_build.json` and
  `candidate_runtime_artifacts.json`. No target ELF was executed.

### Offline validation record

- Task 026, Tasks 022--025, and the Task 019 profile validators passed. The
  Task 027 validator passed with `COMPLETED_VALIDATED`; overlay audit,
  JSON/YAML parsing, Bash/Python syntax, focused tests (23/23), Release build
  (`ninja: no work to do`), CTest (14/14), Markdown-link, sensitive-material,
  and Task 026 immutability checks passed.
- Repository-wide Python discovery was also attempted with `PYTHONPATH=python`:
  100 tests were collected and 94 ran; six imports are unavailable in this
  host (`cv2` and `onnx`). No package was installed or substituted. This
  unrelated host limitation is retained in `results/evidence/027/validation.json`.
- The board was used only for user-authorized read-only validation of the
  deployed key-fix2 and key-fix3 candidates: cold boot, one reboot,
  health-check, mount, module, device-node and binding observations. No module
  loader, target ELF, camera Demo, eMMC, FPGA or Device Tree write was used by
  Task 027. The VM was used only for the isolated user-space Buildroot build
  and static artifact inspection.

### Host-key repair and runtime observation

- The running initial candidate restored all four host private keys and kept
  the expected ed25519 fingerprint across the user-observed reboot. Current and
  persisted private-key SHA256 values match, and `eth0`, `sshd`, all three NPU
  modules, device nodes, platform bindings and the existing health check pass.
- The running FAT mount exposed `fmask=0022,dmask=0022`, and the ed25519
  `.pub` sidecar was absent. This is retained as a real defect observation;
  it is not treated as private-key loss.
- The repair candidate restores all private keys, derives missing `.pub`
  sidecars with `ssh-keygen -y`, tests `sshd -t`, computes health fingerprints
  from private keys, and requests `fmask=0177,dmask=0077`. It was rebuilt in
  `/home/uisrc/task027-repro/uisrc-lab-anlogic-task027-keyfix2-20260807` with
  `uInitrd.lz4` SHA256
  `358048b9aa73edeed6c3ee8e50b67bb4bde1cd062c1217d37ccbc06cd8442028`.
- The key-fix2 candidate was written only to the approved FAT-root
  `uInitrd.lz4` after stable-ID, serial, size and removable guards. The old
  `a84cb5…` file was backed up, the new `358048…` hash was read back, all other
  root files were unchanged, and the filesystem was synced and safely
  unmounted.
- Key-fix2 cold boot and one reboot both kept `eth0=192.168.50.2/24`, `sshd`
  running, `cma_mem`, `hard_npu` and `soft_npu` loaded, all three device nodes
  present, and both platform drivers bound. Both boots nevertheless retained
  `fmask=0022,dmask=0022`; the persisted private-key SHA matched but its
  fingerprint could not be read under that FAT mode, so the health-check exited
  1. This is a real failed security gate, not a missing key.
- Key-fix3 was built offline with a verified unmount-before-secure-remount
  implementation. Its `uInitrd.lz4` SHA256 is
  `0da5cad9ed0ec4f2987f250ff5d7d60f037cd6e3d99bc409503e4a44a54366c7`; it was
  written as the only changed FAT-root file after the explicit
  `UPDATE-UINITRD-ONCE` approval. Readback and safe unmount passed; board cold
  boot and one reboot also passed.
- The user-authorized key-fix2 cold boot and one `/sbin/reboot` were captured
  through the board SSH wrapper. Both reported the deployed `358048…`
  `uInitrd.lz4`, `fmask=0022,dmask=0022`, matching current/persisted private-key
  SHA256, an empty persistent fingerprint field, and health-check exit code 1.
  No kernel oops, NPU probe failure, or storage write occurred.

### Latest offline/read-only recheck

- `python3 scripts/vendor/validate_task027_persistent_runtime.py
  --evidence-dir results/evidence/027` passes the completed key-fix3 boot and
  reboot evidence while retaining key-fix2's failed boot gate separately.
- Task 023, 024, 025 and 026 validators all passed; model-independent Python
  focused tests passed (`49` tests), Release CTest passed (`14/14`), JSON/YAML
  parsing, shell/Python syntax, overlay/artifact hash reconciliation and
  `git diff --check` passed.
- A mixed Python test invocation still cannot import the repository's optional
  `cv2`/`onnx` modules in this host; no package was installed or substituted.
- The current board was queried read-only after key-fix3 validation. It reports
  `eth0=192.168.50.2/24`, `sshd` running, `CmaTotal=131072 kB`, all three NPU
  modules/nodes and both platform bindings. The candidate FAT view reports
  `fmask=0177,dmask=0077`; `/etc/ssh` private keys are mode 600 and public
  sidecars are mode 644. A temporary mode-600 copy was used only when reading
  the persisted private-key fingerprint, then removed.
- The latest offline recheck passed the Task 027 validator, overlay audit,
  shell/Python syntax, 74 model-independent Python tests, CTest 14/14, JSON
  parsing and `git diff --check`. Tests requiring host `cv2` or `onnx` remain
  unavailable; no dependency was installed.

## Current disposition

Task 027 is `Completed`; `deployment_readiness` is
`COMPLETED_VALIDATED`. Key-fix2's failed FAT-mask validation remains retained
as historical evidence. Key-fix3 is written as the sole FAT-root update and
passed cold boot plus one reboot: secure FAT masks, `/etc/ssh` permissions,
public sidecars, host-key identity, network, sshd, CMA, NPU modules, device
nodes, platform bindings and health-check all passed. All Task 025 boot files
remain unchanged.
