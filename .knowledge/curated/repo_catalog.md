# Anlogic DR1 repository catalog

This is a source-code inventory, not a build or runtime validation. The two
repositories were synchronized into the private workspace and inspected at the
recorded revisions. Wiki URLs are seeds only; their pages were not fetched.

## `dr1_demo_prjs`

- Branch/tag/commit: branch `2026.1`, no Git tag, commit `4fc802664e09d18f015035f2c8ecc4811a8bb6d1`.
- Function: Anlogic DR1 series example projects, including FD application/BSP
  projects, TD FPGA projects, peripheral/AXI examples and D20 NPU hardware
  examples.
- Applicable stage: possible source reference for later ARM/NPU integration;
  not validated against the current board or SDK.
- Entry README: `README.md`.
- Build files: many project-local `Makefile`/`.mk` files, for example
  `C3_HelloWorld/FD_C3_AD101V20/app/Makefile` and
  `C21_VDMA/C21.1_VDMA_HDMI/FD_C21.1_AD101V20/app/Makefile`.
- Key source directories: `C3_HelloWorld/`, `C4/`, `C10/`, `C11/`,
  `C13/`, `C14_AXI_UART/`, `C15_AXI_RAM/`, `C16_AXI_DNA/`, `C17_AXI_DMA/`,
  `C18_QSPI/`, `C19_AXILite2APB/`, `C20_AXI4_Full/`, `C21_VDMA/`,
  `C22_AXILite/`, `C25_PLL/`, `C27/`, `D20_NPU_Demo/`.
- Wiki URLs:
  - `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/WCuPymw`
    (root README overview)
  - `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/XKwEaVkZ`
    (`C4/wiki_links.md`)
- Current availability: synchronized and clean locally; no tag-to-SDK
  compatibility statement found in the repository README.
- Unresolved dependencies: exact SDK/toolchain revision, board applicability,
  and required Anlogic project tools remain unknown.

## `dr1m90_npu`

- Branch/tag/commit: branch `release`, tag `SDK_2026.01`, commit
  `199ef4d71f453bb9a000102ff39def09c4cf73f9`.
- Function: Linux SDK NPU applications: camera-to-HDMI face/pose/OBB demos and
  storage-input `npu_demo` applications.
- Applicable stage: future ARM/NPU work after the SDK, board image and runtime
  are independently frozen; no ARM build was run.
- Entry README: `README.md`; NPU application guide
  `npu_demo/readme.md`.
- Build files: `npu_demo/build.sh`, `face_detection/build.sh`, `obb/build.sh`,
  `pose/build.sh`, and CMake files under each `*/src/`.
- Key source/config directories: `npu_demo/demo_src/`,
  `npu_demo/demo_scripts/`, `npu_demo/demo_inputs/`, `npu_demo/libs/`,
  `face_detection/src/`, `obb/src/`, and `pose/src/`.
- Wiki URLs:
  - `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/GVKBLhkf`
    (root README SDK guidance)
  - `https://alwiki.anlogic.com/wiki/external/org/AzZaqNHH/#/page/SdAMW8ED/R7MPfrun`
    (camera/HDMI README VDMA framebuffer reference)
- Current availability: synchronized and clean locally; source contains Git LFS
  pointers for ONNX/images/archives, while the local git-lfs executable was not
  available and no large objects were downloaded.
- Unresolved dependencies: matching SDK tag and environment, AArch64 compiler,
  Arm NN libraries, AArch64 OpenCV archive, kernel/module tree, HPF/bitstream,
  and target-board runtime have not been validated.

## Do-not-run boundary for this inventory

No repository build, demo, model conversion, Wiki fetch, Gitee raw-file fetch,
SDK download, qmd embedding, or target-board operation belongs to this
read-only inventory.
