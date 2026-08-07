# Task 026

## Title

MLK-F3P-CZ02 NPU controlled SD deployment and first-boot validation.

## Status

Completed

## Stage and dependency

Stage 4 controlled NPU deployment. Depends on Task 025 (`Completed`).

## Recommended branch

`feature/anlogic-npu-controlled-sd-deployment`

## Final result

The read-only preflight, user-approved SD write/readback, physical first boot,
module binding, and official Arm NN camera demo all passed. The reversible
source-derived module sequence `cma_mem.ko -> hard_npu.ko -> soft_npu.ko`
loaded successfully. After a retained pre-camera failure, the official demo
ran with only the `Alnpu` backend enabled, assigned graph layers to
`Alnpu | ALHardNPU`, completed decoder/post-process work, and exited 0.

Final result: `FIRST_BOOT_PASS_NPU_DEMO_PASS`.
This is functional one-shot evidence only; no performance benchmark was run.

## Scope

- Recompute all 13 Task 025 candidate file hashes and verify `SHA256SUMS`.
- Enumerate visible WSL block devices with `lsblk`, `blkid`, `udevadm` and
  `/sys/block`; record path, size, vendor/model, serial, transport,
  `removable`, mounts, partitions, filesystems and read-only state.
- Build an explicit exclusion list for system disks, WSL/VM disks, Windows
  disks, board eMMC and any identity-ambiguous device.
- Read and statically audit `make_parted.sh`, `deploy_image.sh`,
  `parameter-tf-fat.txt`, `create_image.sh`, boot scripts and deployment paths.
- Produce a precise, default-dry-run SD write plan and explicit user approval
  string. A wrapper, if needed, must fail closed on path, capacity, model,
  serial, `removable=1` and one-time confirmation mismatches.

## Acceptance criteria for this phase

1. Task 025's 13-file candidate manifest and aggregate checksum are verified,
   or the phase is blocked with the exact missing/unavailable files.
2. Every visible block device is recorded and every non-target device has an
   explicit exclusion reason.
3. Vendor write scripts are not executed; destructive commands and data-loss
   scope are documented from static inspection.
4. The plan identifies partition layout, filesystem expectations, per-file
   post-write verification, failure stop conditions, removal/recovery and
   serial first-boot steps.
5. Before user approval, the result must be exactly
   `AWAITING_EXPLICIT_SD_WRITE_APPROVAL` with `deployment_approval=PENDING` and
   `sd_write=NOT_PERFORMED`. After an explicit approval, a separate execution
   record may advance the phase to post-write verification without touching the
   board.

## Allowed files

- `tasks/026_mlk_f3p_cz02_npu_controlled_sd_deployment.md`
- `TASKS.md`
- `results/evidence/026/*.json`
- `scripts/vendor/validate_task026_sd_preflight.py`
- `scripts/vendor/run_task026_sd_preflight.sh`

## Forbidden changes

- Do not modify Task 017--025 task files, manifests or evidence.
- Do not execute `make_parted.sh`, `deploy_image.sh`, `dd`, `mkfs`,
  `parted`, `fdisk`, mount/unmount user media, or any write wrapper.
- Read-only access to the running candidate board is permitted for the
  explicitly approved first-boot validation. The user additionally authorized
  reversible in-memory NPU module loading and one bounded official-demo
  attempt. Do not modify the eMMC, SD card, FPGA, Device Tree, boot files,
  network configuration, services, or VM system.
- Do not format, partition or write SD media, and do not install packages.
- Do not commit, push, create a PR, merge, rebase or reset in this phase.

## Execution record

- Start: `2026-08-06` Asia/Shanghai; branch and worktree were checked before
  this task file was created. The branch is
  `feature/anlogic-npu-controlled-sd-deployment`; worktree was clean.
- VM wrapper probes returned `UtilBindVsockAnyPort:307: socket failed 1` twice;
  no VM command or mutation was performed. Candidate-file verification must
  remain explicitly unavailable until the VM workspace is reachable or an
  approved local copy is found.
- `lsblk -J -O`, `blkid`, `udevadm info`, `/sys/block` and `findmnt` were run
  read-only. Five whole-disk entries were visible (`/dev/sda` 388.4 MiB,
  `/dev/sdb` 186 MiB, `/dev/sdc` 4 GiB swap, `/dev/sdd` 1 TiB current WSL
  root/project disk, `/dev/sde` 1 TiB). Every entry reported `Msft`/`Virtual
  Disk` or WSL mounts and `removable=0`; no physical SD candidate was found.
  `blkid` returned no records and `udevadm` reported `Unknown device` for the
  WSL block paths. Evidence: `results/evidence/026/block_device_inventory.json`.
