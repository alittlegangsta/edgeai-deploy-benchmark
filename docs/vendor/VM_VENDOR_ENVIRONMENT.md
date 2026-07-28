# VM vendor environment and staged inputs

Audit date: 2026-07-24

## Responsibilities

- WSL runs the repository scripts and invokes the VM only through
  `/home/dministrator/bin/anlogic-vm-ssh`.
- The Ubuntu 18.04 VM is the vendor SDK staging/build host.
- The future DR1 board remains a separate runtime target; no board operation is
  included here.
- Windows Putty remains a Windows-only serial-console tool and is not copied to
  the VM.

## Verified VM baseline

The VM is `ubuntu`, user `uisrc`, home `/home/uisrc`, Ubuntu `18.04.4 LTS`,
kernel `4.15.0-91-generic`, and architecture `x86_64`. SSH is active and the
VM has `192.168.244.128/24` on `ens33`. It reports 7.8G RAM, 162G free on the
root filesystem, GCC/G++ 7.5.0, Make 4.1, Python 3.6.9, GNU tar 1.29 and Git
2.17.1. CMake is not installed; no installation was attempted.

## VMware shared inputs

The shared folder `/mnt/hgfs/fpga_info` is available.

- SDK source: `/mnt/hgfs/fpga_info/sdk.2025.7.tar.gz`
- NPU Demo source:
  `/mnt/hgfs/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/05-5_NPU演示`

The SDK is 1,368,135,226 bytes with SHA256
`c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`.
The Demo source contains 1,321 files and 460 directories, with a measured
source size of 713,313,118 bytes.

## VM destinations

The existing destinations were verified without copying; the authorized execute
step therefore skipped both transfers because their content identities matched:

- `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz` has the same SDK
  SHA256 as the shared source.
- `/home/uisrc/vendor/anlogic/demos/milianke_npu_demo` has 1,321 files and
  460 directories. Its content-tree digest matches the source:
  `c82767562ba9e07d8ca6bf3842b32b366d08bc5b9cafa113bdaadd908882202a`.

The authorized execute step created the missing `builds/`, `manifests/`, and
`logs/input_staging/` directories and generated six input-staging logs under
`/home/uisrc/vendor/anlogic/logs/input_staging/`.

## Current safety boundary

- The SDK archive remains intact and was not extracted by this session. However,
  a pre-existing expanded tree exists at
  `/home/uisrc/vendor/anlogic/sdk/sdk` (mtime `2025-09-08 10:31:53 +0800`,
  125,421 files, 12,577 directories, 2,877,807,733 bytes). It was not created,
  deleted, or modified by this session, so the strict single-unextracted-tree
  acceptance criterion is not met.
- No vendor script or NPU Demo was executed.
- No SDK or Demo source was modified.
- No dependency was installed.
- No Putty files were copied.
- The SDK source and destination SHA256 values both remain
  `c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0`.
- The Demo source and destination tree digest both remain
  `c82767562ba9e07d8ca6bf3842b32b366d08bc5b9cafa113bdaadd908882202a`.
- No Git commit was created.

## Next step

The staging operation is complete and idempotent. A human must decide whether
the pre-existing expanded SDK tree is an accepted prior artifact or requires a
separately authorized cleanup; this session will not delete or alter it.
