# EdgeAI Deploy Benchmark

EdgeAI Deploy Benchmark is a reproducible PC deployment and measurement baseline
plus an Anlogic DR1 ARM CPU single-image deployment baseline for a fixed
YOLOv5n v7.0 detector. The PC implementation contains Python ONNX Runtime, C++
ONNX Runtime, and C++ ncnn image/video paths with shared correctness and
benchmark contracts. The ARM implementation reuses the approved C++ ncnn
single-image pipeline and correctness contract.

## Current status

Tasks 001–036 are completed. Task 021 ARM UVC camera inference passed its
automated stage and received user representative-frame approval. Task 020 ARM video-file inference passed
automated real-board validation and user playback review.
Checkpoint C is
human-approved, PC Stage 1 is complete, and the Anlogic DR1 Stage 2 CPU
single-image and unoptimized benchmark baselines are complete.
Stage 2 covers the validated AArch64 toolchain, a CPU-only static ncnn build,
real-board ncnn runtime smoke, frozen YOLOv5n single-image inference, PC/ARM
correctness, user-approved visual output, and the formal CPU/FP32 one-thread
benchmark. It does not include video, camera, Vulkan, quantization, optimization,
or NPU deployment. Task 020 is a functional video validation, not a formal
video performance benchmark.

Task 017 froze the separate formal DR1 ARM CPU benchmark protocol and offline
collector/validator. It defines five independent processes, 10 warmups and 20
measured iterations per process, exact stage boundaries, nearest-rank
statistics, Peak RSS, frequency/temperature observation, and before/after
correctness. The complete 100-sample real-board session passed automated
validation and user review and is published as the default unoptimized baseline.
See [the ARM benchmark protocol](docs/vendor/ANLOGIC_ARM_CPU_BENCHMARK.md).

Task 018 completed a contemporaneous paired one-thread/two-thread experiment
with one OpenMP-enabled ncnn build. The user-approved `BENEFICIAL` result
records `1.845334x` pipeline speedup and `84.53%` FPS gain while preserving
correctness. The earlier OpenMP-off session remains parameter-sensitivity
evidence and is invalid for multithread performance comparison. See
[the threading experiment protocol](docs/vendor/ANLOGIC_ARM_CPU_THREADING_EXPERIMENT.md).

Task 019 turns the approved result into explicit deployment policy without
changing PC defaults: `baseline-single-thread` preserves Task 017, while
`recommended-dual-thread` binds the Task 018 OpenMP build, two threads, and its
private libgomp. DR1 deployments should select the recommended profile
explicitly. See
[the ARM runtime profile guide](docs/vendor/ANLOGIC_ARM_RUNTIME_PROFILES.md).

Task 020 reuses that recommended dual-thread profile for a 30-frame lossless
fixed-image video on the real board. All frames pass the PC ncnn golden gate,
and the returned MJPEG/AVI decodes 30/30 frames in WSL. See
[the ARM video-file guide](docs/vendor/ANLOGIC_ARM_VIDEO_FILE_INFERENCE.md).
The user approved full playback, frame continuity, and annotations; Task 020 is
`Completed`. This remains functional validation, not a formal video benchmark.

Task 021 uses the real DR1M90 UVC camera at the audited `/dev/video0` V4L2
`YUYV 640x480@5` configuration and a capacity-one latest-frame slot. Ten live
frames were retained and independently replayed through the approved single-
image path with `PASS_TARGET` equivalence. See
[the ARM UVC camera guide](docs/vendor/ANLOGIC_ARM_UVC_CAMERA_INFERENCE.md) and
the six user-approved representative files under `results/images/021/`. This
is functional bounded-latency validation, not a realtime benchmark; YUYV 5 FPS
is the camera capture setting, not an inference FPS result.

Task 022's prior local/VM/board audit and seven-page official AlWiki review are
user-approved. The task is complete as an audit, while NPU deployment remains
blocked; the primary result remains
`BLOCKED_DRIVER_OR_DEVICE`: the
board's hard-NPU device-tree node and CMA reservation are visible, but no
matching NPU/CMA modules are loaded, no `/dev/hard_npu`, `/dev/soft_npu`, or
`/dev/cma_mem` nodes exist, and the searched VM/SDK scope lacks a versioned
standalone `npu_runtime`, host converter executables, and official `rt.bin` /
`weight.bin` artifacts. The AArch64 Arm NN/Alnpu libraries in the SDK are
candidate assets, not proof of a deployable board runtime. No vendor one-shot
was run and the frozen project YOLOv5n model has not been converted for NPU.
This is a current asset/device readiness block, not a claim that DR1M90
permanently lacks NPU support; a version-matched vendor package must be
received and reviewed before any deployment change.
See [the NPU feasibility audit](docs/vendor/ANLOGIC_NPU_RUNTIME_FEASIBILITY.md)
and its structured evidence under `results/evidence/022/`.

The selected public AlWiki API pages (seven pages, `7/7` HTTP 200) add an
official D20.1 DR1M90 Buildroot/HPF/module-selection flow and D20.0 NPU API
documentation. They do not expose a verified current-board driver/runtime,
bitstream, one-shot, `rt.bin`/`weight.bin`, or host converter package. The
examples mention AD101V20 or DR1M90GEG484-2 in places, so exact
MLK-F3P-CZ02-DR1M90/Linux 6.1.111-rt42 applicability is still unknown. No
attachment was downloaded; the supplemental Wiki review is complete, and
project YOLOv5n conversion is still not ready.

