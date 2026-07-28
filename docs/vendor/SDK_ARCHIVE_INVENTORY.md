# SDK archive inventory

Audit date: 2026-07-24 (Asia/Shanghai)

This audit reads only ZIP central-directory metadata and runs a read-only CRC/
integrity test. No member was extracted, opened as a document, executed, or
written into the repository. Complete member listings are outside the
repository at:

`/home/dministrator/vendor/anlogic-dr1-knowledge/logs/archive_inventory/`

## Archive summary

| ID | Archive size | Members | Uncompressed total | SHA256/integrity | Top level | Assessment |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `secondary_demo_archive` | 114,924,599 | 3,485 | 206,782,523 | match / valid | `boot`, `soc_dts`, `soc_hw`, `soc_prj`, `soc_sdk` | FPSoC boot/project workspace |
| `linux_base_archive` | 121,364,628 | 3,526 | 227,410,095 | match / valid | `Linux Base Appendix` | Linux base example bundle |
| `linux_driver_archive` | 1,040,244,482 | 28,199 | 1,912,595,064 | match / valid | `Sourcecode` | Repeated Linux driver examples and generated artifacts |

The compressed member totals were 113,991,427, 120,212,112, and 1,031,275,498
bytes respectively. No archive had a sibling split marker or a failed CRC
test. No member reached the 100 MiB uncompressed large-member threshold; the
largest member in each archive is nevertheless a generated boot image or IDE
index and is listed in the external inventory.

Exact source paths (read from `local_sdk_inventory.yaml`):

- `secondary_demo_archive`: `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/04_secondary_developmemt/demo.zip`
- `linux_base_archive`: `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/3-4_ex_soc_linux/01_ex_linux_base_F3P_DR1M90G.zip`
- `linux_driver_archive`: `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/3-4_ex_soc_linux/02_ex_linux_drive_F3P_DR1M90G.zip`

## Marker findings

### `secondary_demo_archive`

- SDK-like names: two `VERSION` files and five README-like files, including
  `soc_sdk/.metadata/version.ini`.
- Buildroot, `output/host`, `output/staging`, `output/target`, toolchain,
  sysroot and libc markers: none.
- Kernel-like names: 13, including `soc_dts/kernel-dts/anlogic-dr1.dts`.
- NPU-like names: two `.hpf` files and three `.bit` files.
- The top-level layout resembles the already observed FPSoC project workspace,
  not a versioned Linux SDK. `recommended_action` is
  `selective_metadata_extract`.

### `linux_base_archive`

- SDK-like names: two `VERSION` files and five README-like files under
  `Linux Base Appendix/Chapter 3/soc_sdk`.
- Buildroot, compiler, sysroot and libc markers: none.
- Kernel-like names: 13, including an `anlogic-dr1.dts` device-tree file.
- NPU-like names: two `.hpf` files and three `.bit` files.
- The archive contains `boot/uInitrd.lz4`, `boot/uImage.lz4`, `BOOT.bin` and
  generated `system.bit` files, but names alone do not prove SDK identity.
  `recommended_action` is `selective_metadata_extract`.

### `linux_driver_archive`

- SDK-like names: 16 `VERSION` files and 42 README-like files, repeated across
  demo workspaces.
- Buildroot, compiler, sysroot and libc markers: none.
- Kernel-like names: 118 `kernel` matches, 32 module-related names and 16
  `.ko` files.
- NPU-like names: 16 `.hpf` files and 24 `.bit` files.
- Two filenames carry a legacy non-UTF-8 filename flag. The ZIP integrity test
  still passed; the names require encoding review if later selected for copying.
- The 1.91 GB uncompressed tree is dominated by repeated examples and build
  outputs. `recommended_action` is `selective_metadata_extract`, not full
  extraction.

## Could these be complete Linux SDKs?

No archive is currently a high-confidence complete Linux SDK or an identified
`SDK_2026.01` package. The central directory contains no explicit
`SDK_2026.01`, Buildroot tree, AArch64 compiler, sysroot, Arm NN, OpenCV
package, or `libnpu_runtime` path. Repeated `soc_sdk` directory names and HPF
files are filename evidence only and must not be promoted to a version or
compatibility claim.

## Recommended next action

Selective extraction of small, human-readable metadata is reasonable after
separate approval. Candidate members are the small `version.ini`, top-level
README/Makefile/build-script files, and any explicit manifest or release note
that can be verified without unpacking generated images or binaries. Preserve
source path, archive SHA256, member CRC, member size and extracted-file SHA256.

Full extraction is not recommended now. In particular, the driver archive
would materialize approximately 1.91 GB before temporary and duplicate-output
overhead, while its directory contains no toolchain or Buildroot markers.

No network access, Git LFS download, qmd embedding/query/vector search,
compilation, demo execution, or vendor-source modification was performed.
