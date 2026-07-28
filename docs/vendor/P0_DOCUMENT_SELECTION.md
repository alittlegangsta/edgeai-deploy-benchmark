# P0 document selection

This is a metadata-only first-pass inventory of the user-authorized Milianke
bundle. The configured source root was verified as:

`/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA`

The inventory contained 165,763 files, including 2,731 PDF/Markdown/TXT files.
The selection below uses paths, filenames, file sizes, modification timestamps,
and SHA256 values only. PDF bodies were not parsed and no source files were
copied. The approved first batch is explicitly marked below; all records remain
`index_status: not_indexed`.

## Approved first batch

The following 11 manifest records are the first manually approved copy set. The
approval is a curation decision based only on file path and material
organization. It does not prove document authority: no PDF revision page,
revision record, or content comparison has been used. The approved files remain
outside the repository and are still not indexed.

- `mlk_f3p_cz02_board_hw_manual`
- `mlk_cz02_core_hw_manual`
- `linux_factory_test`
- `linux_buildroot_secondary_development`
- `linux_basics`
- `fpsoc_application_development_alpha12`
- `dr1_product_overview_ug1214_dr1_copy`
- `apug1205_npu_reference_design`
- `ipug166_video_npu_user_manual`
- `putty_serial_login`
- `fpsoc_sdk_intro_2024`

The selected FPSoC and UG1214 records each have a second candidate with a
different SHA256. Those candidates are retained for comparison after a future,
explicitly authorized document-reading step.

## Deferred records

These records are intentionally retained with `approved_for_copy: false` and
`priority: P1`:

| ID | Reason for deferral |
| --- | --- |
| `linux_driver_development` | Large follow-on driver material; not required for the first metadata-approved copy set. |
| `linux_qt_demo` | Optional application demo, deferred until the target user-space is known. |
| `linux_ubuntu_demo` | OS/demo applicability is not established from metadata alone. |
| `linux_pl_multinet_demo` | Network-transfer candidate; exact transport support remains unverified. |
| `linux_wireless_demo` | Wireless-transfer candidate; board hardware and protocol remain unverified. |
| `fpsoc_application_development_alpha12_milianke_copy` | Near-identical FPSoC candidate; retain for later PDF revision/content comparison. |
| `dr1_product_overview_ug1214_root` | Alternate UG1214 candidate; retain for later PDF revision/content comparison. |
| `fpsoc_sdk_advanced_2025` | Related SDK guide; applicability and relationship to the 2024 guide remain unverified. |

Other unapproved records remain `approved_for_copy: false` and were not deleted.

## Initial P0 candidate inventory (before approval)

These records are the smallest metadata-supported set covering board bring-up,
Linux, build/toolchain, network access, and DR1/NPU references. The project
stages are planning labels, not evidence that any procedure has been verified.

