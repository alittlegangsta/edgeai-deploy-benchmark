# Task 034

## Title

ARM ncnn inference-kernel and build optimization.

## Status

Completed

## Dependencies

Task 033 (`Completed`). Task 028/029/031/032 NPU work remains frozen at
`WAITING_FOR_VENDOR_INPUT` and is not reopened.

## Recommended Branch

`dev` (the user selected Task 034 on the current branch; no branch switch is
authorized).

## Goal

Explain and, where evidence supports it, reduce the ncnn inference-only cost of
the validated ARM YOLOv5n v7.0 CPU pipeline. Task 033's configuration is the
only baseline: ncnn 20240410, OpenMP, two threads, default scheduling, packing
on, FP32, fixed 640x640 input, confidence 0.25, and NMS IoU 0.45. No model,
input, threshold, kernel, boot, DTB, eMMC, SD or NPU change is in scope.

## Frozen baseline

```text
pipeline mean: 1963.817618 ms
inference mean: 1873.474372 ms
correctness: PASS_TARGET
runtime: recommended-dual-thread / OpenMP / threads=2 / packing=on / FP32
```

Task 017/018/030 evidence is historical and immutable. Task 033 evidence is
the reference for this task and must not be rewritten.

## Work contract

1. Add a profiling-only path that can be disabled and reports ncnn layer/operator
   type, layer name, tensor shapes, per-layer time, cumulative percentage and
   aggregate operator costs. It must not alter the ordinary image or benchmark
   semantics. The pinned ncnn source's `NCNN_BENCHMARK` facility may be used in
   an isolated profiling build; the production ncnn library remains unchanged.
2. Audit source revision, compiler, build type, flags, OpenMP, AArch64/NEON,
   runtime CPU dispatch, packing and LTO. Record facts from CMake cache,
   compile commands and ELF/static metadata, not assumptions.
3. Build reproducible A/B candidates from identical ncnn source. Change one
   explainable build variable at a time (for example a validated `-mcpu` or
   profiling-only `NCNN_BENCHMARK=ON`). Every performance candidate must pass
   the frozen golden before timing is retained.
4. Audit the YOLOv5n conversion graph for fusion, constant folding, dead-node
   removal and packing-friendly layout. Record `ALREADY_OPTIMIZED` or retain a
   correctness-gated candidate; do not silently replace the model.
5. Attempt only read-only PMU/perf observation when already available. Missing
   permissions or tools are recorded as unavailable; the kernel is never
   rebuilt or changed.
6. Decide from measured evidence whether the bottleneck is compute/kernel
   throughput or memory/cache pressure. Defer INT8 unless the FP32 profile
   establishes a justified next experiment.

## Required evidence

```text
results/evidence/034/
  profiling_contract.json
  layer_profile.json
  build_audit.json
  build_matrix.json
  graph_optimization_audit.json
  perf_capability.json
  validation.json
```