Task 023 is the completed, user-approved read-only Anlogic NPU package-intake
audit. The user-provided
`NPU_info` collection and approved AlWiki/Gitee sources now have a provenance
and dependency map. The native `npu_runtime` path remains asset-blocked, while
the Arm NN/ONNX demo path has been configured and linked in an isolated VM
workspace; neither path is deployment-ready because the mixed
DR1M90GEG400/AD101V20/AD103V20/GEG484 materials do not map to the active
MLK-F3P-CZ02-DR1M90 FPGA/Device Tree. The primary status is
`BLOCKED_BOARD_HARDWARE_MAPPING`; secondary build, symbol-CRC, runtime,
release-identity and asset blockers remain. No driver, bitstream, vendor ELF,
or project model was executed or added to this repository. See
`docs/vendor/ANLOGIC_NPU_PACKAGE_AND_BUILD_CHAIN.md` and
`results/evidence/023/` for the static intake.
The audit is complete; deployment remains blocked, the vendor one-shot was not
executed, controlled board deployment was not approved, and project YOLOv5n
conversion is not ready.

Task 024 is the completed read-only MLK-F3P-CZ02 board-mapping audit. A current
Buildroot 2022.02.6/Linux 6.1.111-rt42 read confirmed the boot partition,
BOOT.bin, boot.scr, system.dtb and uImage.lz4 hashes, and parsed the active
hard-NPU/CMA Device Tree semantics. The BOOT.bin FPGA payload/source remains
opaque, and the supplied DR1M90GEG400 NPU project is a candidate rather than
the active FPGA/Device Tree. Kernel symbol provenance and rollback readiness
remain open; current eMMC NPU readiness is Not ready and controlled deployment
is not approved. No module, bitstream, DTB, kernel, media, or vendor program was touched. See
`docs/vendor/ANLOGIC_NPU_BOARD_MAPPING_AND_CONTROLLED_DEPLOYMENT.md` and
`results/evidence/024/`.

Task 025 is the completed SD-image preflight. The Milianke project is a strong
`DR1M90GEG400` board-level lead and its candidate HPF/bitstream/DT/boot hashes
are retained outside Git. The exact `SDK_2025.07-linux6.1` superproject clone
is reproducible, but local relative submodules cannot be materialized; the
fuller vendor release tarball has no `.git` provenance and the official SDK has
no MLK-F3P-CZ02 BoardConfig. Arm NN application targets link as AArch64
binaries in isolation, and their recursive non-system `DT_NEEDED` closure is
static-pass; the packaging step's `libprotoc.so*` names are not runtime
dependencies for the inspected closure, while absolute OpenCV RPATH
relocation remains unverified. The PDF-guided injection flow was then exercised
in a fresh isolated VM copy: the same workspace generated `BOOT.bin`,
`system.dtb`, kernel and the three NPU modules, and compiled the Arm NN demo.
The Buildroot 2022.02.6 dependency cache is now frozen and hash-checked, and a
formal rootfs was built offline in the isolated VM workspace. Static inspection
found only AArch64 ELF files and no missing DT_NEEDED names. A complete
external candidate file set (but no partitioned SD image) is recorded as
`READY_FOR_SD_WRITE_APPROVAL`; `candidate_approved: true` admits the static
13-file set to a controlled deployment workflow only. It does not authorize
formatting, partitioning or writing real media; `deployment_approval` remains
`PENDING`. No SD/eMMC write, module load, FPGA write, vendor NPU execution or
project-model conversion was performed. See
[the Task 025 preflight](docs/vendor/ANLOGIC_NPU_SD_IMAGE_PREFLIGHT.md) and
`results/evidence/025/`.

The bounded `03_demo` follow-up audit selected `05-5_NPU演示` as the direct
Milianke NPU lead. It confirms an Arm NN/ONNX package and candidate
DR1M90GEG400 HPF/bitstream/boot assets, but also records mixed AD101/GEG484
metadata, a missing base DTS, differing platform and best-result bitstream
hashes, and no MLK BoardConfig or native `npu_runtime` assets. The candidate
source identity remains mixed, but the documented injection workflow and
formal Buildroot rootfs are separately evidenced. Source provenance, board
boot and runtime execution remain unverified; the screening, deep-audit, PDF
workflow and formal rootfs evidence is in `results/evidence/025/`.

The subsequent bounded archive audit listed the 05-5 package and hash-recorded
the two large FPSoc RAR SDK archives; no local RAR reader was available, so no
RAR extraction was attempted. Direct 3-2/3-4 inspection confirms only generic
GEG400/FSBL/Linux context, while the 05-5 HPF/platform bit and best-result bit
are different and its BOOT payload has no packaged BIF/bootgen source. This
keeps candidate BoardConfig recovery at `ASSET_IDENTITY_CONFLICT`; the
formal candidate file set is now ready for a separate SD-write approval, but
no partitioned image or board boot is claimed.

