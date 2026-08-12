# Changelog

## Unreleased

- Continued Task 035 through the final independent COCO gate and ARM run. The
  500-image calibration block was excluded from all 4,500 evaluation images;
  exact subset IDs, COCO80 mapping and original-pixel bbox conversion were
  checked with AP confidence `0.001`, NMS `0.6` and maxDets 100. EQ's absolute
  mAP50/mAP50-95 degradation was `0.014296/0.014662` (limit `0.02`) with no
  zero-detection images. The same AArch64 `NCNN_INT8=ON` ELF measured
  `1.604359x` inference and `1.557952x` pipeline speedup versus FP32, with
  `55.795208%` FPS gain and `1.938084x` diagnostic convolution speedup. The
  experiment decision is `INT8_ACCEPTED`; the strict single-image regression
  remains secondary evidence and no NPU work is reopened.

- Completed Task 035. EQ is the accepted ARM INT8 configuration after the
  independent 4,500-image COCO gate and matching ARM benchmark; deployment
  thresholds remain unchanged, and no NPU work was reopened.

- Audited and repaired the Task 035 COCO evaluator before making an INT8
  verdict. The prior 500-prediction/5000-GT denominator and deployment-threshold
  report is retained as superseded evidence. The corrected evaluator constrains
  `imgIds` to the exact 500-image held-out manifest, verifies COCO80 category
  mapping and source-pixel `xyxy` to COCO `xywh`, and uses AP confidence `0.001`
  with NMS IoU `0.6` while deployment remains `0.25`/`0.45`. FP32/ACIQ/KL/EQ
  corrected mAP50 is `0.497349/0.475986/0.407040/0.484071` and mAP50-95 is
  `0.309718/0.285813/0.244242/0.293925`; FP32 sanity passes. Because no
  acceptable mAP degradation tolerance was pre-registered, the task remains
  `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`; no ARM INT8 benchmark is run.

- Completed the bounded Task 035 INT8 candidate matrix using the pinned ncnn
  official ACIQ, KL and EQ flows. The deterministic 500-image val2017 fallback
  (500 calibration, 500 disjoint held-out evaluation) produced held-out mAP50
  `0.040780/0.038645/0.009564/0.038569` for FP32/ACIQ/KL/EQ. ACIQ, KL and EQ
  all fail the unchanged frozen-reference and/or held-out correctness gates;
  the bounded verdict is `INT8_ACCURACY_REJECTED`. No ARM INT8 build or
  benchmark was entered, and the FP32 threads=2/default/packing-on deployment
  remains the accepted configuration.

- Continued Task 035 with bounded local validation. The pinned 20240410
  official flow used 22 unique calibration images (20 Task 021 replay frames
  plus two existing YOLOv5 v7.0 samples); no larger local set was available
  without fabricated or downloaded data. The historical "43" is a Python test
  count, not a 43-image Golden set, so the one disjoint `pc_reference.jpg`
  remains FP32-reference regression and no mAP is claimed. ACIQ failed the
  unchanged five-detection/IoU/confidence gate (3 detections; min IoU
  `0.9154784851416163`; max confidence delta `0.0782729983329773`), KL produced
  zero detections, and the bounded EQ search exited 130 before generating a
  table. No INT8 candidate or ARM benchmark is accepted; the VM wrapper issue
  is recorded separately and no NPU or board-system change was made.

- Reclassified the Task 035 task-level result to
  `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`: the retained 22-image
  calibration and one-image FP32-reference regression are not sufficient to
  claim overall COCO80 accuracy. The frozen model manifest confirms COCO80,
  but no local COCO train2017/val2017 images or `instances_val2017.json` were
  available. No data was downloaded or fabricated; ARM INT8 build and
  benchmark remain gated until real calibration and annotated evaluation data
  are supplied.

- Continued Task 035 with the user-provided official COCO archives. A
  deterministic val2017 fallback (train2017 images were not supplied) now
  provides 500 calibration and 500 disjoint held-out evaluation images. Fixed
  threshold FP32/ACIQ/KL held-out mAP50 is
  `0.040780/0.038645/0.009564`; mAP50-95 is
  `0.027727/0.025114/0.007113`. ACIQ count/class agreement with FP32 is
  272/500 and 314/500; KL is 75/500 and 78/500. EQ is still running through
  the official ncnn tool. The task remains
  `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`; no ARM INT8 build or benchmark
  is entered and the FP32 backend remains accepted.

