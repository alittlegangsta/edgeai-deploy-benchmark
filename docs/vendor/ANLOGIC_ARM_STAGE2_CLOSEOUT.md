# Anlogic DR1 ARM CPU single-image baseline closeout

## Outcome

Tasks 013 and 014 establish a reproducible, correctness-first ARM CPU baseline
for the MLK-F3P-CZ02-DR1M90. Task 013 freezes the AArch64 toolchain and ncnn
runtime, then proves a hash-identical model-free smoke ELF on the real board.
Task 014 cross-builds the existing C++ ncnn image application, runs the frozen
YOLOv5n model on the board, compares the result with the PC C++ ncnn golden,
and records user visual approval.

Task 015 reconciles those existing artifacts. It does not rerun a build,
inference, or benchmark and does not introduce another deployment
implementation.

## Environment roles

| Environment | Responsibility | Needed for this offline closeout | Needed for clean reproduction |
| --- | --- | --- | --- |
| WSL | Git, source snapshot creation, frozen hash checks, evidence storage, PC/ARM comparison | Yes | Yes |
| Anlogic Ubuntu VM | User-local CMake and AArch64 cross-build | No | Yes, for rebuild |
| DR1 board | Dependency closure, runtime smoke, single-image execution, output capture | No | Yes, for runtime reproduction |

The tracked evidence is sufficient for closeout, so Task 015 does not access
the VM or board.

## Frozen toolchain and ncnn

| Component | Identity |
| --- | --- |
| Build host | Ubuntu 18.04.4 x86_64 |
| CMake | 3.16.9 |
| CMake source SHA256 | `1708361827a5a0de37d55f5c9698004c035abb1de6120a376d5d59a81630191f` |
| CMake executable SHA256 | `fa6d96ed54cbb20be01e16a275e6f86e97ed76953c113c8fffa2de18123f42b5` |
| Compiler | Linaro GCC/G++ 7.5.0 |
| Target | `aarch64-linux-gnu` |
| Sysroot | glibc 2.25 under the validated Linaro toolchain |
| Dynamic loader | `/lib/ld-linux-aarch64.so.1` |
| CMake toolchain | `configs/toolchains/anlogic-dr1-aarch64.cmake` |
| Toolchain-file SHA256 | `8ba63b21a1fa6bb2d3ddb391c686e460ea08d39a521592540997e76edb5359b0` |
| ncnn remote | `https://github.com/Tencent/ncnn.git` |
| ncnn tag/commit | `20240410` / `56775de50990ab7f16627efdcf5529b49541206f` |
| Clean ncnn archive SHA256 | `81239dfeb25316afd526ccf3d7da20ee85b66d8ff613d3af61d4ae36dfdc5e45` |
| `libncnn.a` SHA256 | `5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a` |
| Model-free smoke ELF SHA256 | `cad23a736f86b0d1ae6f9cfd938dce55732a3fc983a5baaa5a31fde0e393b8f7` |

The static build uses Release, CPU runtime, no shared ncnn library, no Vulkan,
Python, tools, examples, benchmark, tests, OpenMP, INT8, or ARMv8.2 path.
`NCNN_BF16=ON` compiles conversion code required by this fixed revision with
VFPV4; Task 013 and Task 014 explicitly disable BF16/FP16/INT8 runtime use.

The full option list and the repair record are in
[the Task 013 build document](ANLOGIC_AARCH64_NCNN_BUILD.md).

## Frozen model and correctness contract

| Artifact | SHA256 |
| --- | --- |
| ncnn model manifest | `9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff` |
| ncnn param | `72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4` |
| ncnn bin | `658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0` |
| inference configuration | `82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d` |
| fixed input | `625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071` |
| PC ncnn golden JSON | `fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9` |
| PC ncnn golden PNG | `57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2` |

The contract is CPU-only FP32, batch 1, `640x640`, one thread, input `in0`,
output `out0`, confidence `0.25`, class-aware NMS IoU `0.45`, and COCO-80.
Model conversion remains a PC-host operation and did not run on the board.

## Target and accepted result

The target is the MLK-F3P-CZ02-DR1M90: AArch64, two cores with CPU part
`0xd04`, Buildroot 2022.02.6, Linux 6.1.111-rt42, glibc 2.25, and OpenCV 4.7.0
`core`/`imgproc`/`imgcodecs`.