The exact expected ARM Milianke package `uisrc-lab-anlogicM-V4.0.1.tar.gz`
was then identified by MD5 and statically inspected. It is a generic DR1M
SDK_2025.1 source/toolchain snapshot with image scripts and NPU driver source,
not an MLK-F3P-CZ02 BoardConfig or complete Arm NN/NPU runtime package. The
expected `anlogic-linuxsdk` download was not found locally; this increment is
classified `RECOVERABLE_STRUCTURE_VERSION_MISMATCH`; that package-only
increment did not itself provide the rootfs inputs needed by the later
PDF-guided candidate build.

Task 028 keeps the ArmNN/Alnpu result as Track A: the AArch64 runner forces
`Alnpu`/`ALHardNPU` and rejects CPU fallback, but the frozen FP32 graph is
rejected at `/model.11/Floor`. The completed C3c binary audit now scopes Track
A to `CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE` for the
matched backend. Track B retains the independent APUG1205
native result `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`: its documented
`convert_tool` -> `.tmfile` -> `al_ai_flow` -> `rt.bin`/`weight.bin` and
`libnpu_runtime.a` assets remain unavailable. Track C is now the active
official `AL_onnx_pass` path. Its host dependencies are closed in a separate
vendor-requirements venv and the unmodified frozen-model entry emits the
documented Detect-cropped FP32 and uint8 QDQ graphs. The uint8 host golden gate
fails (minimum IoU `0.8421554845490358`, maximum confidence delta
`0.09312496031303408`), so the host accuracy status is `NOT_ACCEPTED`. No quantized Alnpu correctness or FPS
benchmark is published. A deterministic 500-image host calibration smoke also
fails the golden gate (minimum IoU `0.8891731303877853`, confidence delta
`0.11366653714614872`). The 05-5 platform bitstream
does statically carry `NPU_SOFT=1` and `SOFT_YOLO=1`, which is hardware-side
evidence only. Track C is split into C1 official conversion `PASS`, C2
quantized host accuracy `NOT_ACCEPTED`, C3 board compatibility
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`, and C4 benchmark `NOT_RUN`. The
best opset14 uint8 candidate was run once from board `/tmp` with Alnpu-only and
CPU fallback disabled; ArmNN rejected QAsymmU8 Conv2d, Activation and
ElementwiseBinary during Optimize, before LoadNetwork. The corresponding
opset14 INT8 candidate rejected QSymmS8 Conv2d, Activation and
ElementwiseBinary, while the release YOLOv8n control rejected QAsymmU8
Splitter. See [the ArmNN/Alnpu
bring-up record](docs/vendor/ANLOGIC_YOLOV5N_ARMNN_ALNPU.md) and
`results/evidence/028/`.

Track C2 preserves the frozen opset12 FP32 baseline and adds same-weight
static-640 opset13/14 exports. All four pass ONNX/ORT raw checks and the
unchanged official conversion produces checker/ORT-valid uint8 and int8 graphs,
resolving the opset12 int8 `DequantizeLinear(axis=...)` dialect error. An
independent eight-image held-out teacher-relative gate still fails both
quantized types (class-multiset agreement is 87.5% for both); no local ground
truth exists, so true precision/recall/mAP is not claimed. Host preprocessing
is exactly equal to the project baseline on the frozen 1280x960 input, while
vendor calibration uses `scaleup=False`; the requested YOLOv5s positive-control
assets were not found and the release picture demo uses a separate
`yolov8n.quant.onnx` graph. The existing `43` in the test summary is a test
count, not a 43-image golden set.

The current C3 focus is runtime/toolchain compatibility. The release
`armnn_lib.tar.xz` (version marker `ed5ae24`) and six compared ArmNN/Parser/
protobuf/timeline libraries are byte-identical to the board's loaded runtime.
An `LD_LIBRARY_PATH`/`LD_DEBUG=libs` temporary `/tmp` run proved those
candidate files were loaded: the face positive control completed with
Alnpu-only, while the matched-runtime vendor `yolov8n.quant.onnx` control still
failed Alnpu `Optimize` on `QAsymmU8 Splitter`. Because the available NEW
runtime is the same identity as the OLD runtime, runtime-version skew is not
proven; this does not close the YOLOv5n compatibility gate. See
`results/evidence/028/trackc3_runtime_compatibility_matrix.json`. C4 remains
`NOT_RUN` and no benchmark or CPU fallback is claimed.
The audited release HEAD is untagged and three commits after its nearest
`SDK_2026.01` ancestor; the Task 026 tutorial `system.bit`/`system.dtb` and
static `NPU_SOFT=1`, `SOFT_YOLO=1` context are recorded separately, so neither
an SDK tag nor a bitstream mismatch is being inferred from the model failure.
The focused D20.1 comparison shows that its AD101V20/DR1M90GEG484 HPF uses a
different package, SoftNPU address/IRQ, VDMA topology and `SOFT_RESIZE` setting
than the 05-5 DR1M90GEG400 platform; it is not a valid substitute. Evidence:
`results/evidence/028/trackc3_hpf_d20_comparison.json`.

The C3 support-boundary audit statically inspected the matched AArch64
`libarmnn.so.32.1`: Alnpu-specific overrides cover a finite whitelist, while
Conv2d, Activation, Splitter, Addition and Multiplication vtable slots resolve
to generic `LayerSupportBase` rejection methods. This matches the retained real
graph results: vendor YOLOv8n fails first on `QAsymmU8 Splitter`, and YOLOv5n
UINT8/INT8 fail on quantized Conv2d/Activation/ElementwiseBinary. The face
positive control has no Split and remains a separate Alnpu/ALHardNPU positive.
The board wrapper was unavailable in this audit turn (`UtilBindVsockAnyPort:
307: socket failed 1`); no new board workload was claimed. See
`results/evidence/028/trackc3_support_boundary_audit.json`.

The completed C3c audit records the full ten-method AlnpuLayerSupport override
set and scopes the result to this exact compiled backend:
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`. The face PASS is
explained by the measured three `Alnpu|ALHardNPU` fused/custom workload
assignments, not by generic Conv2d support. All available ArmNN library copies
were byte-identical; no alternate backend implementing the generic YOLO slots
was found. The wrapper failure is environment-only. See
`results/evidence/028/trackc3_capability_face_path_audit.json`.

