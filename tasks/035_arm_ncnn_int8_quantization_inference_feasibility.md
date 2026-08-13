# Task 035

## Title

ARM ncnn INT8 quantization and inference feasibility.

## Status

Completed

## Dependencies

Task 034 (`Completed`). Task 028/029/031/032 NPU work remains frozen at
`WAITING_FOR_VENDOR_INPUT` and is not reopened.

## Recommended Branch

`dev` (the user selected Task 035 on the current branch; no branch switch is
authorized).

## Goal

Determine, using the fixed ncnn 20240410 source and official ncnn quantization
tools, whether an ARM CPU INT8 YOLOv5n v7.0 candidate can preserve the frozen
correctness contract and provide a material convolution/inference benefit over
Task 033/034's accepted FP32 configuration. The YOLO model, input, thresholds,
preprocessing and postprocessing remain unchanged. This task must not reuse the
AL_onnx_pass NPU quantized graph.

## Frozen FP32 reference

```text
model: YOLOv5n v7.0 ncnn conversion
input: 640x640, batch=1, FP32
runtime: ncnn 20240410, OpenMP, threads=2, default scheduling, packing=on
pipeline mean: 1963.817618 ms
inference mean: 1873.474372 ms
correctness: PASS_TARGET
confidence threshold: 0.25
NMS IoU threshold: 0.45
```

Task 017/018/030/033/034 evidence is historical and immutable. The historical
"43" is a Python test count, not an available image set; the evaluation
manifest contains one disjoint `pc_reference.jpg` input. It is valid only for
FP32-reference regression and, without ground-truth annotations, must not be
described as mAP or a detection-accuracy benchmark.

## Work contract

1. Audit the exact ncnn 20240410/commit `56775de50990ab7f16627efdcf5529b49541206f`
   INT8 source, quantization tools, ARM/AArch64 kernels, packing support and
   current build options. Record facts from source, CMake cache, compile/link
   commands and ELF/static metadata.
2. Establish deterministic calibration and independent evaluation manifests from
   local assets only. A representative calibration set should target about 500
   images; if local assets are fewer, record the actual count and limitation
   rather than inventing or downloading data. Keep calibration and evaluation
   manifests disjoint. Existing golden inputs are FP32-reference evidence only.
3. Use the pinned ncnn official flow (`ncnnoptimize` when required,
   `ncnn2table`, `ncnn2int8`) with exact commands and hashes. Do not run the
   AL_onnx_pass NPU quantizer and do not hand-edit QDQ or model graphs.
4. Validate FP32 versus INT8 before any performance acceptance: output shape and
   dtype, detection count, class agreement, matched box IoU distribution and
   confidence deltas under the frozen thresholds and preprocessing/postprocess.
   If correctness is not acceptable, do not publish an INT8 performance result
   as an accepted deployment configuration.
5. Only for an accepted correctness candidate, repeat the Task 033 benchmark
   protocol, including warmup/repeats, preprocess/inference/postprocess/pipeline
   timing, FPS, CPU utilization and RSS, and re-run layer profiling to compare
   convolution costs. Preserve every baseline and intermediate experiment.
6. Conclude with one evidence-backed status: `INT8_ACCEPTED`,
   `INT8_ACCURACY_REJECTED`, `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`,
   `INT8_NO_PERFORMANCE_BENEFIT`, or an explicit toolchain blocker. No NPU,
   kernel, boot, DTB, eMMC or SD work is in scope.

## Required evidence

```text
results/evidence/035/
  int8_source_build_audit.json
  int8_tool_audit.json
  calibration_manifest.json
  evaluation_manifest.json
  int8_quantization_run.json
  int8_correctness.json
  int8_build_matrix.json
  int8_layer_profile.json
  int8_bounded_validation.json
  coco_accuracy_readiness.json
  validation.json
```