- The Task 025 candidate manifest structure contains 13 entries and retains
  aggregate manifest SHA256
  `65e4d98db58e20c407b7e65e443bfe1774b692ccb49a0fd1b6f7062ebcf73ddd`, but its
  declared VM placeholder is not reachable and no local candidate override was
  supplied. No per-file hash was recomputed; all 13 files remain explicitly
  unavailable. Evidence: `results/evidence/026/candidate_manifest_verification.json`.
- Prior Task 025 safety evidence confirms `make_parted.sh` and
  `deploy_image.sh` are destructive and were never executed. Their source,
  `parameter-tf-fat.txt`, `create_image.sh` and boot-script paths could not be
  re-read because the VM wrapper was unavailable; hard-coded device and
  identity-check behavior therefore remains unknown. Evidence:
  `results/evidence/026/write_script_audit.json`.
- `bash scripts/vendor/run_task026_sd_preflight.sh --dry-run` exited 0 and
  generated the above evidence without invoking any destructive command.
  `python3 scripts/vendor/validate_task026_sd_preflight.py --evidence-dir
  results/evidence/026` exited 0. The phase result is
  `BLOCKED_PREWRITE_INPUTS_UNAVAILABLE`, not `AWAITING_EXPLICIT_SD_WRITE_APPROVAL`.
- Before the later user approval, safety state was
  `deployment_approval=PENDING`, `sd_write=NOT_PERFORMED`,
  `board_accessed=false`, and no write/format/partition/mount operation had
  been attempted.
- On 2026-08-06 at 13:07 +08:00 the requested recovery probes were retried:
  `/home/dministrator/bin/anlogic-vm-ssh 'printf VM_OK\\n; hostname; id -un'`
  and two further wrapper/direct-SSH variants. The wrapper and Windows
  `ssh.exe` still fail with `UtilBindVsockAnyPort:307: socket failed 1`; a
  read-only Linux SSH attempt to `192.168.244.128:22` timed out and a ping
  received no reply. The user-observed `/dev/sdb` details are retained as
  unverified provenance in `results/evidence/026/vm_connection_probe.json`;
  they do not replace the required command evidence. No candidate hash,
  exact byte size, serial/model query, or script-source recheck was claimed.

## Current stop condition

The SD write and first boot were separately approved and completed. The active
automatic stop is now the exact camera blocker: no `/dev/video0` or
`/dev/mipicam` is present, so the official camera demo cannot produce a frame
or establish an Arm NN backend assignment. Do not add a synthetic camera,
modify the FPGA/Device Tree, rewrite SD/eMMC, install packages, or claim Alnpu
execution without a real supported camera and a successful workload.

## Blocking Report

Current Task: 026
Current Status: Blocked
Last Successful Step: Local read-only evidence validation; Task 025 manifest structure and declared aggregate SHA256 were confirmed, and no destructive command was run.
Failed Command: `/home/dministrator/bin/anlogic-vm-ssh 'printf VM_OK\\n; hostname; id -un'` (retried three times); direct read-only SSH to `uisrc@192.168.244.128`; `ping -c 1 -W 2 192.168.244.128`.
Exit Code: wrapper probes failed with `UtilBindVsockAnyPort:307: socket failed 1`; direct SSH timed out; ping had 100% packet loss.
Relevant Error: The authorized VM endpoint is unreachable from the current WSL/SSH environment. The user-observed `/dev/sdb` is recorded as unverified provenance only; exact size bytes, vendor/model/serial/transport, candidate file hashes, and vendor script source cannot be obtained.
Files Changed: `TASKS.md`; `tasks/026_mlk_f3p_cz02_npu_controlled_sd_deployment.md`; `results/evidence/026/*.json`; Task 026 preflight scripts.
Attempts Made: Three wrapper retries, one direct Windows-OpenSSH probe, one direct Linux-SSH probe, and one read-only ping; no write, mount, unmount, board access, or VM mutation.
Why Automatic Recovery Is Unsafe: Continuing without VM-side identity, candidate hashes, and script source could authorize erasing the wrong device or writing an unverified candidate. The user observation cannot substitute for exact command evidence.
Exact Human Action Required: Restore read-only SSH reachability for `/home/dministrator/bin/anlogic-vm-ssh` to `192.168.244.128:22` (or provide an equivalent read-only VM session). Do not approve SD writing yet.
Commands to Resume: Re-run `/home/dministrator/bin/anlogic-vm-ssh 'printf VM_OK\\n; hostname; id -un; lsblk -J -O'`, then rerun the candidate hash, block-device, and script-source preflight.
Git Status: Task 026 changes remain uncommitted and unstaged; no push or PR was created.