Task 028 is now `Completed` with primary verdict
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. The blocker
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE` is scoped to the
audited AArch64 ArmNN binary only. Track A remains raw-ONNX
`BLOCKED_UNSUPPORTED_ALNPU_GRAPH`; Track B remains
`BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`; C1 is `PASS`; C2 is
`NOT_ACCEPTED_PAUSED`; C3 stops at Alnpu LayerSupport before LoadNetwork; and
C4 is `NOT_RUN`. Reopening requires a supported generic-YOLO Alnpu backend,
APUG1205 compiler/native runtime, or an official DR1M90 GEG400 YOLO deployment
chain. No CPU fallback or NPU benchmark is claimed.

## PC architecture and model lineage

```text
YOLOv5n v7.0 weights
├── frozen ONNX ──> Python ORT / C++ ORT
└── frozen TorchScript ──> pnnx 20240410 ──> ncnn param/bin ──> C++ ncnn
```

The two ONNX Runtime implementations use the same frozen ONNX model. The ncnn implementation uses a separately frozen TorchScript-to-pnnx model generated from the same YOLOv5n v7.0 weights and validated for semantic equivalence.

YOLOv5n was selected as a small, established detector suitable for learning and
comparing deployment pipelines. The source weights SHA256 is
`4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3`;
the frozen ONNX SHA256 is
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`.
The input contract is batch 1, FP32, NCHW `[1,3,640,640]`.

## Environment and dependencies

- WSL2 Linux x86_64; CPU affinity scheduler managed; pinning disabled.
- Python 3.12.3, ONNX Runtime 1.18.1 CPUExecutionProvider, OpenCV 4.10.0.
- GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1, system OpenCV 4.6.0.
- C++ ONNX Runtime SDK 1.18.1 and ncnn 1.0.20240410.
- ORT intra/inter-op threads 1, ncnn threads 1, OpenCV threads 1.
- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
  `NUMEXPR_NUM_THREADS` are all 1.
- ARM cross-build: Ubuntu 18.04.4 VM, user-local CMake 3.16.9, Linaro
  GCC/G++ 7.5.0, target `aarch64-linux-gnu`, and glibc 2.25 sysroot.
- ARM target: MLK-F3P-CZ02-DR1M90, AArch64 dual core, Buildroot 2022.02.6,
  kernel 6.1.111-rt42, glibc 2.25, and OpenCV 4.7.0.
