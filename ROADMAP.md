# Roadmap

## Stage 1: PC deployment baseline

The PC work is organized as three auditable batches:

- Batch A, Tasks 002–005, is completed and Checkpoint A is approved. It freezes
  YOLOv5n v7.0 and provides the tested Python ONNX Runtime reference.
- Batch B, Tasks 006–009, is completed and Checkpoint B is approved. It provides
  shared C++ processing, C++ ONNX Runtime image/video inference, and the unified
  benchmark method.
- Batch C, Tasks 010–012, is completed and Checkpoint C is approved. It contains
  the fixed TorchScript/pnnx ncnn conversion, C++ ncnn image/video/benchmark path,
  order-balanced three-backend benchmark, and final PC acceptance.

`tasks/000_pc_stage_execution_protocol.md` defines selection, state transitions,
evidence, retry limits, blocking reports, recovery, commits, and human checkpoints.
PC Stage 1 is complete. The approved WSL2 measurements must not be generalized
to ARM or other systems.

## Stage 2: Anlogic DR1 ARM CPU baseline

This stage is `Completed` for the correctness-first CPU single-image baseline:

- Task 013 freezes the user-local CMake, Linaro AArch64 toolchain, glibc 2.25
  sysroot, ncnn `20240410` CPU-only static build, and real-board runtime smoke.
- Task 014 reuses the frozen YOLOv5n ncnn model and common C++ pipeline on the
  MLK-F3P-CZ02-DR1M90, reaches the PC/ARM `PASS_TARGET` gate, returns a
  byte-identical annotated PNG, and receives user visual approval.
- Task 015 reconciles provenance, hashes, evidence, and the existing
  build/deploy/run/compare entry points into the Stage 2 closeout.

The correctness-first closeout itself did not add a formal ARM benchmark.
Tasks 017 and 018 subsequently add the preregistered single-thread baseline and
paired CPU-threading experiment. Video, camera, Vulkan, quantization, and NPU
remain outside Stage 2.

## Stage 2 benchmark

Task 017, `Anlogic DR1 ARM CPU benchmark`, is `Completed`. Its protocol was
frozen before measurement:

- unchanged ncnn `20240410`, frozen YOLOv5n param/bin, fixed input, CPU FP32,
  batch 1, `640x640`, and one thread;
- five independent processes, each with 10 warmups and 20 measured pipelines;
- exact preprocess/inference/postprocess sums, nearest-rank P50/P90, sample
  standard deviation, aggregate-mean FPS, model-load time, and Peak RSS;
- read-only governor/frequency/thermal/environment observation;
- correctness against the PC C++ ncnn golden before and after every process;
- all raw samples and invalid-attempt evidence retained.

The approved real-board baseline contains five independent processes and 100
retained formal samples. It passes before/after correctness, deterministic
validator recomputation, the frozen `10%` stability gate with `1.688017802%`
round-mean spread, and user review. The unoptimized one-thread pipeline mean is
`3513.992354 ms` and sequential batch-1 FPS is `0.284576601`; inference is the
dominant stage.

## Stage 2 CPU threading experiment

Task 018, `Anlogic DR1 ARM CPU threading experiment`, is `Completed`. Its
protocol compares `configured_threads=1` and `configured_threads=2` while
holding the corrected OpenMP-enabled runtime, model, input, thresholds,
executable, timing, and statistics constant. Five pairs alternate `1→2`,
`2→1`, `1→2`, `2→1`, and
`1→2`; each condition receives five independent processes and 100 retained
samples.

The initial complete real-board session remains preserved, but a fixed-revision
source, build-cache, symbol, and short board-runtime audit confirmed that it used
`NCNN_OPENMP=OFF`, `NCNN_THREADS=ON`, and `NCNN_SIMPLEOMP=OFF` with no
effective operator-parallel backend. It is therefore retained as configured
thread-parameter sensitivity evidence, not published as a multithread
performance comparison.