- Completed Task 034 ARM ncnn inference-kernel/build optimization. A switchable
  `NCNN_BENCHMARK` layer profile attributes 80.304% of summed layer time to
  Convolution; the exact Release/OpenMP/packing build and graph conversion are
  audited. A correctness-passing `-mtune=cortex-a35` candidate is retained as
  rejected because it is 0.607296% slower in pipeline. PMU/perf is unavailable,
  and no INT8, NPU, kernel or board-system change is made.

- Started Task 033 ARM CPU profiling with a standalone ncnn profiler. The
  historical Task 017/018 measurements remain immutable; the new tool adds
  decode/NMS timing, runtime capability reporting, affinity and single-variable
  packing/FP16/threads experiments, all gated by the existing YOLOv5n golden.

- Completed Task 033 ARM CPU profiling on the two-core DR1 board. The accepted
  ncnn 20240410 OpenMP configuration uses two threads, default scheduling,
  packing on and FP32; it measured 1.789854x same-session pipeline speedup and
  78.985396% FPS gain over one thread with all retained rows passing the frozen
  golden. CPU affinity, packing-off and FP16 rows were retained as slower A/B
  evidence; no NPU or camera benchmark was added.

- Updated the Task 029 vendor handoff to `WAITING_FOR_VENDOR_INPUT` with the
  Task 032 ALHardNPU fusion addendum. The face ONNX has no ALHardNPU custom
  node; the audited `libarmnn.so.32.1` forms three `Alnpu|ALHardNPU`
  assignments during Optimize and contains `ConvertConv2dIntoALHardNPUImpl`,
  `checkConv`, `checkAct` and `checkPool`. The complete fusion predicate is not
  recoverable from public evidence, so the handoff does not claim YOLOv5n is
  inherently incompatible.

- Added Task 032's bounded ALHardNPU fusion eligibility audit. The matched
  AArch64 ArmNN binary contains the fusion implementation symbols and a finite
  ten-method Alnpu support whitelist, while generic YOLO layer slots resolve
  to `LayerSupportBase`. The face's three `Alnpu|ALHardNPU` assignments are
  retained, but exact fusion predicates and source-node regions are not
  recoverable from the stripped binary without backend source or an AArch64
  disassembler. The conservative result is
  `FUSION_PREDICATE_NOT_RECOVERABLE`; no model, board, runtime or benchmark
  change was made.

- Completed Task 031's read-only official NPU asset recovery and GEG400
  compatibility audit. The three public repository histories contain no
  recoverable `npuv1_release`, APUG1205 native compiler/runtime,
  `yolov5s_sim_quant_uint8.onnx`, materially broader Alnpu backend, or official
  GEG400 `NPU_Yolo` HPF/TD. Face `ALHardNPU` is an ArmNN fusion path, not an
  ONNX custom node. The scoped primary verdict remains
  `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`; no board, model, bitstream or vendor
  binary was changed or executed.

- Added Task 030's correctness-first PC C++ ORT and DR1M90 ARM ncnn benchmark
  consolidation. Retained raw campaigns are independently recomputed for stage
  mean/P50/P95, FPS, process CPU utilization, Peak RSS, and null
  frequency/temperature availability. The report uses the same frozen YOLOv5n
  v7.0 workload contract, makes no cross-platform speedup claim, and keeps
  vendor face NPU functional-only with YOLOv5n NPU `NOT_BENCHMARKED`.

- Completed the Task 028 C3c static Alnpu capability audit. The exact matched
  ArmNN binary exposes a finite ten-method `AlnpuLayerSupport` whitelist while
  generic Conv2d/Activation/Splitter/Add/Mul slots resolve to
  `LayerSupportBase`; the face positive is documented as an evidenced
  `ALHardNPU` fused/custom path. Track A/C3 therefore converge, for this
  backend identity, to `CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`.
  No new board workload, benchmark, fallback, or system change was performed.