| Check | Result |
| --- | --- |
| Board application exit code | `0` |
| Detection count | `5` |
| Classes | `keyboard`, `tv`, `cup`, `mouse`, `mouse` |
| Finite values / valid boxes / classes | `PASS` |
| Minimum class-matched IoU | `0.999985507578` |
| Maximum confidence delta | `0.00000500679016113` |
| Automated gate | `PASS_TARGET` |
| ARM PNG versus PC ncnn golden | byte-identical |
| Human visual check | `PASS` by the user |

The low-confidence earbud-case `mouse` false positive is retained. The Task 014
single-run timing fields are diagnostic only and are not benchmark evidence.

See [the Task 014 validation document](ANLOGIC_ARM_YOLOV5N_SINGLE_IMAGE.md) and
[the machine-readable closeout manifest](../../.knowledge/manifests/anlogic_arm_stage2_closeout.yaml).

## Reproduction flow

The repository deliberately keeps build and real-board deployment separate.
The following commands are the existing audited entry points; run only the
stage for which its environment and authorization are available.

### 1. Check and build the ncnn AArch64 install tree

Requires WSL and the Anlogic VM:

```bash
bash scripts/vendor/build_anlogic_aarch64_ncnn.sh --check
bash scripts/vendor/build_anlogic_aarch64_ncnn.sh --execute
bash scripts/vendor/validate_anlogic_aarch64_ncnn.sh
```

The build script generates a clean archive from the fixed Git commit, transfers
only hash-checked inputs, configures the frozen CPU-only options, installs to
the VM workspace, and builds the model-free smoke ELF.

### 2. Build the ARM single-image application

Requires WSL and the Anlogic VM:

```bash
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh --check
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh --execute
```

This builds `edgeai_ncnn_image` from the shared PC/ARM C++ modules and exports
only the executable plus the required AArch64 OpenCV `core`, `imgproc`, and
`imgcodecs` libraries. It does not run inference.

### 3. Prepare, deploy, run, and collect

Requires WSL and the real board. `--check` performs a board preflight, so it is
not an offline dry-run:

```bash
bash scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh --check
bash scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh --execute
```

The script verifies frozen input and build-output hashes, creates an isolated
package, checks hashes on the board, applies executable permissions without
changing content hashes, verifies `ldd`, runs one CPU/FP32 image, and returns
the JSON, PNG, stdout, stderr, exit code, environment, and dependency records.
It does not install libraries into the board system.

### 4. Compare returned detections

Requires WSL only. Write reproduction output outside approved evidence:

```bash
PYTHONPATH=python .venv/bin/python tests/python/compare_detections.py \
  --reference results/acceptance/cpp_ncnn_reference.json \
  --candidate results/evidence/014/anlogic_arm_ncnn_detections.json \
  --profile ncnn-preregistered \
  --min-iou 0.99 \
  --max-confidence-delta 0.01 \
  --output /tmp/anlogic_arm_ncnn_comparison.json
```

The approved comparison remains
`results/evidence/014/anlogic_arm_ncnn_comparison.json`; a reproduction must not
overwrite completed-task evidence.

## Artifact and evidence policy

Git tracks contracts, scripts, task records, small JSON/YAML evidence, and the
approved annotated image. It does not track the CMake source/binary, ncnn
archive/source/install tree, SDK, VM build tree, `libncnn.a`, ARM ELF,
deployment package, model `.param`/`.bin`, credentials, or raw runtime logs.
Ignored model files may be deployed only after matching their frozen hashes.

## Scope boundary and next task

Stage 2 closes the reproducible ARM CPU single-image correctness baseline. It
does not establish ARM performance, video or camera support, Vulkan, FP16/BF16
or INT8 inference, or NPU deployment. The local SDK identity is
`SDK_2025_07`, but exact equivalence to an official repository tag remains
unproven. NPU stays `HOLD`.

The next unused task number is 017. A future `Anlogic DR1 ARM CPU benchmark`
task should preserve the same model, CPU FP32, and one-thread baseline and
preregister warmup, formal repetitions, independent process rounds, timing
boundaries, P50/P90/FPS, Peak RSS, governor, frequency, temperature, and raw
samples. No benchmark command or result belongs to Task 015.
