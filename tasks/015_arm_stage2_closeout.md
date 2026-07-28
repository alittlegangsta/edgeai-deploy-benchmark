# Task 015

## Title

Consolidate and close the reproducible Anlogic DR1 ARM CPU single-image
deployment baseline established by Tasks 013 and 014.

## Status

Completed

## Stage

Stage 2

## Dependencies

Tasks 013 and 014 (`Completed`).

## Recommended Branch

`feature/arm-stage2-closeout`

## Recommended Commit

`docs(arm): close DR1 single-image deployment baseline`

## Goal

Reconcile the already approved toolchain, ncnn build, real-board runtime,
frozen-model deployment, PC/ARM comparison, and human visual evidence into one
auditable ARM CPU single-image baseline. Provide a clear path through the
existing build, validation, deployment, collection, and comparison entry points
without rerunning inference or introducing a second implementation.

## Scope

This task is limited to:

- consolidating immutable Task 013 and Task 014 evidence;
- freezing the VM, compiler, sysroot, ncnn, model, input, board, and
  correctness identities already observed;
- documenting how WSL, the Anlogic VM, and the real board participate in
  reproduction;
- documenting the existing build, host validation, deployment, collection,
  and PC/ARM comparison commands;
- checking tracked evidence hashes and repository hygiene;
- updating the repository entry points and Stage 2 status.

This task does not run or publish a formal ARM benchmark. It also excludes
model conversion, new inference, video, camera, Vulkan, FP16/BF16/INT8 runtime,
NPU, performance tuning, system-image changes, SDK changes, and PC benchmark
changes.

## Sources of Truth

```text
tasks/013_arm_toolchain_setup.md
tasks/014_arm_yolov5n_single_image.md
.knowledge/manifests/anlogic_aarch64_ncnn_build.yaml
.knowledge/manifests/anlogic_arm_yolov5n_single_image.yaml
results/evidence/013/anlogic_ncnn_board_smoke.json
results/evidence/014/anlogic_arm_ncnn_detections.json
results/evidence/014/anlogic_arm_ncnn_comparison.json
results/evidence/014/anlogic_arm_ncnn_validation.json
results/images/anlogic_arm_ncnn_reference.png
```

Completed-task evidence is immutable. In particular, the original Task 014
detection JSON retains the visual-review state recorded at board-run time; the
later user approval is recorded in the Task 014 validation evidence and
manifest.

## Allowed Files

```text
TASKS.md
tasks/015_arm_stage2_closeout.md
README.md
ROADMAP.md
CHANGELOG.md
.knowledge/manifests/anlogic_arm_stage2_closeout.yaml
docs/vendor/ANLOGIC_ARM_STAGE2_CLOSEOUT.md
```

## Forbidden Files and Actions

- Do not modify Tasks 001–014 or 016, their manifests, or their evidence.
- Do not modify PC benchmark data, the PC acceptance table, model manifests,
  frozen model/input/configuration files, thresholds, or PC golden files.
- Do not commit SDKs, CMake binaries, ncnn source/archive, `libncnn.a`, ARM
  ELF files, model `.param`/`.bin`, VM build trees, large logs, or credentials.
- Do not access the VM or board unless tracked evidence is missing,
  inconsistent, or a required acceptance command cannot otherwise be
  validated.
- Do not run inference, benchmark, video, camera, Vulkan, quantization, or NPU
  workflows.
- Do not add a duplicate build/deployment implementation when the Task
  013–014 scripts already provide the required stages.

## Reproduction Contract

The documented flow must identify:

1. the fixed ncnn remote, tag, commit, clean archive, and CMake source;
2. the validated Linaro compiler, target triple, glibc 2.25 sysroot, loader,
   and checked-in CMake toolchain file;
3. the exact CPU-only ncnn build options and static-library/smoke identities;
4. the frozen model, input, inference configuration, PC golden, and hashes;
5. the existing host build and validation commands;
6. the existing package, transfer, board-run, collection, and comparison
   commands;
7. which artifacts stay outside Git and which evidence is tracked;
8. which stages require WSL, the VM, or the real board.

The repository does not provide an unattended one-command pipeline. Build and
deployment remain deliberately separate because deployment accesses a real
board and must not be triggered by an offline documentation check.

## Acceptance Criteria

1. Tasks 013 and 014 are `Completed`.
2. CMake, compiler, sysroot, toolchain-file, ncnn source/options/output, and
   board-runtime provenance reconcile with the tracked evidence.
3. Frozen model, configuration, input, PC golden, ARM JSON/PNG, and validation
   hashes reconcile with the tracked files or approved ignored inputs.
4. The real-board ncnn model-free runtime smoke is `PASS`.
5. The real-board YOLOv5n single-image run exited zero and produced five finite
   detections with valid boxes and matching classes.
6. PC/ARM comparison is `PASS_TARGET`, with minimum class-matched IoU
   `0.999985507578` and maximum confidence delta
   `0.00000500679016113`.
7. The ARM PNG is byte-identical to the PC ncnn golden and the user visual
   review is `PASS`.
8. Build, validation, deployment, collection, and comparison steps are
   traceable to checked-in files without a duplicate implementation.
9. The repository contains no SDK, ncnn archive/source tree, CMake binary,
   `libncnn.a`, ARM ELF, ignored model binaries, credentials, or new large
   runtime logs.
10. Model-independent Release build, CTest, Python unittest, syntax, data,
    link, sensitive-material, and diff checks pass.
11. README, roadmap, task table, and ARM closeout document state that Stage 2
    single-image correctness is complete.
12. No formal ARM benchmark is presented as completed, and the boundaries for
    benchmark, video, camera, Vulkan, quantization, and NPU are explicit.