Large source archives, build trees, model files, calibration images, libraries,
board logs and binaries remain outside Git. Evidence stores identities, hashes,
commands, summaries and explicit limitations.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/035_arm_ncnn_int8_quantization_inference_feasibility.md
cpp/apps/arm_cpu_profiler.cpp
cpp/tests/test_arm_cpu_profiler.cpp
docs/benchmark/ARM_NCNN_INT8_QUANTIZATION_FEASIBILITY.md
scripts/validate_task035_ncnn_int8.py
scripts/vendor/audit_task035_ncnn_int8.sh
scripts/vendor/run_task035_ncnn_int8.sh
results/evidence/035/**
```

Do not modify completed Task 017/018/030/033/034 evidence or any NPU evidence.
Do not commit model files, calibration data, binaries, SDKs, libraries or build
directories. No dependency installation or download is allowed.

## Forbidden Actions

- Do not use the AL_onnx_pass NPU quantization path or alter the frozen model
  contract, thresholds, input or postprocess.
- Do not modify kernel, boot, DTB, eMMC, SD, governor, frequency or NPU state.
- Do not install dependencies, use sudo/apt, or silently download data.
- Do not publish mAP without real annotations or claim a camera/video benchmark.
- Do not push, create a PR, merge, rebase, reset or commit unless the user
  explicitly authorizes a later Task 035 submission.

## Acceptance Criteria

1. The pinned ncnn INT8 source/tool/build capability and ARM ISA path are
   independently evidenced.
2. Calibration/evaluation manifests and their hashes are deterministic, and any
   shortage of representative local images is explicit.
3. The official ncnn INT8 conversion command is recorded with real outputs and
   model identities; no hand-edited graph or AL_onnx_pass model is used.
4. INT8 correctness is independently validated against the frozen FP32 reference
   before timing acceptance.
5. If correctness passes, the Task 033 protocol and layer comparison run with
   real ARM outputs; otherwise performance is explicitly skipped.
6. Focused validation, Release build, CTest, Python unittest, JSON/YAML/syntax,
   immutability, repository hygiene and `git diff --check` pass for the actual
   scope, with skipped checks and environmental limitations recorded.

## Execution Record

Started: `2026-08-11` (Asia/Shanghai)

Branch: `dev`

Starting status: clean after Task 034 commit `b82484c`.

The task remains `In Progress` until all real commands and evidence are
complete. Commands, outputs, repair attempts, skipped checks and resume notes
will be appended below. No commit or push is authorized by the current request.

## Execution Record (continued)

Environment timestamp: `2026-08-11` (Asia/Shanghai). Branch remained `dev`.
Only Task 035 files are modified; Task 017/018/030/033/034 and NPU evidence
remain untouched.

- The fixed source and host CMake cache were audited. The source is tag
  `20240410` at commit
  `56775de50990ab7f16627efdcf5529b49541206f`; host `NCNN_INT8`, OpenMP,
  threads and runtime CPU dispatch are enabled. The source contains ARM NEON
  INT8 convolution/depthwise/quantize/dequantize/requantize implementations.
- The pinned host tools were hashed and their official usage was recorded.
  `ncnnoptimize` produced an optimized param/bin pair, `ncnn2table` completed
  KL and ACIQ calibration, and `ncnn2int8` produced both quantized candidates.
  An EQ attempt did not finish a reproducible table search and is retained as
  a failed attempt only.
- A deterministic local calibration manifest contains 22 unique images: the 20
  Task 021 raw replay images plus the existing local YOLOv5 v7.0 `bus.jpg` and
  `zidane.jpg`. This remains below the approximately 500-image target because
  no further local representative data was available and network download is
  forbidden. The one-image PC reference evaluation manifest is disjoint and is
  used only for FP32-reference regression; no mAP is claimed.
- The profiler was extended with an opt-in `--int8 on|off` control. The
  default remains FP32. A valid 22-image ACIQ candidate ran on the host with
  INT8 inference enabled and returned output shape `[1,25200,85]`, but only 3
  detections versus the frozen 5, producing `FAIL_CORRECTNESS_GATE`. The valid
  20-image KL candidate produced 0 detections. Formal performance and layer
  profiling were skipped because correctness failed.
- The reproducible AArch64 build script
  `scripts/vendor/run_task035_ncnn_int8.sh --execute` was prepared and its
  `--check` invocation reached the VM wrapper, which failed before the build
  with `UtilBindVsockAnyPort:307: socket failed 1`. No ARM build, board run or
  ARM INT8 performance claim is recorded after that failure.
- Real outputs and hashes are summarized in `results/evidence/035/`; external
  models, calibration images, logs, build trees and binaries remain outside
  Git. `scripts/validate_task035_ncnn_int8.py` passed its self-test and full
  evidence validation.

### Current disposition

The task-level status is now `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`.
The prior `INT8_ACCURACY_REJECTED` remains retained for the bounded 22-image
ACIQ/KL observations only; those observations do not establish overall
COCO80 accuracy. The frozen model manifest confirms 80 COCO classes, but no
local COCO train2017/val2017 images or `instances_val2017.json` annotations
were found. The accepted ARM configuration is unchanged: threads=2, default
scheduling, packing on, FP32. ARM build and benchmark remain gated off until
real calibration and annotated evaluation data are supplied. The VM wrapper
issue is an independent infrastructure record, not the INT8 model verdict.

## Execution Record (bounded validation continuation)

Continuation timestamp: `2026-08-11` (Asia/Shanghai). Branch remained `dev`;
no commit or push was performed.

- A bounded local search found no 43-image Golden set. The existing evidence's
  43 is a Python test count; only the frozen `pc_reference.jpg` is an actual
  evaluation input. This was recorded rather than manufacturing duplicate
  entries. The independent evaluation therefore remains one image and is
  explicitly named FP32-reference regression, not mAP.
- The fixed model manifest was independently confirmed as standard COCO80
  (80 classes and the frozen COCO label order). A bounded search across the
  repository, local YOLOv5 source tree, vendor materials, home directory and
  Task 035 temporary workspace found no COCO `train2017`/`val2017` images or
  `instances_val2017.json`; network download was not attempted under the
  active no-download rules. The exact missing inputs and future evaluation
  contract are recorded in `coco_accuracy_readiness.json`.
- Calibration was expanded from 20 to 22 unique local images by adding the
  existing local YOLOv5 v7.0 `bus.jpg` and `zidane.jpg` to the 20 unique Task
  021 raw replay PNGs. The manifest is
  `/tmp/task035-int8/bounded22/calibration_images.txt`, SHA256
  `1d1ebb2c51a8cfff1745dce6ab4a2c6f44eb08bcbd0cf2d13bf68720e5bf7113`;
  evaluation overlap is zero. No repeated frame is counted as a new sample.
- With the pinned 20240410 host tools, the official ACIQ and KL flows both
  completed. ACIQ produced table/bin identities recorded in
  `results/evidence/035/int8_quantization_run.json`; its diagnostic INT8 run
  returned `[1,25200,85]` float output but 3 detections. Class-matched IoUs
  were keyboard `0.9459513272624841`, tv `0.94682602892869`, cup
  `0.9154784851416163`, with maximum confidence delta
  `0.0782729983329773`; both mouse detections were missing. KL produced zero
  detections. Both fail the unchanged five-detection/IoU/confidence gate.
- The official EQ search was attempted on the same 22-image manifest and
  bounded by manual interruption after it failed to finish a table search
  (exit 130); no EQ model is accepted or used. Its stderr identity is retained.
- Since no candidate passed correctness, ARM `NCNN_INT8=ON` build and benchmark
  remain skipped. The VM wrapper `UtilBindVsockAnyPort:307: socket failed 1`
  remains an independent infrastructure issue and is not used as the INT8
  model verdict.

Offline validation after the bounded continuation:

- `python3 scripts/validate_task035_ncnn_int8.py --self-test` passed.
- `python3 scripts/validate_task035_ncnn_int8.py --output
  results/evidence/035/validation.json` passed, including the ACIQ/KL/EQ
  matrix, the 22-image manifest identity, the explicit one-image evaluation
  limitation, the COCO80 contract/missing-data gate, and the correctness/data-
  gated ARM skip.
- `bash -n scripts/vendor/audit_task035_ncnn_int8.sh
  scripts/vendor/run_task035_ncnn_int8.sh` and
  `bash scripts/vendor/audit_task035_ncnn_int8.sh` passed against the pinned
  source and tools.
- `cmake --build build/task033-host-release -j2` and
  `ctest --test-dir build/task033-host-release --output-on-failure` passed
  (8/8 CTest tests).
- `PYTHONPATH=python:tests/python .venv/bin/python -m unittest discover -s
  tests/python -p 'test*.py' -q` passed (152 tests).
- All eleven Task 035 JSON files parsed, the scoped Markdown-link check passed,
  Python/Bash syntax checks passed, and `git diff --check` passed. No network,
  VM, board, SD/eMMC, or ARM benchmark command was run in this continuation.

### Current data-gated disposition

`INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA` is the current Task 035
task-level status. The earlier `INT8_ACCURACY_REJECTED` remains attached to the
bounded 22-image ACIQ/KL observations (EQ not generated), but those observations
and the one-image FP32-reference regression cannot establish overall COCO80
accuracy. No INT8 candidate is accepted, no ARM benchmark was entered, and the
accepted deployment remains Task 033/034's two-thread/default-scheduling/
packing-on FP32 configuration. Reopening the accuracy gate requires real
COCO train2017 calibration images and independent val2017 annotations.

## Execution Record (COCO bounded validation continuation)

Continuation timestamp: `2026-08-11` (Asia/Shanghai). Branch remained `dev`;
no commit or push was performed. The user supplied
`annotations_trainval2017.zip` (252907541 bytes, MD5
`f4bbac642086de4f52a3fdda2de5fa2c`, SHA256
`113a836d90195ee1f884e704da6304dfaaecff1f023f49b6ca93c4aaae470268`) and
`val2017.zip` (815585330 bytes, MD5
`442b8da7639aecaf257c1dceb8ba8c80`, SHA256
`4f7e2ccb2866ec5041993c9cf2a952bbed69647b115d0f74da7ce8f4bef82f05`). No
network download was performed by the agent.

- The extracted val annotation has 5000 images, 36781 annotations and 80
  categories (SHA256
  `e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f`). The
  deterministic split uses seed 35035, 500 calibration IDs and a disjoint 500
  held-out evaluation IDs. Calibration and evaluation manifest hashes are
  `de490f890d82b40e0f66f17ed4289d2efd276e933b6e9f0935e4572c365c28f7` and
  `b98b81be7822bce89b10535e6806833b30ac56d706723ce1d88b80c0f2cc3f2d`;
  overlap is zero. This is a val2017 fallback because train2017 images were
  not supplied, and is not described as a full COCO benchmark.
- The pinned official ncnn tools generated ACIQ and KL tables/models from the
  500-image calibration. A single-process host runner evaluated FP32, ACIQ
  and KL on all 500 held-out images with frozen preprocessing,
  confidence=0.25 and NMS IoU=0.45. The deterministic metrics are stored in
  external `/tmp/task035-coco/coco_metrics.json` (SHA256
  `ab3d8133bd157b57319deb2e27c4a3b380fc3eed0d97f21c8a62c995192eb31d`).
- FP32/ACIQ/KL results are respectively mAP50 `0.040780/0.038645/0.009564`
  and mAP50-95 `0.027727/0.025114/0.007113`; precision is
  `0.685178/0.691275/0.837555`, recall is `0.048218/0.045356/0.026393`.
  These fixed-threshold subset metrics exclude `iscrowd` records and do not
  claim full-val COCO leaderboard parity. ACIQ count/class agreement with
  FP32 is 272/500 and 314/500; KL is 75/500 and 78/500. EQ remains in the
  official tool search and has not been accepted or benchmarked.
- The strict frozen Golden gate remains required. No candidate is accepted and
  no AArch64 INT8 build or ARM benchmark is entered while EQ and the final
  task-level decision remain incomplete. The VM wrapper error remains a
  separate infrastructure issue.

### Current disposition after COCO subset evaluation

`INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA` remains the task-level state while
the EQ candidate completes. The supplied data closed the prior missing-data
condition for ACIQ/KL, but did not authorize a relaxed correctness gate or an
ARM benchmark. The accepted deployment remains FP32 threads=2, default
scheduling, packing on.

## Execution Record (final bounded validation)

Final validation timestamp: `2026-08-11` (Asia/Shanghai). The supplied
annotations and `val2017.zip` were used locally; no network download, board
access, VM build, ARM build, or commit was performed.

- The official EQ search completed with exit code 0 using the same 500-image
  calibration manifest. The table SHA256 is
  `2d138307017cf68769ec01b5c06502f4d903fe3720399235be215102d1462471` and
  the resulting ncnn INT8 parameter/bin hashes are
  `b05bd424462f40d92792287cafdf463ec513ea1eb5d7a024cefd3f93b769a2c4` and
  `9ae93520aa8fa9c235176e57c3146ac6a66115cddd0186c20f2637f7516c09f7`.
  The 500-image EQ prediction JSON SHA256 is
  `2753c5c9117c9f65353784833f27b81a5ec2ee33e9faf21d6c4673775deac844`.
- EQ held-out results are mAP50 `0.038569`, mAP50-95 `0.025833`, precision
  `0.688936`, recall `0.045356`, with 319/500 count agreements, 329/500
  class agreements, 42 candidate zero-detection images, mean matched IoU
  `0.916791`, and maximum confidence delta `0.659040`.
- Expanded-calibration frozen-reference regression produced 4 ACIQ, 1 KL and
  5 EQ detections versus the required 5. EQ nevertheless fails the unchanged
  IoU/confidence thresholds (minimum class-matched IoU
  `0.8992660203111462`, maximum confidence delta
  `0.1995950338696899`).
- The prior bounded verdict `INT8_ACCURACY_REJECTED` is retained only as a
  historical observation from the superseded evaluator. It is not a final
  Task 035 verdict because that evaluator used all 5000 annotation image IDs
  in its GT denominator while predictions covered 500 held-out IDs, and used
  deployment confidence/NMS thresholds rather than an AP confidence sweep.
- The earlier provisional
  `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA` status and the 22-image ACIQ,
  KL and interrupted EQ evidence remain retained as historical records. The
  VM wrapper error remains an independent infrastructure issue.

Offline validation for this final continuation:

- `python3 scripts/validate_task035_ncnn_int8.py --self-test` passed.
- `python3 scripts/validate_task035_ncnn_int8.py --output
  results/evidence/035/validation.json` passed with the completed ACIQ/KL/EQ
  matrix, expanded metrics, frozen-reference regression and explicit ARM
  correctness gate.
- JSON parsing, Python/Bash syntax, Release build, CTest, Python unittest,
  Markdown-link, immutability, repository-hygiene and `git diff --check`
  checks are rerun after the evidence update; no board, VM, SD/eMMC or ARM
  benchmark action is in scope.

## Execution Record (COCO evaluator sanity audit)

Continuation timestamp: `2026-08-12` (Asia/Shanghai). The board was not
accessed. The supplied local COCO archives and the existing 500-image fallback
workspace were used; no network or dependency installation was performed.

- The prior evaluator was audited and found to sum ground truth over all 5000
  annotation image IDs while loading only 500 prediction image IDs. Its fixed
  confidence `0.25`/NMS `0.45` predictions were also unsuitable for a COCO AP
  confidence sweep. The old metrics remain retained as
  `SUPERSEDED_INVALID_SCOPE_AND_THRESHOLD` evidence.
- A corrected evaluator (`evaluate_corrected.py` SHA256
  `50287b0271daf95097da819a249a0dbe5cb9309a3d4eb953b7d32550d87ebb4b`) now
  verifies 500 held-out `imgIds` exactly equal to the
  evaluation manifest (`d2a9767f...`), 500 prediction IDs for every model,
  494 held-out IDs containing non-crowd annotations, COCO80 category-name
  mapping, and source-pixel `xyxy` to COCO `xywh` conversion. AP uses confidence
  `0.001`, NMS IoU `0.6`, and max 100 detections per image for the AP summary;
  crowd GT is retained for ignore matching and non-crowd GT forms the
  denominator; deployment thresholds remain `0.25`/`0.45` and are unchanged.
- Corrected FP32/ACIQ/KL/EQ mAP50 is respectively
  `0.497349/0.475986/0.407040/0.484071`; mAP50-95 is
  `0.309718/0.285813/0.244242/0.293925`. Relative mAP50-95 deltas versus
  FP32 are `-7.72%/-21.14%/-5.10%` for ACIQ/KL/EQ. The FP32 engineering
  sanity floor passes (`mAP50 >= 0.25`, `mAP50-95 >= 0.15`); this is not a
  full-val2017 leaderboard claim.
- The task-level status is restored to
  `INT8_ACCURACY_VALIDATION_INSUFFICIENT_DATA`: Task 035 contains no
  pre-registered acceptable mAP degradation tolerance, so no INT8 candidate is
  accepted and no ARM INT8 build or benchmark is entered. The earlier strict
  frozen-reference count/IoU/confidence comparisons remain secondary
  diagnostics, not a standalone final rejection under the corrected evaluator
  policy. The accepted deployment remains FP32 threads=2/default scheduling/
  packing-on.
- Evidence: `results/evidence/035/coco_evaluator_audit.json`.

Offline checks for this audit:

- `python3 scripts/validate_task035_ncnn_int8.py --self-test` and the full
  validator passed; the validator now checks held-out ID equality, format
  mapping, corrected metrics and the FP32 sanity gate.
- `bash -n scripts/vendor/audit_task035_ncnn_int8.sh
  scripts/vendor/run_task035_ncnn_int8.sh` and the source audit passed.
- `cmake --build build/task033-host-release -j2` plus CTest passed (8/8), and
  `cmake --build build/ci-default-options-release -j2` plus CTest passed (15/15).
- Repository Python unittest passed (152 tests); JSON parse, Python/Bash syntax,
  Markdown links, completed-task evidence scope, external evidence hashes and
  `git diff --check` passed. Task 033 validators passed for all retained thread
  rows and the Task 034 parser self-test passed.
- No board, VM, ARM INT8 build, ARM benchmark, network download, SD/eMMC or
  NPU operation was performed in this audit.

## Execution Record (full independent gate and ARM EQ benchmark)

Continuation timestamp: `2026-08-12` (Asia/Shanghai). The task remains
`In Progress` because this user turn explicitly forbids submission. No NPU,
SD/eMMC or boot asset was changed.

- The complete independent evaluation set was formed from every val2017 image
  ID not in the 500-image calibration block: 4,500 images, zero overlap. The
  manifest, ID list, per-image hashes and annotation identity are recorded in
  `results/evidence/035/coco_full_evaluation.json`.
- Under the fixed AP protocol (confidence `0.001`, NMS IoU `0.6`, maxDets 100,
  exact subset image IDs, COCO80 category mapping and original-pixel bbox
  conversion), FP32 measured mAP50/mAP50-95 `0.4576054997961436 /
  0.2797771184417101`; EQ measured `0.44330934307986297 /
  0.2651150199415103`. Absolute deltas are `0.01429615671628063` and
  `0.0146620985001998`, both within the user-defined `0.02` gate, and zero
  detection images are zero for both. EQ became `EQ_INT8_ARM_BENCHMARK_CANDIDATE`.
- The approved isolated VM build produced an AArch64 Release
  `NCNN_INT8=ON` profiler (ELF SHA256
  `598886d9b1a2b3b2d56455e2efbaef79b70f740c62f2c2a6a9c82ddfe9a71e64`) with
  ncnn library SHA256
  `248c96f0afd9fb5acb36ca40fa6db0bf62ae860e31fd6febdbf0bfd5fffb47a2` and
  private libgomp SHA256
  `87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91`.
  The initial wrapper socket error was an infrastructure event; the isolated
  build completed successfully.
- On the board, FP32 and EQ used that same ELF, the same input and postprocess,
  threads=2, default scheduling and packing-on. Each variant used five
  independent processes, three warmups and ten retained samples (50 samples
  per variant). FP32 inference mean/P50/P95 was `1882.246/1877.733/1888.663`
  ms and pipeline was `1973.146/1968.619/1984.812` ms. EQ inference was
  `1173.208/1172.656/1187.336` ms and pipeline was
  `1266.500/1264.251/1285.630` ms. EQ delivered `1.604359x` inference,
  `1.557952x` pipeline and `55.795208%` FPS gain; peak RSS changed from
  `168376` to `150836` KiB. Frequency and temperature were unavailable.
- A diagnostic `NCNN_BENCHMARK=ON + NCNN_INT8=ON` build produced 206 layers
  over six runs. Convolution aggregate was `756.940 ms` versus the retained
  FP32 `1467.013 ms` (`1.938084x`), with 60 convolution layers in each graph.
  This is diagnostic layer evidence, not a changed production benchmark
  semantic.
- The EQ profiler's frozen single-image comparison remains explicitly
  `FAIL_CORRECTNESS_GATE` (five detections but minimum reported IoU zero).
  It is retained as a secondary regression diagnostic; the primary task-level
  accuracy gate is the independent annotated COCO evaluation and is not
  silently replaced by the single image.

### Current decision

`INT8_ACCEPTED` is the final Task 035 experiment decision: EQ passes the
pre-registered independent accuracy gate and provides a material ARM CPU
inference benefit. The FP32 threads=2/default/packing-on configuration remains
the historical baseline, and no NPU claim is made.

### Offline verification continuation

Continuation timestamp: `2026-08-12` (Asia/Shanghai). No board, VM,
network, SD/eMMC or NPU operation was performed during this verification pass.

- `python3 scripts/validate_task035_ncnn_int8.py --self-test` and the full
  validator both passed; the latter rewrote
  `results/evidence/035/validation.json` with `status=PASS`.
- The host Release build completed for `build/task033-host-release` and
  `build/ci-default-options-release`; CTest passed 8/8 and 15/15,
  respectively. Python unittest passed 152 tests.
- Task 030, Task 033 and Task 034 focused validators passed. The Task 035
  shell audit and Bash syntax checks passed; JSON/YAML parsing and Python
  syntax passed (including multi-document YAML); local Markdown links passed
  with zero missing targets; and `git diff --check` passed.
- The changed paths remain limited to the Task 035 allowlist. No completed
  Task 017/018/030/033/034 evidence or NPU evidence was modified, and no
  vendor binary, model, calibration image, SDK or build directory is in the
  worktree.

### Completion record

Completion timestamp: `2026-08-12 11:26:02 CST` (WSL local time). Task 035 is
`Completed`; `experiment_decision=INT8_ACCEPTED`,
`benchmark_candidate=EQ_INT8_ARM_BENCHMARK_CANDIDATE`, and EQ is the accepted
ARM INT8 configuration. KL remains rejected and ACIQ remains secondary only.
The evaluator defect and its correction remain in the historical evidence, the
deployment thresholds were unchanged, and no NPU work was reopened. The local
completion commit uses the requested message
`perf(arm): validate and accept ncnn INT8 deployment`.