- Closed Task 028 as `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. Track A retains its
  raw-ONNX ArmNN failure, C1 is `PASS`, C2 is paused after the independent
  quantized host gate, C3 stops before LoadNetwork at the compiled Alnpu
  LayerSupport boundary, and C4 remains `NOT_RUN`. Reopening requires a
  supported generic-YOLO backend, APUG1205 compiler/native runtime, or official
  DR1M90 GEG400 deployment chain; no NPU benchmark was claimed.

- Added the minimal repository documentation for the two-stage baseline.
- Added a C++17/CMake OpenCV smoke-test target that writes and verifies a
  640 x 360 image.
- Added an explicit Git line-ending policy.
- Removed legacy empty-directory placeholder files.
- Froze the YOLOv5n v7.0 source weights and ONNX contract and added the Python
  ONNX Runtime tensor, single-image, and golden-test baseline.
- Added backend-neutral C++ preprocessing/postprocessing, C++ ONNX Runtime image
  and video inference, and the unified Release-only PC benchmark framework.
- Added the fixed same-weight TorchScript-to-pnnx ncnn conversion contract and
  C++ ncnn image, video, correctness, and benchmark paths.
- Added the Task 012 six-round order-balanced Python ORT, C++ ORT, and C++ ncnn
  campaign with 1,800 retained samples, generated summaries, and validation.
- Added the generated PC acceptance README/report with correctness, stage timing,
  stability, position-effect, process CPU, Peak RSS, and limitation analysis.
- Completed PC Stage 1 and received Checkpoint C approval while keeping the
  Anlogic DR1 ARM CPU stage explicitly `Not implemented / Planned`.
- Completed the Anlogic DR1 ARM CPU single-image baseline with a frozen
  AArch64 ncnn build, real-board runtime smoke, frozen YOLOv5n deployment,
  PC/ARM `PASS_TARGET` correctness, byte-identical annotated output, and user
  visual approval.
- Added the preregistered DR1 ARM CPU benchmark with five independent
  processes, 100 retained samples, before/after correctness, independent
  statistic recomputation, stability validation, and user approval. The
  published result is the unoptimized CPU-only FP32 one-thread baseline; NPU
  remains out of scope and `HOLD`.
- Completed the paired DR1 CPU threading experiment with a shared
  OpenMP-enabled ncnn build and private libgomp. The user-approved
  `BENEFICIAL` result records `1.845334x` pipeline speedup and preserves the
  original OpenMP-off session as invalid-for-comparison sensitivity evidence.
- Added explicit DR1 ARM runtime profiles: a historical Task 017
  `baseline-single-thread` profile and a recommended Task 018
  `recommended-dual-thread` profile with fail-closed OpenMP, ncnn, thread, and
  private-libgomp identity validation. Generic PC defaults remain unchanged.
- Added Task 020's profiled AArch64 video-file path and reproducible 30-frame
  lossless fixture. The real board passes automated per-frame correctness and
  output-video decode validation, and the user approved full playback plus the
  representative frames. This is functional validation, not a formal video
  performance benchmark.
- Added Task 021's real-board UVC camera capability audit, V4L2 YUYV capture,
  capacity-one latest-frame pipeline, ten-frame bounded run, and offline replay
  evidence. Automated validation and user representative-frame review pass; the
  task is complete. No realtime camera benchmark or NPU claim is made.
- Completed and user-approved Task 022's bounded, read-only Anlogic NPU runtime
  and official YOLO one-shot feasibility audit. The result remains
  `BLOCKED_DRIVER_OR_DEVICE`: current-board NPU/CMA modules and device nodes,
  a versioned standalone `npu_runtime`, host converter tools, and official
  runtime model artifacts were not established. No vendor one-shot or project
  YOLOv5n NPU conversion was run; this is a current readiness block, not a
  claim that DR1M90 permanently lacks NPU support.
- Completed and user-approved the bounded official AlWiki incremental audit
  for Task 022. Seven
  selected public API pages were readable, documenting a D20.1 DR1M90
  Buildroot/HPF/module-selection flow and D20.0 NPU API symbols, but no
  verified current-board package or downloadable runtime assets. The primary
  verdict remains `BLOCKED_DRIVER_OR_DEVICE`; no VM/board access, attachment
  download, driver load, one-shot, or project-model conversion occurred.
- Completed and user-approved Task 023's read-only Anlogic NPU package intake.
  The native
  `npu_runtime`/`rt.bin`/`weight.bin` path remains asset-blocked, while the
  Arm NN/ONNX face-demo path and three SDK driver sources were built in
  isolated VM user workspaces. The driver objects have matching AArch64
  vermagic but no Module.symvers/symbol-CRC proof; mixed
  AD101V20/AD103V20/DR1M90GEG400/GEG484 identities and active FPGA/DT mapping
  remain unresolved. The primary intake verdict is now
  `BLOCKED_BOARD_HARDWARE_MAPPING`, with build, backend, deployment,
  provenance and asset secondary blockers. No vendor binary, module,
  bitstream, board deployment, or project model was executed. The audit is
  complete, but deployment remains blocked and the vendor one-shot and project
  YOLOv5n conversion were not performed.

- Started Task 028's ArmNN/Alnpu bring-up with an AArch64 runner that disables
  CPU fallback. The real frozen YOLOv5n FP32 parser attempt reports the
  unsupported `/model.11/Floor` operator; bounded exact-ORT graph repairs and
  a reproducible Conv-only QDQ conversion are retained, but parser/correctness
  gates remain blocked. The official Alnpu-positive model was graph-diffed
  against YOLOv5n; six static640 opset10/11/12 TorchScript exports passed local
  ONNX/ORT checks but all hit Floor on the board, while dependency-sliced
  probes isolated INT64-shape/Resize/FP32 limits. The refined conclusion is
  `VENDOR_TOOLCHAIN_REQUIRED`; no NPU benchmark number is recorded.

- Continued Task 028 with the APUG1205 native compiler/runtime track. The
  documented `convert_tool`/`.tmfile`/`al_ai_flow`/`rt.bin`/`weight.bin` flow,
  native headers/library and YOLOv5s positive-control assets were searched in
  the approved local, repository-history, VM and vendor-knowledge scopes but
  were not found. Track A remains `BLOCKED_UNSUPPORTED_ALNPU_GRAPH`; the active
  Track B conclusion is `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`. The
  05-5 platform bitstream statically confirms `NPU_SOFT=1` and `SOFT_YOLO=1`,
  but no native conversion, board execution or benchmark was performed.

- Added Task 028 Track C2 host-only opset13/14 deployment candidates using the
  same YOLOv5n v7.0 weights and static640 export. All four exports and the
  unchanged official uint8/int8 conversions pass ONNX/ORT structural checks;
  the opset12 int8 axis failure is resolved for these opsets. An independent
  eight-image held-out teacher-relative quantization gate still fails both
  types (class-multiset agreement is 87.5% for each; no ground-truth mAP is
  claimed), so Alnpu correctness and benchmark remain unexecuted.

- Continued Task 024's read-only MLK-F3P-CZ02 board mapping gate. A current
  board read confirmed BOOT.bin, boot.scr, system.dtb and uImage.lz4 hashes,
  active hard-NPU/CMA Device Tree semantics, and FPGA-manager operation. The
  BOOT.bin payload/source identity, exact SDK/BoardConfig lineage, kernel symbol
  provenance and rollback backup remain unresolved. Official dr1m90_npu,
  toolchains, BoardImages and sdk repository metadata were recorded; AD101V20
  images remain unsuitable as an unproven MLK substitute. No module, bitstream,
  media or vendor program was changed or executed.

- Completed and user-approved Task 024's board-mapping audit. The current
  eMMC boot chain and system.dtb are identified, but the BOOT.bin FPGA payload
  cannot be mapped to a known bitstream; the active DT has HardNPU but no
  SoftNPU node, no NPU device nodes exist, and no driver is deployed. The
  primary verdict remains `BLOCKED_ACTIVE_BITSTREAM_IDENTITY`; deployment is
  not approved. Proposed next task: reproducible MLK SD-image build and
  deployment preflight (Task 025). No board write or NPU execution occurred.

- Continued Task 025's read-only MLK-F3P-CZ02 SD-image preflight. The exact
  SDK_2025.07-linux6.1 superproject clone is reproducible, but local relative
  submodules cannot be materialized; the fuller official release tarball has
  no `.git` provenance and contains no MLK BoardConfig. Recursive static Arm NN
  dependency analysis resolves all supplied non-system `DT_NEEDED` libraries;
  the packaging script's `libprotoc.so*` warnings are not runtime dependencies
  for the inspected closure, while absolute OpenCV RPATH relocation remains
  unverified. The full matched SD chain remains blocked by
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`; no media, board, module, bitstream or
  vendor NPU program was changed or executed.