## Recovery Record

- Human intervention restored the Windows SSH wrapper without any VM or media
  mutation. The recovery command
  `/home/dministrator/bin/anlogic-vm-ssh 'printf VM_OK\\n; hostname; id -un; uname -m'`
  succeeded under the approved read-only SSH execution context (`ubuntu`,
  `uisrc`, `x86_64`).
- The task resumed as `In Progress`. The VM-only device snapshot, candidate
  SHA256 recomputation, and static script audit passed and the prewrite evidence
  reached `AWAITING_EXPLICIT_SD_WRITE_APPROVAL`; the later user approval is
  recorded in `sd_write_execution.json`.

## Recovery Execution Record

- Recovery command succeeded through the restored Windows SSH wrapper:
  `/home/dministrator/bin/anlogic-vm-ssh 'printf VM_OK\\n; hostname; id -un; uname -m'`
  returned `VM_OK`, `ubuntu`, `uisrc`, `x86_64`.
- Read-only VM block-device evidence identified exactly one candidate:
  `/dev/sdb`, 31,299,993,600 bytes, vendor `Mass`, model `Storage Device`,
  serial `121220160204`, transport `usb`, `removable=1`, `RO=0`. Its existing
  `/dev/sdb1` is DOS/vfat, label `EDGEAI_DATA`, UUID `BA70-6249`, mounted at
  `/media/uisrc/EDGEAI_DATA`. `/dev/sda` is the 200G VMware root disk;
  `/dev/loop0`--`/dev/loop15` and `/dev/sr0` are explicitly excluded.
- `blockdev --getsize64 /dev/sdb` was attempted read-only but the unprivileged
  VM user received `Permission denied`; `lsblk -b` and `/sys/block/sdb/size`
  independently provide the exact 31,299,993,600-byte capacity. No sudo was
  used.
- Candidate root:
  `/home/uisrc/task025-repro/uisrc-lab-anlogic-pdf-20260805/results/task025-candidate-sd-fileset-20260806`.
  All 13 files exist, the aggregate `SHA256SUMS` hash is
  `65e4d98db58e20c407b7e65e443bfe1774b692ccb49a0fd1b6f7062ebcf73ddd`, and
  `sha256sum -c SHA256SUMS` returned `OK` for all entries. Evidence:
  `results/evidence/026/candidate_manifest_verification.json`.
- Static source review read `make_parted.sh`, `deploy_image.sh`,
  `parameter-tf-fat.txt`, `create_image.sh`, `create_dr1m_image.sh` and
  `boot.scr`. The selected `parameter-tf-fat.txt` branch creates one bootable
  FAT32 partition over the device; deployment copies the boot directory to
  that partition. No reviewed script was executed.
- `python3 scripts/vendor/validate_task026_sd_preflight.py --evidence-dir
  results/evidence/026` passed. JSON parsing, Bash syntax, Python compilation,
  the focused Task 022--025 tests (23 tests), and CTest (14/14) passed. The
  repository-wide Python discovery ran 100 tests but had six import errors for
  missing host `cv2`/`onnx`; no package installation or substitution was
  attempted. This environment limitation is unrelated to SD I/O.
- The approved write completed with
  `deployment_approval=APPROVED_BY_USER`, `sd_write=COMPLETED`,
  `media_unmounted=true`, `board_accessed=false` and readback verification
  PASS. The board first-boot gate remains pending.
- A final read-only staging check found that the 13-file candidate stores
  `uInitrd.lz4` under `rootfs/`, while `parameter-tf-fat.txt` loads it from the
  FAT root. The frozen file hash is unchanged; the controlled deployment plan
  explicitly maps `rootfs/uInitrd.lz4` to the FAT-root `uInitrd.lz4` destination.
  This normalization is required for boot-script consistency and does not add
  or substitute an asset.

## Approved Write Record

- The exact user approval string in `results/evidence/026/sd_write_execution.json`
  authorized erasing `/dev/sdb` with the recorded stable ID, capacity, model,
  serial and candidate aggregate hash. No board or serial-console operation
  was included in that approval.
- The controlled VM transaction unmounted `/dev/sdb1`, created an msdos table
  with one bootable full-device FAT32 partition, formatted it as `BOOT`, and
  copied the seven frozen boot files plus the normalized `uInitrd.lz4`.