| ID | Exact source path | Why needed | Project stage | Duplicate note |
| --- | --- | --- | --- | --- |
| `mlk_f3p_cz02_board_hw_manual` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/01_硬件手册/MLK_F3P_CZ02_DR1开发板硬件使用手册.pdf` | Board-specific physical interfaces and bring-up reference. | ARM board identification and deployment wiring | No same-hash P0 candidate; board boot test is only a related alternative. |
| `mlk_cz02_core_hw_manual` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/01_硬件手册/MLK_CZ02_DR1核心板硬件使用手册.pdf` | Core-board-specific hardware context. | Board provenance and interface validation | Unique in the selected P0 set. |
| `linux_factory_test` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/02_test_board/02-1_米联客-安路开发板Linux出厂系统测试.pdf` | Named factory Linux test procedure. | First board boot and smoke validation | Related by name to `linux_restore_factory`, not hash-equivalent. |
| `linux_buildroot_secondary_development` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/04_secondary_developmemt/04-1_米联客-安路开发板二次开发Buildroot篇.pdf` | Direct Buildroot secondary-development reference. | Toolchain and system-image planning | Unique in the selected P0 set. |
| `linux_basics` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/3-4_ex_soc_linux/ebook/3-4-01_米联客2024版安路F3P-CZ02-FPSoc Linux基础入门篇.pdf` | F3P-CZ02 Linux entry material. | Board user-space baseline | Unique in the selected P0 set. |
| `linux_driver_development` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/3-4_ex_soc_linux/ebook/3-4-02_米联客2024版安路F3P-CZ02-FPSoC Linux驱动开发篇.pdf` | Linux driver-development reference. | Runtime and device integration | Unique in the selected P0 set. |
| `linux_qt_demo` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/05_application_demo/05-1_QT环境搭建及demo演示/05-1_米联客-安路F3P-CZ02开发板QT环境搭建及demo演示.pdf` | Application-layer Qt setup/demo candidate. | Optional application environment validation | Unique in the selected P0 set. |
| `linux_ubuntu_demo` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/05_application_demo/05-2_Ubuntu桌面演示/05-2_米联客-安路F3P-CZ02开发板Ubuntu桌面演示.pdf` | Ubuntu user-space demonstration candidate. | OS-image and desktop capability review | Unique in the selected P0 set. |
| `fpsoc_application_development_alpha12` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/06_芯片手册/01_DR1/FPSoC应用开发说明_alpha1.2.pdf` | DR1 FPSoC application-development reference. | Chip/software integration | A near-identical filename has a different hash; human selection required. |
| `dr1_product_overview_ug1214_root` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/UG1214_安路科技DR1系列FPSoC产品说明书.pdf` | Product-family identity before using SDK/NPU claims. | Architecture and provenance freeze | Another UG1214 path has a different hash. |
| `apug1205_npu_reference_design` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/APUG1205_NPU参考设计文档.pdf` | Explicit NPU reference-design candidate. | NPU integration planning | Unique in the selected P0 set. |
| `ipug166_video_npu_user_manual` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/02_hardware/hardware_MLK_F3P_CZ02_DR1_20250526/IPUG166_Video_NPU_IP用户手册.pdf` | Explicit Video NPU IP manual candidate. | Video/NPU planning | Unique in the selected P0 set. |
| `putty_serial_login` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/01_prepare/01-2_米联客-安路开发板PuTTY安装与使用.pdf` | Serial/terminal access guide candidate. | Real-board login and evidence collection | Unique in the selected P0 set. |
| `fpsoc_sdk_intro_2024` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/03_demo/3-0_book_all/3_2_01_米联客2024版FPSoc_SDK入门篇.pdf` | SDK/toolchain entry candidate. | Build and deployment reproducibility | Related 2025 SDK guide has a different hash. |
| `linux_pl_multinet_demo` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/05_application_demo/05-3_PL端多网口方案/05-3_米联客-安路F3P-CZ02开发板Linux下PL多网口演示.pdf` | Network connectivity candidate for file-transfer planning. | Board transport and deployment | Related wireless demo has a different hash. |
| `linux_wireless_demo` | `/mnt/c/Users/Administrator/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/01_start/02_start_Linux/05_application_demo/05-4_无线通信方案/05-4_米联客-安路F3P-CZ02开发板无线通信方案.pdf` | Wireless transport candidate. | Board transport fallback | Related multi-network demo has a different hash. |

## P0 alternatives

These are retained for human review but should not be copied until a canonical
document or scope is approved. `dr1_product_overview_ug1214_dr1_copy` was moved
to the approved first batch; the alternate UG1214 record remains deferred.

- `fpsoc_application_development_alpha12_milianke` — near-identical
  alpha-1.2 filename with a different SHA256; possible reformat/version.
- `dr1_product_overview_ug1214_dr1_copy` — second UG1214 path with a different
  SHA256; possible reformat/version.
- `fpsoc_sdk_advanced_2025` — related 2025 SDK guide; select against the 2024
  SDK introduction only after version applicability is confirmed.
- `linux_restore_factory` — factory recovery companion to the Linux factory
  test; useful but not required for the first login attempt.
- `board_boot_test` — DR1M90G-family power-on test; exact CZ02 applicability is
  unknown from metadata.
- `linux_vm_deployment` — host virtual-machine setup candidate; not a board
  runtime document.
- `dr1_family_overview_ds1201` — DR1 family overview candidate for identity
  cross-checking.
- `dr1_user_guide_fd` — DR1 user-guide candidate for identity cross-checking.
- `dr1_datasheet_ds1200` — DR1 datasheet candidate for identity cross-checking.
- `dr1_outline_txt` — small source-bundle navigation outline; body was not read.

## Completely duplicated files

No exact duplicate was found among the recommended P0 records. In the broader
metadata-only candidate scan, two same-SHA256 groups were observed in explicitly
excluded component datasheets:

1. `duplicate_status: exact_duplicate`, SHA256 `b806e4a9a488507525fbc3174b2ad9273a08efcd24d151c45a3ccb3db540e19f`:
   `02_hardware/.../06_芯片手册/07_DF40/C424647_板对板与背板连接器_DF40C-60DP-0.4V(51)_规格书_WJ301237.PDF`
   and
   `02_hardware/.../06_芯片手册/07_DF40/C424649_板对板与背板连接器_DF40HC(3.0)-100DS-0.4V(51)_规格书_WJ301237.PDF`.
2. `duplicate_status: exact_duplicate`, SHA256 `5afe4a250892b415781ccc446021e44f5383eb3052adb77d6be23bfb4afb3d27`:
   `02_hardware/.../06_芯片手册/12_other/RCLAMP0522P.pdf`
   and `02_hardware/.../06_芯片手册/12_other/RCLAMP0524P.pdf`.

These files are not P0 records and no deduplication or deletion was performed.

## Possible version or reformat files

The following pairs have similar names or roles but different SHA256 values;
they are marked `possible_version_or_reformat` in the manifest and are not
automatically treated as duplicates:

- `FPSoC应用开发说明_alpha1.2.pdf` — `91bed874...6986b` versus
  `FPSoC应用开发说明_alpha1.2--米联客.pdf` — `cf04ecee...91b7f`.
- `UG1214_安路科技DR1系列FPSoC产品说明书.pdf` in the DR1 folder —
  `1d28043b...8fe6` versus the top-level hardware copy —
  `58d8e200...6e23`.
- `3_2_01_米联客2024版FPSoc_SDK入门篇.pdf` — `a815be57...e57fa` versus
  `3_2_02_米联客2025版FPSoc_SDK高级篇.pdf` — `72238e23...1791`.

The shortened hashes above are for navigation only; full hashes are in
`.knowledge/manifests/p0_documents.yaml`.

## Currently missing or not established

The filename scan did not establish a dedicated DR1M90 Linux SSH/SCP/rsync
procedure, a precise cross-compiler/sysroot version, a board OS image identity,
or a target-side NPU runtime/API guide. The PuTTY, network demos, Buildroot,
Linux driver, SDK, APUG1205, and IPUG166 records are candidates, not proof that
these capabilities are available on the current board.

## Questions requiring human confirmation

1. Which physical board revision and core-board revision are in use?
2. Which of the two FPSoC application-development files is authoritative?
3. Which UG1214 copy and which SDK year/tag apply to the intended Linux image?
4. Is serial access sufficient, or should a specific Ethernet/wireless transfer
   path be approved for the next phase?
5. After reviewing the approval boundary, which deferred P1 records may be
   considered for a later copy batch?

## Explicitly excluded categories

Power-management IC, DDR/QSPI, connector, CAN, RS485, audio/FEP-card and other
component datasheets; ModelSim output; FPGA/Verilog fundamentals; generated
build/cache/run directories; bitstreams; large images; unrelated boards; and
non-DR1 chip-family material were excluded from P0 selection. The exact
duplicate component files listed above remain untouched.