- Extended Task 025 with a bounded `03_demo` screening and deep audit of
  `05-5_NPU演示`. The Milianke package is a substantive DR1M90GEG400 Arm
  NN/ONNX and SoftNPU lead, but its mixed AD101/GEG484 metadata, missing base
  DTS, differing bitstream copies, and absent MLK BoardConfig/native runtime
  assets keep the candidate SD chain at
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`. No vendor binary, driver, board or
  storage media was executed or modified.

- Completed the bounded archive follow-up for Task 025 without changing its
  status or creating a commit. The 05-5 ZIP is listed and the large FPSoc RAR
  SDK archives are hash-recorded but not expanded because no local RAR reader
  is available. The deeper 3-2/3-4 audit confirms generic GEG400 process
  context, not a recoverable MLK BoardConfig; the 05-5 HPF embeds its platform
  bit while the saved best-result bit differs and BOOT payload mapping remains
  unresolved. Primary verdict remains
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`.

- Added a WSL-only Task 025 package identity increment. The exact expected
  ARM `uisrc-lab-anlogicM-V4.0.1` archive is present (MD5-matched) and was
  statically shown to contain a generic DR1M SDK_2025.1 source/toolchain and
  image-script skeleton, not an MLK BoardConfig or complete NPU userspace
  package. The expected `anlogic-linuxsdk` MD5 was not found locally; the
  candidate SD chain remains `BLOCKED_MLK_BOARD_PROJECT_IDENTITY` and no
  vendor or board binary was executed.