The corrected formal session uses one standard-libgomp OpenMP-enabled ncnn
build for both conditions. The user-approved `BENEFICIAL` result reduces mean
pipeline latency from `3634.205540 ms` to `1969.402190 ms`, a
`1.845334365x` speedup and `84.533437%` FPS gain. Both 100-sample conditions
pass correctness and stability; cross-thread detections have IoU `1.0` and
confidence delta `0.0`. Task 017 remains the immutable different-build
historical baseline.

## Stage 2 ARM runtime profile

Task 019, `Anlogic DR1M90 dual-thread ARM runtime profile`, is `Completed`.
It preserves Task 017 as `baseline-single-thread` and makes the Task 018
OpenMP build `recommended-dual-thread` for explicit DR1 deployments. Profile
selection records thread/backend/build identity; the recommended profile fails
closed when OpenMP or its private hash-pinned libgomp is absent. Generic PC
defaults are unchanged.

The lightweight board gate reused the approved Task 018 ELF in a new isolated
directory and confirmed OpenMP, two observed process threads, `PASS_TARGET`
correctness, five detections, and exit zero. No benchmark session was rerun and
no new performance value was added.

## Future work: explicitly out of scope

Camera, Vulkan, quantization, affinity/NEON tuning, concurrent requests, and NPU
remain separate projects. Task 019 does not absorb those topics. NPU is `HOLD`.

## Stage 3 ARM video-file inference

Task 020 is `Completed`. Its real-board phase uses the Task 019
recommended OpenMP dual-thread profile and a 30-frame lossless FFV1/AVI
generated from the frozen reference image. The board decoded, processed,
annotated, wrote, and reopened all 30 frames; independent WSL validation reports
`PASS_TARGET` for every frame and decodes the returned MJPEG/AVI completely.
The user approved full playback and the representative first/middle/last
frames.

This is functional validation, not a formal video performance benchmark.
USB camera, streaming, async pipelines, dropped-frame policy, Vulkan,
quantization, and NPU remain outside Task 020.

## Stage 3 ARM UVC camera inference

Task 021 is `Completed` after automated validation and user representative-frame
review. The real DR1M90 camera
audit found two `uvcvideo` nodes and selected `/dev/video0` with V4L2 `YUYV`
`640x480` at negotiated `5 FPS`. A capacity-one latest-frame-wins slot keeps
capture bounded while the recommended Task 019 OpenMP dual-thread ncnn profile
processes ten retained frames. All retained frames replay through the approved
single-image path with `PASS_TARGET` equivalence; 101 overwritten frames are
recorded rather than hidden. This is functional camera validation, not a
realtime benchmark. Video streaming, camera performance benchmarking, Vulkan,
quantization, and NPU remain out of scope.

## Stage 4: Anlogic NPU runtime feasibility

The prior Task 022 local/VM/board audit and its incremental official AlWiki
scope are user-approved. Task 022 is complete as an audit, while NPU
deployment remains blocked; the primary result is still
`BLOCKED_DRIVER_OR_DEVICE`. APUG1205_0.1 and
IPUG166_1.0 document a cooperating PS HardNPU/PL SoftNPU path, required
SoftNPU bitstream, `hard_npu.ko`, `soft_npu.ko`, `cma_mem.ko`, CMA-backed
runtime APIs, and official `rt.bin`/`weight.bin` artifacts. On the current
DR1M90 eMMC image, CMA is reserved and a hard-NPU device-tree node is present,
but no matching modules or NPU/CMA device nodes are available. The VM SDK has
Arm NN/Alnpu candidate libraries and demo source but no identified standalone
`npu_runtime`, host converter executables, or official runtime model pair in
the searched paths. No bitstream, kernel, device tree, system library, or
vendor executable was changed or run. The project YOLOv5n NPU conversion is
not ready; a version-matched vendor runtime release and safe deployment plan
are required first. Secondary blockers are missing vendor assets, unverified
runtime ABI/identity, missing host tools, documentation gaps, and unknown
bitstream/Device Tree mapping. Task 023 should begin only after such a package
is received and its provenance is reviewed. The bounded public AlWiki audit
read seven selected pages through the official API (`7/7` HTTP 200), adding a
D20.1 DR1M90 Buildroot/HPF/module-selection flow and D20.0 NPU API evidence.
It exposed no downloadable, hashable current-board driver/runtime, bitstream,
one-shot, `rt.bin`/`weight.bin`, or host converter package; referenced example
assets remain access-pending and exact MLK-F3P-CZ02-DR1M90/Linux 6.1.111-rt42
mapping is unknown. No VM/board access or one-shot execution was performed in
the incremental pass. The completed Task 023 package-intake audit and its
remaining deployment gate are recorded below.