- Task 018 ARM threading instrument: ncnn `20240410` with
  `NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, plus a private
  `libgomp.so.1` loaded only from the isolated deployment directory.

The Python/C++ OpenCV version difference limits single-cause attribution of
preprocess performance even though tensor and detection correctness pass.

## Anlogic DR1 ARM CPU baseline

The real board ran the frozen ncnn `20240410` CPU/FP32 pipeline with one thread,
the same approved `.param`/`.bin`, fixed image, configuration, preprocessing,
postprocessing, and PC C++ ncnn golden. It exited zero with five matching
detections. The minimum class-matched IoU is `0.999985507578`, the maximum
confidence delta is `0.00000500679016113`, the annotated PNG is byte-identical
to the PC ncnn golden, and the user visual review is `PASS`.

The user-approved Task 017 benchmark uses five independent processes, 10
warmups and 20 measured iterations per process. The aggregate pipeline mean is
`3513.992354 ms` (about `3.514` seconds per image), and sequential batch-1 FPS
is `0.284576601` (about `0.285`). Mean inference time is `3418.092005 ms`, so
inference dominates the pipeline. Maximum process Peak RSS is `142476 KiB`.
These values describe the default CPU-only FP32, batch-1, `640x640`, one-thread
configuration, not multi-thread, NEON-specific, quantized, Vulkan, or NPU
performance.

The user-approved Task 018 paired experiment uses a separate OpenMP-enabled
build for both conditions and changes only `configured_threads`. Mean pipeline
latency is `3634.205540 ms` at one thread and `1969.402190 ms` at two threads,
corresponding to `1.845334x` speedup and an FPS increase from `0.275163303` to
`0.507768299`. Correctness is unchanged (`IoU=1.0`, confidence delta `0.0`
between thread conditions), and both stability gates pass. This is beneficial
but not ideal `2x` scaling; serial pipeline work and scheduling overhead remain.
Task 017 is a different-build historical reference and was not modified.

For deployment, use `recommended-dual-thread`; use
`baseline-single-thread` only when reproducing Task 017. The recommendation is
specific to the verified DR1M90 CPU/FP32 single-image path and does not
silently alter the generic PC CLI.

Use [the Stage 2 closeout guide](docs/vendor/ANLOGIC_ARM_STAGE2_CLOSEOUT.md) for
the frozen identities, environment roles, phased build/deploy/run/collect/
compare commands, tracked evidence, and artifact policy. Task 015 reconciles
existing evidence only; no inference or benchmark was rerun during closeout.

## Repository structure

- `python/`: Python ORT applications and common processing.
- `cpp/`: C++ common modules and ORT/ncnn applications.
- `configs/`: frozen inference and benchmark contracts.
- `models/`: manifests; generated model binaries remain Git-ignored.
- `tasks/`: auditable task state and execution records.
- `results/`: committed small evidence and generated local outputs.
- `docs/`: model, benchmark, PC acceptance, and ARM deployment documentation.

## Model preparation

Model weights, ONNX, TorchScript, ncnn param/bin, SDKs, and large videos are
intentionally Git-ignored. Put the official v7.0 weights at
`models/yolov5n-v7.0/yolov5n.pt`, verify the Task 002 SHA256, and export ONNX
from a read-only YOLOv5 v7.0 checkout:

```bash
export YOLOV5_SOURCE=/path/to/yolov5-v7.0
.venv/bin/python "$YOLOV5_SOURCE/export.py" \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --imgsz 640 640 --batch-size 1 --device cpu \
  --include onnx --opset 12
```

Do not add `--simplify`, `--dynamic`, `--half`, or graph NMS. For ncnn, follow
Task 010's fixed CPU/FP32 chain using the same weights: TorchScript export, pnnx
from ncnn tag `20240410` revision
`56775de50990ab7f16627efdcf5529b49541206f`, `inputshape=[1,3,640,640]f32`,
`device=cpu`, `fp16=0`, and `optlevel=2`. The manifests and Task 010 validators
must reproduce the recorded SHA256 values before inference. Do not substitute a
different model, pnnx revision, input size, precision, or threshold.

## Build

```bash
export ONNXRUNTIME_ROOT=/path/to/onnxruntime-linux-x64-1.18.1
export NCNN_ROOT=/path/to/ncnn-linux-x64-20240410-local
cmake -S cpp -B build/pc-acceptance-release -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT="$ONNXRUNTIME_ROOT" \
  -DNCNN_ROOT="$NCNN_ROOT"
cmake --build build/pc-acceptance-release --parallel
ctest --test-dir build/pc-acceptance-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
```

## Single-image and video commands

```bash
mkdir -p build/reproduction
PYTHONPATH=python .venv/bin/python python/apps/ort_image.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/python_ort_reference.png \
  --output-json build/reproduction/python_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_image \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/cpp_ort_reference.png \
  --output-json build/reproduction/cpp_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_video \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output build/reproduction/cpp_ort_reference.mp4 \
  --output-json build/reproduction/cpp_ort_video.json

./build/pc-acceptance-release/edgeai_ncnn_image \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/cpp_ncnn_reference.png \
  --output-json build/reproduction/cpp_ncnn_reference.json

./build/pc-acceptance-release/edgeai_ncnn_video \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output build/reproduction/cpp_ncnn_reference.mp4 \
  --output-json build/reproduction/cpp_ncnn_video.json
```

These reproduction outputs stay under the Git-ignored build tree and do not
overwrite approved evidence. The known low-confidence second `mouse` on the
earbud case is retained as a model false positive; it is not hidden with
threshold or coordinate rules.

## Task 012 benchmark method

Six rounds execute all permutations of Python ORT, C++ ORT, and C++ ncnn. Every
backend appears twice in each position. Every invocation is an independent
process with 10 warmups and 100 formal iterations, yielding 600 samples per
backend. Every formal iteration performs preprocess, inference, and postprocess.

Pipeline total is the exact unrounded sum of those stages. It excludes image
read, model/runtime load, drawing, labels, writes, video decode, and encoding.
Pipeline FPS is `1000 / aggregate mean pipeline_total_ms`, not a mean of per-run
FPS and not video application throughput. P50/P90 use nearest-rank.

To reproduce the campaign without overwriting the approved Task 012 files, use
new paths under the Git-ignored build tree:

```bash
mkdir -p build/reproduction/benchmark
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
PYTHONPATH=python .venv/bin/python scripts/generate_pc_acceptance.py run-campaign \
  --config configs/benchmark_pc_three_backend.json \
  --base-config configs/benchmark_pc.json \
  --python .venv/bin/python \
  --python-benchmark python/apps/benchmark_ort.py \
  --cpp-ort build/pc-acceptance-release/edgeai_benchmark_ort \
  --cpp-ncnn build/pc-acceptance-release/edgeai_benchmark_ncnn \
  --ncnn-manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --reference-detections results/evidence/007/cpp_ort_detections.json \
  --python-output build/reproduction/benchmark/python_ort.json \
  --cpp-ort-output build/reproduction/benchmark/cpp_ort.json \
  --cpp-ncnn-output build/reproduction/benchmark/cpp_ncnn.json \
  --summary build/reproduction/benchmark/summary.json \
  --csv build/reproduction/benchmark/summary.csv \
  --validation build/reproduction/benchmark/validation.json \
  --log build/reproduction/benchmark/campaign.log