- Added a read-only VM history increment for Task 025. The VM contains a
  generic SDK_2025.07 marker tree with generic `anlogic-dr1m90` DTS files, but
  no MLK BoardConfig or recoverable submodule object provenance. Its Milianke
  V4.0.1 tree remains SDK_2025.1, and its 05-5 demo is an exact copy of the
  local package rather than an independently retained historical workspace.
  The primary candidate-SD verdict remains
  `BLOCKED_MLK_BOARD_PROJECT_IDENTITY`; no VM source, vendor program, board or
  media was modified or executed.

- Added a PDF-guided Task 025 injection reproduction in a fresh VM copy of the
  Milianke ARM package. The documented 05-5 FSBL, platform bitstream, DTS
  fragments and framebuffer sources produced same-workspace kernel/DTB, three
  NPU modules, U-Boot and `BOOT.bin`; the Arm NN demo also compiled as AArch64.
  The local Buildroot download cache was empty, so `make_rootfs.sh` was
  deliberately not run and no network fetch was attempted. The derived rootfs
  staging is not a Buildroot result, leaving the candidate at
  `BLOCKED_CANDIDATE_IMAGE_BUILD`. No board, media, FPGA or NPU program was
  touched.

- Continued Task 025 with a controlled Buildroot dependency closure. The
  2022.02.6 configuration used a 141-entry, hash-checked download cache; an
  offline-guarded build generated formal `rootfs.tar.gz`, `rootfs.cpio.lz4`
  and `uInitrd.lz4` outputs. Static validation found 353 AArch64 ELF files,
  zero x86_64 files and no missing DT_NEEDED names. The external candidate file
  set is `READY_FOR_SD_WRITE_APPROVAL`, but no partitioned SD image, SD/eMMC
  write, board boot, module load, FPGA write or NPU execution was performed.

- Completed and user-approved Task 025's static MLK SD-image preflight. The
  13-file external candidate set has a frozen checksum manifest and is
  `READY_FOR_SD_WRITE_APPROVAL`; `candidate_approved: true` admits it to a
  controlled deployment workflow only. `deployment_approval` remains
  `PENDING`, `candidate_sd_image` is `NOT_PARTITIONED_IMAGE`, and no physical
  medium, board, module, FPGA or NPU runtime was touched. Task 026 is planned
  for device identification, dry-run validation, and first-boot approval gates.

