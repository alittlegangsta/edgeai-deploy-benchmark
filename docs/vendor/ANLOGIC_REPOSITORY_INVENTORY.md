# Anlogic DR1 repository inventory

## Scope and synchronization

This inventory records a read-only synchronization of the two official Gitee
repositories into the private workspace configured by
`.knowledge/local_paths.yaml`. The repositories were obtained as full clones
and inspected without changing their source trees. Existing worktrees were
required to be clean; the permitted repository update operation was
`git fetch --prune --tags origin` only.

Observed local state was recorded on 2026-07-24:

| Repository | Branch | Commit | Remote HEAD | Tags | Worktree |
| --- | --- | --- | --- | --- | --- |
| `dr1_demo_prjs` | `2026.1` | `4fc802664e09d18f015035f2c8ecc4811a8bb6d1` | same commit | none | clean |
| `dr1m90_npu` | `release` | `199ef4d71f453bb9a000102ff39def09c4cf73f9` | same commit | `SDK_2026.01` | clean |

No repository was built or executed. No Wiki page, Gitee raw asset, SDK, model,
or large-file object was downloaded by this inventory. The full process log is
outside the repository at:

`/home/dministrator/vendor/anlogic-dr1-knowledge/logs/anlogic_repo_inventory.log`

## `dr1_demo_prjs`

The root README describes a collection of Anlogic DR1 series example projects
and points each project to a Wiki page. The observed top-level categories are:

- `C3_HelloWorld`, `C4`, `C10`, `C11`, `C13`;
- `C14_AXI_UART`, `C15_AXI_RAM`, `C16_AXI_DNA`, `C17_AXI_DMA`,
  `C18_QSPI`, `C19_AXILite2APB`, `C20_AXI4_Full`, `C22_AXILite`,
  `C25_PLL`, and `C27`;
- `C21_VDMA`, with FD/TD examples for HDMI and MIPI VDMA;
- `D20_NPU_Demo`, with TD projects for `AD101V20` and `AD103V20`.

The source layout uses `FD_*` application/BSP projects and `TD_*` FPGA project
directories. It does not provide a single repository-wide Linux build entry;
project-local Makefiles and Anlogic project metadata are the observed build
entry points. `C4` includes SD, Ethernet/LwIP and iperf examples. `C21_VDMA`
contains framebuffer/HDMI/MIPI source and board metadata. `D20_NPU_Demo`
contains NPU-related FPGA/TD assets such as `.hpf`, `.al`, HDL and generated
project metadata. These are source-code facts, not evidence of a successful
build on the current board.

The repository contains a GPL version 2 `LICENSE`. No Git tag was present;
branch `2026.1` is recorded as a branch only. The README does not state that
this branch is an SDK tag or establish compatibility with `SDK_2026.01`.

## `dr1m90_npu`

The root README groups examples into:

1. camera input plus NPU plus HDMI output (`face_detection`, `pose`, `obb`);
2. storage input from EMMC/SD with terminal or storage output (`npu_demo`).

The observed build entry points are `npu_demo/build.sh`,
`face_detection/build.sh`, `obb/build.sh`, and `pose/build.sh`, with CMake
projects below each `src` directory. The scripts reference an SDK-provided
`toolchains/aarch64-linux/bin/aarch64-linux-gnu-g++`/`gcc`, an Arm NN library
prefix, and an AArch64 OpenCV 4.7.0 archive. `npu_demo/readme.md` also documents
SDK Buildroot configuration for `hard_npu_driver`, `soft_npu_driver`,
`cma_mem_driver`, an extra rootfs directory, HPF selection, and a larger DR1M90
rootfs. Those instructions were read as source text only; no SDK build was
attempted.

`npu_demo/demo_scripts/` contains CRNN, distance, gesture, keyword spotting,
leaf, wind-turbine, YOLO image, YOLO pose, and YOLO segmentation launchers.
`npu_demo/scripts/README.md` describes host-side ONNX checking/optimization and
quantization, including YOLO post-processing parameters. It is not a license to
convert the project's frozen model in this inventory.

The `release` branch and `SDK_2026.01` tag are real local Git state. The root
README explicitly says the repository tag must match the SDK tag for correct
compilation. This is the only recorded compatibility rule; the SDK itself,
board image, compiler, Arm NN, OpenCV and kernel tree were not inspected.

The repository uses Git LFS attributes for `.onnx`, image and archive files.
The checked-out files are LFS pointer text (for example, ONNX files are 131–132
bytes), and the local `git-lfs` executable was unavailable. No LFS object was
downloaded. This is a material unresolved dependency for any later demo build.

## Wiki links observed locally

Only these four unique Wiki URLs were found in repository README or source
text; they are also recorded in `.knowledge/manifests/wiki_seed_urls.yaml`.

| URL | Source context |
| --- | --- |
| `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/WCuPymw` | `dr1_demo_prjs/README.md`, DR1 example overview |
| `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/XKwEaVkZ` | `dr1_demo_prjs/C4/wiki_links.md`, C4 project |
| `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/GVKBLhkf` | `dr1m90_npu/README.md`, SDK environment/cross compiler |
| `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/R7MPfrun` | camera/HDMI README files, labeled D21.1 Linux VDMA framebuffer |

No URL was opened or crawled. Gitee repository and raw HPF URLs were observed
in README files but are intentionally not Wiki seeds.

## Local P0 keyword checks

The existing `milianke-dr1-p0` qmd 1.0.9 collection was searched with BM25
keywords only. No embedding, vector search or reranking was used, and the
collection remains at `vectors: 0`.

| Query | Real result |
| --- | --- |
| `Linux SDK` | Hits in the Buildroot secondary-development guide and the Linux basics guide; no SDK version was stated by this search. |
| `SDK tag` | No results. |
| `SDK revision` | No results. |
| `DR1M90 NPU Runtime` | Hit in `UG1214_安路科技DR1系列FPSoC产品说明书.pdf` at extracted lines 4073–4076 describing the NPU Runtime. |
| `dr1m90_npu` | No results. |
| `NPU Demo` | No results. |
| `模型转换` | Hit in the same UG1214 document at extracted lines 4038–4041 describing host-side model conversion/optimization and NPU runtime use. |
| `工具链版本` | No results. |

These extracted line addresses are qmd addresses, not asserted PDF page
numbers. The hits do not establish an SDK tag, source revision or board
compatibility; those remain source/repository or real-device questions.

## SDK compatibility and unresolved version questions

- `dr1m90_npu` requires a repository tag matching the SDK tag. The repository
  tag observed locally is `SDK_2026.01`; no claim is made that a matching SDK is
  installed or suitable for the target board.
- `dr1_demo_prjs` has branch `2026.1` and no Git tags. Its relationship to
  `SDK_2026.01` is unknown and must not be inferred from similar digits.
- Board revision, exact DR1M90 device/board pairing, SDK path, cross compiler
  revision, sysroot, libc, Arm NN libraries, AArch64 OpenCV package, HPF
  provenance and Linux image remain unknown.
- Git LFS client/object availability is unresolved for `dr1m90_npu` model and
  archive assets.

## Relationship to this project

The repositories are reference sources for the ARM CPU baseline and any future
NPU phase. They do not establish the current board environment, and they do not
replace the PC-validated ncnn model manifest. No PC benchmark evidence or
approved model contract was modified.

## Explicitly deferred operations

Do not build either repository, run its demos, fetch Wiki pages or Gitee raw
assets, download an SDK or LFS objects, run qmd embedding, or claim a toolchain
or board compatibility until a separate task freezes the applicable board,
SDK, source revision and real-device evidence.