```

This command intentionally launches a new campaign; its outputs are not the
approved data below and must not replace files under `results/benchmarks/`.

### Final PC performance — campaign approved

| Backend | Pipeline mean (ms) | P50 | P90 | Min | Max | Pipeline FPS | Six-round spread | Position spread |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Python ORT | 54.881306 | 54.640382 | 56.898155 | 51.590660 | 65.453303 | 18.221141 | 3.098913% | 1.156671% |
| C++ ORT | 51.802986 | 51.595426 | 53.627128 | 48.863992 | 65.671301 | 19.303907 | 3.221212% | 1.383173% |
| C++ ncnn | 77.865349 | 77.618684 | 80.776143 | 73.478461 | 85.075339 | 12.842683 | 1.727134% | 0.438557% |

### Stage means

| Backend | Preprocess mean (ms) | Inference mean (ms) | Postprocess mean (ms) | Pipeline mean (ms) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 3.356562 | 45.898201 | 5.626543 | 54.881306 |
| C++ ORT | 1.833570 | 45.849137 | 4.120279 | 51.802986 |
| C++ ncnn | 1.815537 | 71.941530 | 4.108283 | 77.865349 |

Under this fixed WSL2 configuration, C++ ORT has the lowest complete-
pipeline mean at `51.802986 ms`, which is `5.61%`
lower than Python ORT. Python ORT and C++ ORT inference means are
`45.898201 ms` and
`45.849137 ms`, a difference of about
`0.11%`; the observed C++ pipeline advantage is
therefore concentrated in this implementation's preprocess and postprocess
overheads, not evidence that C++ or the ORT inference kernel is universally
faster.

C++ ncnn records `77.865349 ms`, `50.31%` above
C++ ORT for the complete pipeline. Its inference mean is
`71.941530 ms`, `56.91%`
above C++ ORT in this campaign. This is specific to the fixed x86 CPU, WSL2,
runtime versions, model-conversion path, build, and input; it predicts neither
another PC nor ARM behavior.

### Running-position effect

| Backend | Position 1 mean (ms) | Position 2 mean (ms) | Position 3 mean (ms) | Position spread |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 54.472042 | 55.102104 | 55.069772 | 1.156671% |
| C++ ORT | 52.163539 | 51.451871 | 51.793547 | 1.383173% |
| C++ ncnn | 77.956484 | 77.649513 | 77.990051 | 0.438557% |

Every position group contains 200 samples. All round spreads are below 3.3% and
all position spreads are below 1.4%; the execution position did not change the
backend ranking in this campaign. Position spread is diagnostic and no sample
was removed because of it.

### Model load, CPU, and Peak RSS

| Backend | Model load range (ms) | Process CPU range (%) | Peak RSS range (bytes) | Peak RSS range (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 27.340525–34.602837 | 99.942096–99.972122 | 178225152–181420032 | 170.0–173.0 |
| C++ ORT | 53.144442–54.676551 | 99.996220–100.000091 | 153935872–155078656 | 146.8–147.9 |
| C++ ncnn | 30.798871–32.886271 | 99.988997–99.998528 | 187768832–188178432 | 179.1–179.5 |

All 1,800 samples and outliers are preserved. The table applies only to this
fixed WSL2 environment, code, model lineage, input, thread configuration, and
campaign. It is not a universal language/runtime ranking and cannot be projected
to bare-metal Linux, another PC, or ARM.

## Correctness

Python/C++ ORT use the frozen golden tolerances. ncnn matches ORT at the
pre-registered target of class-matched IoU at least 0.99 and confidence delta at
most 0.01. Each formal process performs untimed checks before warmup and after
measurement. The approved final values are minimum IoU `0.999999982537` and
maximum confidence delta `1.64833068306e-08` for Python/C++ ORT, and minimum IoU
`0.999997080011` and maximum delta `2.02655792236e-06` for C++ ORT/ncnn. The
three annotated images are human-approved and byte-identical with SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.

## CPU and memory definitions

`process_cpu_percent_one_core_basis` is 100 times process CPU-time delta divided
by wall-time delta. About 100% represents sustained use of one logical CPU;
values above 100% can reflect auxiliary Runtime or system activity. A configured
thread count of 1 does not mean the process owns exactly one OS thread.

Peak RSS is the complete process peak, not model-only memory. Python includes the
interpreter/modules; C++ includes executable and linked-library costs; every
backend includes its Runtime, model, and input state.

## Evidence, limitations, and reproduction

- Benchmark summary: `results/benchmarks/pc_three_backend_summary.json` and CSV.
- Validation: `results/evidence/012/three_backend_benchmark_validation.json`.
- Approved annotated outputs: `results/acceptance/python_ort_reference.png`,
  `results/acceptance/cpp_ort_reference.png`, and
  `results/acceptance/cpp_ncnn_reference.png`.
- PC acceptance: `docs/pc_stage_acceptance.md` and
  `results/evidence/012/pc_acceptance.json`.
- Task 009/011 campaigns remain immutable historical evidence and are not used as
  substitute rows in the Task 012 main table.
- WSL2 scheduling, frequency/thermal state, background activity, unpinned CPU,
  distinct OpenCV versions, and distinct ONNX/ncnn serialized graphs limit causal
  attribution.
- Generated models, SDKs, logs, videos, and other large reproducible artifacts
  remain Git-ignored. Reproduction requires the exact recorded hashes and local
  tool versions.

Task 025's read-only VM history audit found a generic SDK_2025.07 tree and
generic `anlogic-dr1m90` base DTS files, but no MLK BoardConfig, exact
submodule provenance, historical 2025.07 uisrc package or original 05-5
workspace. The VM 05-5 tree is an exact copy of the local demo package, not an
independent build workspace. The later PDF-guided isolated build generated
boot/kernel/module artifacts, and the subsequent offline Buildroot build
generated the formal rootfs. The current candidate is a complete external file
set without a partitioned SD image and is `READY_FOR_SD_WRITE_APPROVAL`;
`candidate_approved: true` admits the static 13-file set to a controlled
deployment workflow only. It does not authorize formatting, partitioning or
writing real media; `deployment_approval` remains `PENDING`, and no board boot
or runtime result is claimed.

## Stage boundary and future work

PC Stage 1 and the DR1 ARM CPU single-image Stage 2 baseline are complete.
Task 017 has completed the preregistered single-thread CPU/FP32 benchmark and
published the validator- and user-approved unoptimized default baseline.
Task 018 completed the corrected OpenMP-enabled paired thread experiment without
changing that baseline. Its original OpenMP-off session remains intact and
invalid for multithread performance comparison. Camera validation is now an
independent completed functional Task 021 with user-approved representative
frames; no camera timing is a formal realtime benchmark. Affinity/NEON-specific optimization, Vulkan,
quantization, and NPU remain separate future work; NPU readiness remains
`HOLD`.

Task 024 is `Completed` as an audit with primary verdict
`BLOCKED_ACTIVE_BITSTREAM_IDENTITY`; active file hashes are read-confirmed but
the payload/source mapping is unresolved. `candidate_approved: true` approves
the audit record only, not SD writes, module loading or NPU execution. It is
not an NPU execution or performance result.

Task 029 is completed as the documentation-only vendor enablement handoff and is
`WAITING_FOR_VENDOR_INPUT`. The package at
`docs/vendor_handoff/dr1m90_npu/` freezes Task 028 identities, causal evidence
the scoped Alnpu capability boundary, and the Task 032 fusion addendum; vendor
binaries, models, SDKs, datasets and credentials remain external. The face ONNX
has no ALHardNPU custom node; the audited runtime forms three
`Alnpu|ALHardNPU` assignments during Optimize, but the complete fusion
predicate is not recoverable. This does not claim that YOLOv5n is inherently
incompatible.

Task 030 consolidates the approved PC C++ ORT and DR1M90 ARM ncnn YOLOv5n CPU
measurements under one correctness-first reporting contract. It independently
recomputes nearest-rank P50/P95, stage means, FPS, process CPU utilization,
Peak RSS, and frequency/temperature availability from retained raw evidence.
The PC row uses WSL2 C++ ORT; the ARM row uses the recommended dual-thread
OpenMP ncnn profile. They share the frozen model/input and preprocessing and
postprocessing contracts, but are different platforms and runtimes, so no
cross-platform speedup is claimed. The vendor face NPU is a functional control
only, and DR1 YOLOv5n NPU remains `NOT_BENCHMARKED`. See
[the consolidated benchmark report](docs/benchmark/ARM_CPU_BENCHMARK_PROFILING_CONSOLIDATION.md)
and `results/evidence/030/`.

Task 031 is the completed read-only recovery audit of the public `sdk`,
`dr1m90_npu` and `dr1_demo_prjs` histories. It found no recoverable
`npuv1_release`, APUG1205 native compiler/runtime, official YOLOv5s positive
model, materially broader Alnpu backend, or GEG400 `NPU_Yolo` HPF/TD. The face
ONNX contains no ALHardNPU custom node; ArmNN fuses its eligible path into
ALHardNPU workloads. The generic quantized YOLO boundary remains scoped to the
audited AArch64 build and the primary result is
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`; Task 029's vendor handoff remains the
next action. See `docs/vendor/ANLOGIC_OFFICIAL_NPU_ASSET_RECOVERY_GEG400.md`
and `results/evidence/031/`.

