# Task 042 — Final Demo Capture & Release Validation

Status: Completed
Dependency: Task 041
Recommended branch: `dev`

## Objective

Prepare a reproducible one-to-two-minute interview demonstration from the frozen
Task040 results and Task041 presentation plan.  This task creates commands,
release metadata, asset references and validation only; screen recording remains
a manual operation and no new backend, model, optimization or benchmark is
introduced.

## Acceptance criteria

1. The package covers exactly four segments: README/architecture, PC TensorRT
   FP16 video, DR1 UVC camera with ncnn EQ INT8, and DR1 vendor face
   `Alnpu | ALHardNPU` control.
2. Every command, asset, overlay, narration point and expected duration is
   recorded in `docs/FINAL_DEMO_GUIDE.md` and `release/demo/manifest.json`.
3. Formal values are derived from
   `results/final/authoritative_results.json`; Task038/039 timings are never
   published as formal benchmark rows, and the camera result is labeled
   integration evidence.
4. The vendor face path explicitly requires an `Alnpu | ALHardNPU` assignment,
   rejects CPU fallback and is not compared with YOLOv5n performance.
5. Existing representative screenshots, output video and structured evidence
   are referenced by SHA256 without copying new binaries into Git.
6. The deterministic validator, focused tests, Markdown links, Python syntax,
   repository hygiene and `git diff --check` pass.

## Allowed files

`TASKS.md`, `tasks/042_final_demo_capture_release_validation.md`,
`docs/FINAL_DEMO_GUIDE.md`, `release/demo/manifest.json`,
`scripts/validate_task042_demo_release.py`,
`tests/python/test_task042_demo_release.py`, and the minimal historical
Task041 validator allow-list extension in
`scripts/validate_task041_presentation.py` (no Task041 presentation content or
evidence is changed).

The pre-existing uncommitted Task040/041 files are preserved and are not
rewritten by this task.

## Forbidden changes

Do not modify Task001–041 evidence, models, engines, source inference code,
NPU/SDK assets or benchmark values.  Do not fabricate a screen recording or
claim that a prepared command was executed.  Do not call Task039 camera timing
formal performance, use the face NPU control as a YOLOv5n speed result, or
imply that custom YOLOv5n ran on NPU.  Do not access the board, install
dependencies, download data, push or create a PR.

## Execution record

- Started: 2026-08-13 Asia/Shanghai; branch `dev`; the worktree already contains
  Task040/041 allowed presentation changes.
- The local PC `edgeai_demo` binary and TensorRT engine are not present in the
  current checkout, so no new PC video run is claimed.  Existing Task039 PC
  video evidence and Task036/039 DR evidence are used only as recorded assets.
- The manifest generator/validator and guide are added below.  Manual screen
  capture is intentionally not performed by the CLI task.
- The Task041 validator's path allow-list was extended only to recognize these
  Task042 evidence-only files; this keeps the cumulative suite composable and
  does not change any Task041 presentation assertions or source evidence.
- `python3 scripts/validate_task042_demo_release.py --write` generated and
  validated the four-segment manifest; the default validator then passed with
  18 hashed assets and 14 local Markdown links.
- `python3 scripts/validate_task040_final_results.py` and
  `python3 scripts/validate_task041_presentation.py` both passed.  Focused
  Task041/042 tests passed `6/6`; the complete offline suite passed `174/174`
  using `PYTHONPATH=python .venv/bin/python`.
- Python syntax, JSON parsing, sensitive-material scan, Markdown links and
  `git diff --check` passed.  No inference, screen recording, VM/board access,
  engine build, NPU execution or benchmark rerun was performed.

## Final state

`Completed` / `FINAL_DEMO_PACKAGE_READY`.  The four commands remain
`PREPARED_NOT_RUN`; the screen recording is intentionally left for manual
capture.  The later user-requested combined finalization commit covers
Tasks 040–042; its SHA is reported in the final handoff.

## Resume instructions

The package is complete.  If a later recording is made, rerun the validator
before and after the manual capture, but do not execute the prepared board/NPU
commands merely to validate this documentation package.