- A read-only remount verified `lsblk`/`udevadm` metadata and all eight FAT-root
  SHA256 values. The final non-privileged `blkid` assertion in the transaction
  did not emit a value, so its completion marker was absent; this did not hide
  the write result because an independent read-only mount and hash pass was
  performed afterward. The partition is currently unmounted.
- The resulting status is `SD_WRITE_COMPLETED_FIRST_BOOT_PENDING`.
  First-boot validation still requires separate approval and may not start in
  this phase. Evidence: `results/evidence/026/sd_write_execution.json`.

## First-Boot Validation Record

### Pre-module gate snapshot

The following bullets are the immutable pre-module observations captured before
the user authorized the continuation below; they are not the current loaded
state.

- The user confirmed the physical first-boot conditions without requesting a
  second power cycle: SD inserted in the TF/SD slot, boot switch `ON-OFF-OFF`,
  serial connected and recording, and the board powered on. The sanitized
  record is in `results/evidence/026/first_boot_validation.json`; the complete
  raw serial transcript remains outside Git.
- `anlogic-board-ssh` then connected read-only to the running candidate system.
  Observed identity: hostname `buildroot`, root user, AArch64 Linux
  `6.1.111-rt42 #3 SMP PREEMPT Wed Aug 5 18:19:39 CST 2026`, Buildroot
  `2022.02.6`. The running root is an in-memory `rootfs`; `/dev/mmcblk0p1`
  is the 29.2 GiB SD boot partition and `/dev/mmcblk1` is the 7.30 GiB
  onboard eMMC. The eight files on `/mnt/mmcblk0p1` recomputed to the frozen
  Task 025 hashes, including `system.bit`, `system.dtb`, `uImage.lz4` and
  `uInitrd.lz4`.
- The live Device Tree reports model `Anlogic, DR1M90 FPSoc`,
  `anlogic,hard_npu` at `63f00000`, `anlogic,soft_npu` at `1f0000000`, an
  `anlogic,axi-vdma` node, FPGA manager, and a `shared-dma-pool` CMA node of
  128 MiB. `CmaTotal` is 131072 KiB and `CmaFree` is 124436 KiB. The chosen
  initrd range is present, consistent with the SD `uInitrd.lz4` boot path.
- The candidate `hard_npu.ko`, `soft_npu.ko`, and `cma_mem.ko` are installed
  under `/lib/modules/6.1.111-rt42/extra/`; their hashes and embedded vermagic
  match the Task 025 candidate. `lsmod` and `/sys/module` show no NPU module,
  both NPU platform devices are `UNBOUND`, and `/dev/hard_npu`,
  `/dev/soft_npu`, and `/dev/cma_mem` are absent.
- The candidate rootfs does contain the runtime-root demo, model, scripts and
  Arm NN libraries, but the top-level scripts refer to a missing `../bin`
  layout while the executable is under `runtime-root/bin`. This is recorded as
  a static packaging observation; no AArch64 demo was executed.
- The installed init scripts and both demo-script trees contain no NPU module
  insertion sequence. The approved D20.1 document lists the three kernel
  configuration symbols (`hard_npu_driver`, `soft_npu_driver`,
  `cma_mem_driver`) but does not define a runtime `insmod`/`modprobe` order.
  `modules.dep`, `modules.order`, and `modules.alias` are also absent. Since
  the task explicitly forbids guessing the order, the load gate is
  `BLOCKED_UNCONFIRMED_VENDOR_ORDER` and no module operation was attempted.
- Relevant boot diagnostics include successful CMA reservation, FPGA manager
  and Ethernet/SDHCI probes. Non-fatal warnings include an initial VDMA
  framebuffer channel request failure, an I2C mux probe failure, and FAT
  "not properly unmounted" messages. No NPU probe or registration line was
  observed.
- Pre-module first-boot result: `FIRST_BOOT_PASS_DRIVER_BLOCKED` (the state
  before the explicitly authorized module-load continuation).
  `physical_first_boot=COMPLETED`, `serial_boot_observed=PASS`,
  `linux_login=PASS`, and `candidate_sd_boot=PASS_PRELIMINARY`; driver/device
  readiness and official-demo execution remain incomplete at that historical
  point. No eMMC, FPGA, or SD state was modified by this validation.

## Module Load and Official Demo Record