## Human Stop Conditions

Stop for human direction if:

- tracked Task 013 and Task 014 evidence conflicts and no authoritative source
  can be established without rerunning the board;
- a frozen model, input, threshold, Runtime revision, or PC golden would need
  to change;
- validation requires board access but the board is offline;
- credentials, `sudo`, SDK/system modification, or boot-media changes are
  required;
- the task would need to absorb a formal benchmark or change the deployment
  Runtime.

Ordinary documentation, link, schema, hash, task-state, and local validation
issues are repairable within this task.

## Validation Commands

The closeout must run repository-local checks only. At minimum:

```bash
bash -n scripts/vendor/build_anlogic_aarch64_ncnn.sh
bash -n scripts/vendor/validate_anlogic_aarch64_ncnn.sh
bash -n scripts/vendor/build_anlogic_aarch64_yolov5n.sh
bash -n scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
python3 -m json.tool results/evidence/013/anlogic_ncnn_board_smoke.json
python3 -m json.tool results/evidence/014/anlogic_arm_ncnn_detections.json
python3 -m json.tool results/evidence/014/anlogic_arm_ncnn_comparison.json
python3 -m json.tool results/evidence/014/anlogic_arm_ncnn_validation.json
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests/python -p 'test_*.py' -v
ctest --test-dir build/pc-acceptance-release --output-on-failure
git diff --check
```

Do not run the build/deployment scripts in `--execute` mode during closeout.

## Execution Record

Started: `2026-07-28`

Branch: `feature/arm-stage2-closeout`

Starting commit: `7cff6a3dae16e717e1deca8f24371de3bf5b86b3`

Starting status: clean; HEAD equals local `dev`.

Initial contract audit:

- `TASKS.md` defines Task 015 as consolidation and two-stage closeout.
- Neither `TASKS.md` nor `ROADMAP.md` assigns formal ARM benchmarking to this
  task.
- Existing Task 013–014 scripts already cover ncnn build, host validation,
  ARM application build, isolated deployment, board run, evidence return, and
  output decode.
- No VM or board access is required for the tracked-evidence reconciliation.

Resume instructions: reconcile the tracked manifests/evidence and frozen
hashes, write the minimal Stage 2 closeout manifest/document, update the
repository entry points, run the required offline validation, and mark Task
015 `Completed` only if every acceptance criterion passes.

### Evidence Reconciliation

Completed record time: `2026-07-28T16:33:11+08:00`

- All Task 013 and Task 014 JSON evidence parses.
- Replaying `tests/python/compare_detections.py` to `/tmp` reproduced five
  matches, minimum IoU `0.999985507578`, maximum confidence delta
  `5.00679016113e-06`, and `PASS_TARGET`.
- Task 013 evidence reports model-free ncnn board runtime `PASS`, exit code
  zero, and the expected ncnn API path.
- Task 014 validation reports five detections, finite values, valid boxes,
  matching classes, exit code zero, byte-identical PNG, and user visual
  approval `PASS`.
- The toolchain file, ignored model `.param`/`.bin`, model manifest,
  configuration, input, PC golden JSON/PNG, Task 013 evidence, Task 014
  evidence, and ARM output PNG all match their frozen SHA256 values.
- The ARM PNG decodes as `1280x960x3` and is byte-identical to the PC C++ ncnn
  golden.

No VM, board, inference, or benchmark command ran during this reconciliation.

### Reproduction Entry Audit

The existing scripts cover the required stages:

```text
scripts/vendor/build_anlogic_aarch64_ncnn.sh
scripts/vendor/validate_anlogic_aarch64_ncnn.sh
scripts/vendor/build_anlogic_aarch64_yolov5n.sh
scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
```

The ncnn build script has explicit `--check` and `--execute` modes, the host
validator verifies the installed library/cache/ELF, the application builder
uses the checked-in toolchain and ARM OpenCV package, and the deployment script
hashes, packages, transfers, runs, collects, and decodes the result. The latter
performs a real-board preflight even in `--check` mode. A new orchestration
script was intentionally not added because it would duplicate these entry
points or hide their VM/board side effects.

### Validation Results

- YAML: 41 files / 42 documents parse with `yaml.safe_load_all`.
- Required Task 013–014 JSON: 4/4 parse with `python3 -m json.tool`.
- Evidence reconciliation and frozen/local hash checks: PASS.
- Markdown relative links: 10/10 resolve across 52 Markdown files.
- All tracked shell scripts pass `bash -n`; the BusyBox board probe also passes
  `sh -n`.
- Model-independent Release build: PASS
  (`build/ci-cpp-local-release`, 17 build steps).
- Model-independent CTest: 4/4 PASS.
- Fully configured PC CTest: 12/12 PASS; invalid-argument tests did not run
  inference or benchmark.
- Python unittest discovery: 64/64 PASS.
- Sensitive-material and tracked-forbidden-artifact scans: PASS.
- The model `.param`/`.bin` remain ignored; no SDK, source archive, ARM ELF,
  static/runtime library, credential, or new runtime log is tracked.
- `git diff --check`: PASS.

The first aggregate YAML check used single-document `safe_load` and correctly
rejected an existing multi-document YAML file. Re-running with
`safe_load_all`, which matches the repository's data shape, passed all files;
no YAML content change was required.

One custom task-scope assertion searched for the exact phrase `formal ARM
benchmark`, while the closeout document expresses the boundary as no ARM
performance and no benchmark command/result. The assertion was corrected to
check those two explicit statements; no product, evidence, or task-contract
change was required.

All Acceptance Criteria passed with only the Task 015 Allowed Files changed.
Task 015 is `Completed`. The proposed Task 017 benchmark is not started, and
NPU remains `HOLD`.