Large external build trees, model files, libraries and board logs remain
outside Git; evidence stores identities, hashes, summaries and commands.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/034_arm_ncnn_inference_kernel_build_optimization.md
docs/benchmark/ARM_NCNN_INFERENCE_KERNEL_OPTIMIZATION.md
cpp/CMakeLists.txt
cpp/apps/ncnn_layer_profiler.cpp
cpp/tests/test_ncnn_layer_profiler.cpp
scripts/validate_task034_ncnn_optimization.py
scripts/vendor/run_task034_ncnn_layer_profile.sh
scripts/vendor/audit_task034_ncnn_build.sh
results/evidence/034/**
```

Do not modify Task 017/018/030/033 evidence or any NPU evidence. Do not commit
model files, binaries, SDKs, libraries, build directories or private logs.

## Forbidden Actions

- No NPU investigation, CPU fallback, quantization, camera/video benchmark or
  model replacement.
- No kernel/boot/DTB/eMMC/SD/governor/frequency/service changes.
- No dependency download, sudo, apt, or system installation.
- No deletion of user data, push, PR, merge, rebase or reset.

## Acceptance Criteria

1. Profiling instrumentation is off by default and a real ARM layer profile is
   retained with top hot layers and operator aggregates.
2. Current ncnn build identity and optimization flags are independently audited.
3. Every attempted build/runtime A/B has an exact command, hashes and a frozen
   golden result; only correctness-preserving improvements may be accepted.
4. Graph optimization status and conversion provenance are recorded.
5. PMU/perf availability is reported without changing the kernel.
6. Bottleneck attribution and INT8 next-step recommendation are evidence-based.
7. Focused tests, Release build, CTest, Python unittest, JSON/YAML/syntax,
   immutability, repository hygiene and `git diff --check` pass.

## Execution Record

Started: `2026-08-11` (Asia/Shanghai)

Branch: `dev`

Starting status: clean after Task 033 commit
(`39e3f8e1e239100fc0bb0194dcc4234997bc8b09`).

The Task 033 baseline and evidence are frozen. Commands, attempts, real
outputs, skipped checks and completion status are appended here.

## Execution Record (continued)

Environment timestamp: `2026-08-11` (Asia/Shanghai). Branch remained `dev`;
Task 017/018/030/033 and all NPU evidence were not edited.

- `chmod +x scripts/validate_task034_ncnn_optimization.py`,
  `python3 -m py_compile scripts/validate_task034_ncnn_optimization.py` and
  `python3 scripts/validate_task034_ncnn_optimization.py --self-test` exited
  0. The self-test exercises repeated layer-sequence parsing and operator
  aggregation.
- The first parser invocation against the retained board log exited 1 because
  the profiler stores `ncnn_version` under `identity`, not `runtime.version`.
  Repair attempt 1 changed only the validator field lookup and corrected the
  JSON newline emission; the self-test, parser and build audit were rerun and
  passed.
- `python3 scripts/validate_task034_ncnn_optimization.py --layer-log
  /tmp/task034-board-logs/profile-v2.log --layer-run-json <external
  returned/layer_profile_run.json> --output results/evidence/034/layer_profile.json
  --candidate-a <external returned/a.json> --candidate-b <external returned/b.json>
  --candidate-output results/evidence/034/build_matrix.json` exited 0. The
  result retains 206 layers, six layer sequences, top-10 layers, operator
  aggregates, raw correctness identity and independent A/B resource summaries.
- `scripts/vendor/audit_task034_ncnn_build.sh --build-output <external
  Task 034 build-output>` exited 0 after `bash -n`. It verified the exact
  ncnn commit, frozen model/input hashes, Release AArch64 ELF headers, project
  CMake caches, explicit 20240410 identity and the OpenMP/threads/SimpleOMP
  options recorded in the VM build identity.
- The isolated VM build command was the successful `--execute` run of
  `scripts/vendor/run_task034_ncnn_layer_profile.sh`. It archived the exact
  ncnn commit and project inputs, built profiling plus A/B libraries and ARM
  profilers, and returned exit 0. Source archive SHA256 is
  `328fe282b98457d85ab56184fa896467f6bf640d4e48e91fcefc8d31889f92b7` and
  project archive SHA256 is
  `1e750316ddee296b270da6b536921c5403cafc0e5ce427e58a38054c4ad90737`.
- Build repair attempt 1 used `-mcpu=cortex-a35` for candidate B and failed in
  the compiler/source architecture-flag combination. It was not used for
  evidence. Repair attempt 2 rebuilt from the same clean archive with only
  `-mtune=cortex-a35`; the ncnn library and project linked successfully.
  Candidate A uses `-O3 -DNDEBUG`; both use Release, OpenMP ON, threads ON,
  SimpleOMP OFF, runtime CPU ON, VFPV4/inline ASM ON, BF16 ON, INT8/Vulkan/LTO
  OFF and explicit `NCNN_VERSION=20240410`.
- The returned board profile used the same frozen manifest, input, reference,
  threads=2, default affinity, packing on, FP16 off, warmup=2 and repeat=3.
  It exited 0 with `PASS_TARGET`, five detections, minimum IoU
  `0.9999855075776749`, maximum confidence delta
  `0.0000050067901611328125`, inference mean `1996.998719 ms` and pipeline
  mean `2089.939631 ms`. The layer log contains the diagnostic logging
  overhead and is not a replacement for Task 033's formal baseline.
- The returned A/B board runs used warmup=2 and repeat=5. A passed with
  inference mean `1890.049681 ms`, pipeline mean `1984.896740 ms`, p50
  `1983.248720 ms`, p95 `1999.116860 ms`, FPS `0.5038045455`, peak RSS
  `168136 KiB` and correctness `PASS_TARGET`. B passed correctness but was
  slower: inference mean `1901.869501 ms`, pipeline mean `1996.950938 ms`,
  p50 `1996.040330 ms`, p95 `2010.986300 ms`, FPS `0.5007634294`, peak RSS
  `168324 KiB`; B is rejected, with pipeline delta `+0.607296%` and inference
  delta `+0.625371%`.
- The read-only board capability probe recorded AArch64, two logical CPUs,
  CPU part `0xd04` and ASIMD/NEON features. `perf stat -e
  cycles,instructions,cache-references,cache-misses -- <profiler>` was
  unavailable with exit 127 (`perf: command not found`); readable frequency
  and thermal values were also unavailable. No kernel, governor, board
  service, boot asset or NPU state was changed.
- The frozen ncnn manifest records same-revision pnnx 20240410 `optlevel=2`,
  zero unsupported conversion operators, no custom layers, 207 ncnn layers
  and 237 blobs. This is recorded as `ALREADY_OPTIMIZED`; Conv/BN fusion and
  dead-node elimination are not separately claimed because the manifest does
  not quantify them.
- No FP32 optimization is accepted beyond the Task 033 frozen runtime profile.
  The evidence files are `results/evidence/034/`, the report is
  `docs/benchmark/ARM_NCNN_INFERENCE_KERNEL_OPTIMIZATION.md`, and the helper
  scripts are `scripts/validate_task034_ncnn_optimization.py`,
  `scripts/vendor/audit_task034_ncnn_build.sh` and
  `scripts/vendor/run_task034_ncnn_layer_profile.sh`. Large binaries, model
  files, libraries, raw logs and VM build trees remain outside Git.
- Offline validation then passed: the existing Release build required no work;
  CTest passed 15/15; the existing `.venv` plus `PYTHONPATH=python` passed the
  full Python unittest discovery with 152 tests; all Task 034 JSON and the
  repository YAML manifests parsed; Bash/Python syntax, local Markdown links,
  completed-task/NPU immutability scope, sensitive-material scan, repository
  hygiene and `git diff --check` passed. The system interpreter's separate
  unittest attempt was not used because it lacks pre-existing `cv2`, `onnx`
  and package imports; no dependency was installed. The consolidated results
  are in `results/evidence/034/validation.json`.

## Completion Record

Task 034 is completed after the user-approved freeze of the measured
conclusions. The retained profile reports 60 Convolution layers at 80.304% of
summed layer time; the Task 033 inference stage is 95.399611% of pipeline; and
`conv_3` is the hottest layer at 256.862 ms mean / 14.061%. The audited build
already has AArch64, NEON/ASIMD, OpenMP, runtime CPU dispatch and packing. The
frozen pnnx graph is `ALREADY_OPTIMIZED` at `optlevel=2`.

The `-mtune=cortex-a35` candidate passed the unchanged golden but was 0.607296%
slower in pipeline and is rejected. The best FP32 configuration remains
threads=2, default scheduling and packing on. `perf`/PMU was unavailable, so
no cache-miss claim is made. The evidence-supported attribution is primarily
FP32 convolution/kernel throughput; further generic runtime/build micro-tuning
is expected to have limited return. INT8 is deferred to a separate,
correctness-gated task and no INT8 result is published here.

Final offline validation passed: Release build, CTest 15/15, existing-venv
Python unittest 152/152, focused parser/build checks, JSON/YAML parsing,
syntax, Markdown links, immutability, sensitive-material scan, repository
hygiene and `git diff --check`. No NPU, kernel, boot, DTB, eMMC, SD or board
system change was made.

Final commit is created only after explicit-path staging and cached diff checks;
push and PR are not performed.