Task 032 is a bounded static audit of the audited AArch64 ArmNN fusion path.
It confirms the compiled `ConvertConv2dIntoALHardNPUImpl` symbols and the
finite Alnpu support dispatch, retains the face positive assignments, and
documents why the exact fusion predicate and per-node face mapping are not
recoverable from the stripped binary. The result is
`FUSION_PREDICATE_NOT_RECOVERABLE`; no model, board or benchmark was changed.
See `docs/vendor/ANLOGIC_ALHARDNPU_FUSION_ELIGIBILITY.md` and
`results/evidence/032/`.

Tasks 033–035 form the ARM optimization sequence: runtime tuning, kernel
profiling, then INT8 quantization. Task 033 completed correctness-first ARM CPU profiling on the validated ncnn
YOLOv5n path without reopening the frozen NPU vendor handoff. The accepted
two-core board configuration is ncnn 20240410 OpenMP with two threads, default
scheduling, packing on, and FP32 storage/arithmetic. It measured 1963.817618 ms
pipeline mean versus 3514.946744 ms for one thread (1.789854x pipeline speedup
and 78.985396% FPS gain); inference mean was 1873.474372 ms. All retained rows
passed the unchanged five-detection golden. Affinity, packing-off and FP16 A/B
rows were retained as slower evidence, while threads 3/4 were skipped because
the board exposes two logical CPUs. This is CPU profiling evidence, not an NPU
or camera benchmark; see `docs/benchmark/ARM_CPU_PERFORMANCE_OPTIMIZATION.md`
and `results/evidence/033/`.