## Stage 4: Anlogic NPU package intake (Task 023)

Task 023 is `Completed` as a user-approved audit. The bounded intake of the user-provided
`NPU_info` package and the read-only AlWiki/Gitee sources reconstructed the
HardNPU/SoftNPU/CMA → HPF/bitstream/DT → Linux SDK → Arm NN/demo chain. The
native `npu_runtime`/`rt.bin`/`weight.bin` path remains unavailable, while the
Arm NN/ONNX face-demo path and the three SDK driver sources were configured or
compiled in isolated VM user workspaces. The driver outputs lack
`Module.symvers` symbol-CRC provenance, and the mixed board identities and
active FPGA/DT mapping remain unresolved. The primary verdict is
`BLOCKED_BOARD_HARDWARE_MAPPING`, with native-runtime, Arm NN backend,
deployment, build, release-identity, model and provenance blockers. No module
load, bitstream write, vendor execution, board deployment, or project-model
conversion was performed. Arm NN isolated build closure is verified, but board
deployment remains blocked and NPU runtime execution was not performed.

The next proposed task is **Task 024: MLK-F3P-CZ02 NPU board mapping and
controlled deployment plan**. It should identify the active bitstream and DTB,
map the MLK-F3P-CZ02 FPGA project and HPF/SDK version, obtain matching kernel
source/config/Module.symvers, and prepare a module load and SD-card rollback
plan. Any loading or flashing must remain behind a separate human approval.

## Stage 4: MLK-F3P-CZ02 board mapping (Task 024)

Task 024 is `Completed` as a read-only audit. A current board read confirmed the
`/dev/mmcblk1p1` boot and `/dev/mmcblk1p2` root files, kernel/DTB hashes, the
6.1.111-rt42/Buildroot 2022.02.6 ABI, the active 128 MiB CMA and hard-NPU
Device Tree semantics. The current BOOT.bin has `evb_dr1m90`/Build151508
markers but its FPGA payload/source identity remains opaque. The exact
DR1M90GEG400 Milianke NPU candidate and the official SDK/BoardImages release
line remain candidate metadata, not active proof. The primary verdict is
`BLOCKED_ACTIVE_BITSTREAM_IDENTITY`; source mapping, kernel symbols and
rollback evidence remain blocked. No module load, media write, bitstream
write, or vendor NPU program execution occurred. Current eMMC NPU readiness is
Not ready; controlled deployment is not approved and the SD-first strategy is
only recommended.

## Stage 4: NPU SD image preflight (Task 025)

**Task 025: MLK-F3P-CZ02 NPU SD image reproducible build and deployment
preflight** freezes clean SDK/toolchain/NPU project inputs, confirms the MLK
DR1M90GEG400 board project, attempts a matched BOOT.bin/DTB/kernel/rootfs/NPU
candidate, verifies HardNPU/SoftNPU/CMA and driver/Arm NN provenance, and stops
for human approval before writing an SD card. It must not replace the current
eMMC or load modules without separate approval.