- On 2026-08-07 10:55 +08:00, the source-derived sequence
  `cma_mem.ko -> hard_npu.ko -> soft_npu.ko` was used. This is explicitly
  recorded as an inference, not vendor runtime documentation: the NPU Makefile
  lists the same object order, `cma_mem` registers its misc device, and the two
  NPU drivers register independent OF platform drivers with no module
  dependencies.
- Each `insmod` returned 0. `cma_mem` registered `/dev/cma_mem`; HardNPU bound
  `63f00000.hard_npu` and created `/dev/hard_npu`; SoftNPU bound
  `1f0000000.soft_npu` and created `/dev/soft_npu`. The dmesg deltas reported
  IRQs 42/43 and the expected mapped regions; no unknown symbol, invalid
  module, oops, DMA, IRQ or CMA error was observed.
- The first camera-demo attempt is retained as `BLOCKED_NO_CAMERA` with exit
  code 255; it happened before the UVC device was enumerated and is not mixed
  into the successful run.
- After UVC enumeration, the official `yolo_demo_hdmi_camera` was run with
  `-b Alnpu`, `/dev/video0`, 640x480 geometry, the frozen ONNX model/config and
  a loopback UDP endpoint. The camera negotiated MJPEG 640x480 at 30 FPS, the
  graph report assigned layers to `Alnpu | ALHardNPU`, CMA weight usage was
  8.85 MB, the decoder produced 640x480 output, and the post-process workload
  completed. Exit code was 0, with no stderr or severe dmesg delta.
- Current result is `FIRST_BOOT_PASS_NPU_DEMO_PASS`. This is a functional
  one-shot confirmation only, not a camera performance benchmark.
- Evidence: `results/evidence/026/npu_module_load_validation.json`,
  `results/evidence/026/official_demo_validation.json`, and the updated
  `results/evidence/026/npu_module_preflight.json`.

### Continuation commands and outcomes

- Board reachability was restored through the existing wrapper with an
  approved elevated network call:
  `/home/dministrator/bin/anlogic-board-ssh 'printf BOARD_OK\\n; id -un; uname -r'`
  returned `BOARD_OK`, `root`, and `6.1.111-rt42`.
- The three actual load commands were run once each, in order:
  `insmod /lib/modules/6.1.111-rt42/extra/cma_mem.ko`,
  `insmod /lib/modules/6.1.111-rt42/extra/hard_npu.ko`, and
  `insmod /lib/modules/6.1.111-rt42/extra/soft_npu.ko`; all returned exit code
  0. Immediate dmesg, lsmod, platform-binding and device-node observations are
  preserved in the module-load evidence.
- A first local-only demo command omitted the required `--server` option and
  returned exit code 1 with the binary usage text; no workload ran. The actual
  bounded command was:
  `/opt/face_detection/runtime-root/bin/yolo_demo_hdmi_camera -m /opt/face_detection/runtime-root/inputs/yolo_face_uint8_15.onnx -u /opt/face_detection/runtime-root/inputs/example_yolo_face.json -s 127.0.0.1:12345 -i /dev/video0 -o /dev/fb0`.
  It returned exit code 255 with the recorded missing-camera messages and no
  dmesg delta. The subsequent successful command was:
  `/opt/face_detection/runtime-root/bin/yolo_demo_hdmi_camera -m /opt/face_detection/runtime-root/inputs/yolo_face_uint8_15.onnx -u /opt/face_detection/runtime-root/inputs/example_yolo_face.json -b Alnpu -s 127.0.0.1:12345 -i /dev/video0 --geometry 640x480 -l 1`.
  It returned exit code 0 and printed the Alnpu graph assignment and workload
  completion. Both endpoints were loopback-only; no external image data was
  sent.
- No additional module insertion, module unload, SD/eMMC operation, FPGA write,
  reboot, package installation, or project-model execution was performed after
  the successful one-shot.

### Historical blocking report resolution

The earlier VM/first-boot blocking report is retained as historical evidence.
The VM wrapper and board wrapper were subsequently restored, the candidate
hashes and SD write were independently verified, and the user explicitly
authorized the reversible module-load continuation. That prior block is
resolved; Task 026 is now `Completed` with the successful Alnpu demo result.

### Completion record

- `automated_validation`: `PASS`
- `first_boot_validation`: `PASS_PRELIMINARY`
- `npu_module_validation`: `PASS_INFERRED_ORDER`
- `official_demo`: `PASS_ALNPU`
- `cpu_fallback`: not allowed in the successful command
- `benchmark`: not performed
- `sd_write`: completed only under the prior explicit user approval; no further
  media operation was performed in this continuation
- Local Task 026 commit is recorded in the final Git handoff.