Task 034 completed profiling the inference kernel distribution of that same ARM ncnn
pipeline. The isolated `NCNN_BENCHMARK` build reports 206 layers; Convolution
accounts for 80.304% of summed layer time, while Task 033 inference remains
95.399611% of pipeline time. The exact 20240410 Release/OpenMP build was
audited and a correctness-passing `-mtune=cortex-a35` A/B candidate was
rejected because it was 0.607296% slower in pipeline. The frozen conversion is
already optimized at its recorded pnnx `optlevel=2`; no INT8 or NPU claim is
introduced. See
`docs/benchmark/ARM_NCNN_INFERENCE_KERNEL_OPTIMIZATION.md` and
`results/evidence/034/`.

Task 035 (Completed) evaluates the fixed ncnn 20240410 INT8 path separately from the frozen
FP32 baseline. The repaired COCO evaluator uses 500 calibration images and all
4,500 remaining val2017 images, exact subset IDs, COCO80 category mapping and
`xyxy`→`xywh`, with AP confidence `0.001`/NMS `0.6` while deployment remains
`0.25`/`0.45`. Final FP32/EQ mAP50 is `0.457605/0.443309` and mAP50-95 is
`0.279777/0.265115`; absolute EQ degradation is `0.014296/0.014662`, within
the `0.02` gate, and neither has zero-detection images. The same AArch64
`NCNN_INT8=ON` ELF, threads=2/default scheduling/packing-on, measured EQ
`1.604359x` inference and `1.557952x` pipeline speedup (`55.795208%` FPS gain)
with a `1.938084x` diagnostic convolution aggregate speedup. The experiment
decision is `INT8_ACCEPTED`; the strict single-image FP32-reference failure is
retained as secondary evidence rather than relabeled. EQ is the accepted ARM
INT8 configuration, and no NPU work is reopened.
See
[the INT8 feasibility report](docs/benchmark/ARM_NCNN_INT8_QUANTIZATION_FEASIBILITY.md)
and `results/evidence/035/`.

Task 036 closes a project-owned DR1 vendor-face NPU image loop. The AArch64
`edgeai_armnn_face_image` runner uses the audited
`yolo_face_uint8_15.onnx` control, forces `Alnpu`, rejects CPU fallback, emits
JSON and an annotated PNG, and was observed assigning layers to
`Alnpu | ALHardNPU`. Its bounded two-warmup/ten-repeat diagnostic reports
50.3471437 ms inference mean and 65.9801407 ms end-to-end mean (functional
control only; not a YOLOv5n benchmark). The model/runtime/ELF identities,
board device state, logs, images and offline validator are in
[the DR1 NPU closed-loop guide](docs/vendor/ANLOGIC_DR1_NPU_DEMO_INTEGRATION.md)
and `results/evidence/036/`. Custom YOLOv5n NPU compatibility remains
`WAITING_FOR_VENDOR_INPUT`.

Task 037 establishes the PC TensorRT GPU baseline in the approved Ubuntu WSL2
environment. The RTX 4060 Ti (compute capability 8.9), CUDA 12.9.86 toolkit
and TensorRT 10.13.3 C++ stack pass the environment gate; no Linux NVIDIA
display driver was installed. The project-owned runner accepts a real FP32
engine built with `--noTF32` (1.674261 ms CUDA inference mean and 107.715355
FPS end-to-end on the fixed image protocol). The real FP16 engine passes the
frozen 4,500-image COCO accuracy gate (mAP50 0.448105440, mAP50-95
0.274786550 versus TensorRT FP32 0.448302671/0.274720465, zero detection
images 0) and is therefore `TENSORRT_FP16_READY`; its known single-image
Golden drift remains a secondary diagnostic. FP16 GPU inference is 1.221751x
faster, while the complete pipeline is 1.3307% slower because CPU
pre/postprocess dominates. Engines and raw output remain outside Git. See
`docs/benchmark/TENSORRT_DEPLOYMENT_BASELINE.md` and `results/evidence/037/`.