Task 025 is `Completed`. The official SDK_2025.07-linux6.1 source line and
the Milianke DR1M90GEG400 FPGA lead are frozen by hash. An exact Git
superproject clone was made, but local relative submodules cannot be
materialized without the unavailable source repositories; the fuller vendor
release tarball was extracted but has no `.git` provenance and also contains no
MLK BoardConfig. The Arm NN application targets link as AArch64 binaries in an
isolated VM workspace, and recursive static analysis resolves all supplied
non-system `DT_NEEDED` libraries. The packaging script's `libprotoc.so*`
warnings are packaging-only for the inspected closure; OpenCV absolute RPATH
relocation remains a deployment caveat. The PDF-guided injection increment then
generated a same-workspace BOOT.bin, DTB, kernel and three NPU modules and
compiled the Arm NN demo in an isolated copy. A 141-entry Buildroot 2022.02.6
download cache was then hash-checked and reused with a network guard to build a
formal rootfs. Static inspection found 353 AArch64 ELF files, zero x86_64 files
and no missing DT_NEEDED names. The current primary result is
`READY_FOR_SD_WRITE_APPROVAL` for a complete external file set, not for a
partitioned image or board boot; no SD/eMMC write, module load, FPGA write,
vendor NPU execution or project-model conversion occurred. `candidate_approved`
is true only for static audit admission to a controlled deployment workflow;
`deployment_approval` remains `PENDING` and no real medium may be formatted,
partitioned or written without the separate Task 026 gate. The bounded
`03_demo` audit deep-audited
`05-5_NPU演示` and retained its substantive Arm NN/ONNX and
DR1M90GEG400-declared assets, while confirming mixed AD101/GEG484 metadata,
missing base DTS, differing platform/best-result bitstreams, and no native
`npu_runtime` or MLK BoardConfig. Those findings refine but do not close the
candidate identity blocker.

The bounded archive follow-up listed the direct 05-5 ZIP and recorded the two
large 3-2 FPSoc RAR SDK archives without extraction because no local RAR reader
is available. The deeper 3-2/3-4 audit found generic GEG400/FSBL/Linux
references but no MLK BoardConfig or base `anlogic-dr1m90.dts`. The 05-5 HPF
embeds the platform-copy bit, which differs from its best-result bit, and its
BOOT payload cannot be mapped without a packaged BIF/bootgen source. The
pre-injection candidate classification was `ASSET_IDENTITY_CONFLICT` and the
source-only verdict was `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`; the later
PDF-guided partial build is recorded below.

The exact expected ARM `uisrc-lab-anlogicM-V4.0.1` package is now identified
and provides generic DR1M source/toolchain/image-script structure, but its
embedded identity is SDK_2025.1 and it has no MLK BoardConfig or NPU userspace
closure. The expected `anlogic-linuxsdk` package was not found in the bounded
local scope. This is a `RECOVERABLE_STRUCTURE_VERSION_MISMATCH`, not a matched
candidate SD source; considered alone, that package-only increment left the
Task 025 primary block and `NOT_READY` status unchanged before the later formal
Buildroot increment.

The read-only VM history increment found the generic SDK_2025.07 tree and
generic `anlogic-dr1m90` base DTS, but no MLK BoardConfig or historical 2025.07
uisrc/05-5 source workspace. The VM demo is byte/tree-identical to the local
05-5 copy, so it does not close provenance. The formal Buildroot increment now
provides a complete external candidate file set; no partitioned SD image or
board runtime result is claimed.

## Task 026: MLK-F3P-CZ02 NPU controlled SD deployment and first-boot validation

Task 026 is the next planned, approval-gated activity. Before any destructive
operation it must identify the real SD device path, capacity, model, serial
number and `removable` attribute, and explicitly exclude the system disk, WSL
virtual disk, Windows system disk and the current development-board eMMC. It
must statically audit `make_parted.sh` and `deploy_image.sh`, perform only a
dry-run and candidate-file hash recheck, then stop until the user names the
target device and approves writing it. After approved writing, it must read
back and verify partitions, files and SHA256 values, boot from SD through the
serial console, validate the system and NPU drivers first, and only then
consider the official NPU Demo. The task must include a backup, serial recovery
and rollback plan and must never assume that a detected block device is safe.