- Continued Task 028 with the official `dr1m90_npu` `AL_onnx_pass` Track C.
  A separate ext4 environment populated from the unchanged vendor requirements
  now closes the host dependencies and the unmodified frozen YOLOv5n entry
  emits the Detect-cropped FP32 and uint8 QDQ graphs. The uint8 host golden gate
  fails (minimum IoU `0.8421554845490358`, maximum confidence delta
  `0.09312496031303408`), so the current primary status is
  `BLOCKED_TRACK_C_QUANTIZED_CORRECTNESS`; no Alnpu run or benchmark was
  performed. A deterministic 500-image calibration smoke also fails the gate
  (minimum IoU `0.8891731303877853`). Track A remains
  `BLOCKED_UNSUPPORTED_ALNPU_GRAPH`, and Track B
  remains `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`.
- Split Task 028 Track C into explicit C1/C2/C3/C4 states. C1 official
  conversion is `PASS`; C2 quantized host accuracy is `NOT_ACCEPTED`; C3's
  real, Alnpu-only opset14 uint8 board smoke is
  `BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS` because QAsymmU8 Conv2d,
  Activation and ElementwiseBinary were rejected before `LoadNetwork`; C4
  benchmark remains `NOT_RUN`. The smoke used only board `/tmp`, made no system
  or media change, and accepted no CPU fallback. The vendor YOLOv5s positive
  control remains unavailable; `run_yolo_pic.sh` points to a separate
  `yolov8n.quant.onnx` demo.

- Extended Task 028 C3 with an Alnpu-only opset14 INT8 smoke and a bounded
  UINT8/INT8 operator probe matrix. The INT8 full graph reaches parser/network
  creation but Optimize rejects QSymmS8 Conv2d, Activation and
  ElementwiseBinary before LoadNetwork; all synthetic QDQ probes are retained
  as parser-dialect-inconclusive after parser-stage SIGSEGVs. The release
  YOLOv8n control also reaches parser/network creation but rejects QAsymmU8
  Splitter at Optimize. These controls show graph/operator coverage
  differences; runtime/toolchain skew is not proven. No CPU fallback or
  benchmark result was recorded.
- Audited Task 028 C3 runtime identity with the `dr1m90_npu` release ArmNN
  archive. Six compared shared-library hashes and the `ed5ae24` marker match
  the board runtime exactly; temporary `LD_LIBRARY_PATH`/`LD_DEBUG=libs`
  evidence proves candidate loading. The matched-runtime face control completes
  with Alnpu-only, while matched-runtime vendor YOLOv8n still fails Alnpu
  Optimize on QAsymmU8 Splitter. The runtime/toolchain skew sub-track remains
  `BLOCKED_RUNTIME_TOOLCHAIN_SKEW_UNPROVEN`; no benchmark or fallback result was
  added.
- Compared the 05-5 GEG400 SoftNPU HPF/bitstream with the official D20.1
  2025.7 AD101V20/GEG484 example after the matched-runtime YOLOv8n gate. The
  package, bitstream, SoftNPU address/IRQ, VDMA topology, and `SOFT_RESIZE`
  setting differ, so the AD101V20 asset is not a valid board substitute. The
  comparison supports a possible hardware/graph-dialect difference but does
  not prove user-space runtime skew; no bitstream or system file was changed.

- Added a static Task 028 C3 support-boundary audit. The matched
  `libarmnn.so.32.1` dispatches only a finite Alnpu layer-support whitelist;
  Conv2d, Activation, Splitter, Addition and Multiplication slots resolve to
  generic `LayerSupportBase` rejection methods. This matches the retained real
  vendor YOLOv8n `QAsymmU8 Splitter` failure and YOLOv5n UINT8/INT8 quantized
  layer failures. The face model remains the separate no-Split positive
  control; no benchmark or fallback result was added. A fresh board replay was
  not possible because the SSH/vsock wrapper failed before connection.

- Added Task 029's documentation-only vendor enablement handoff. The package
  at `docs/vendor_handoff/dr1m90_npu/` freezes Task 028 identities and evidence
  references, explains the scoped Alnpu capability boundary, and lists the
  exact questions required from Anlogic/Milianke. No new experiment or vendor
  material was added.
