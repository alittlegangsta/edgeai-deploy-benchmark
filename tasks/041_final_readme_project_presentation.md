# Task 041 — Final README & Project Presentation

Status: Completed
Dependency: Task 040
Recommended branch: `dev`

## Objective

Turn the completed deployment work into a concise, interview-ready project
homepage and a reproducible demonstration plan.  This task changes presentation
only; it does not add a backend, alter a model, rerun a benchmark, or rewrite
Task 001–040 evidence.

## Acceptance criteria

1. The README explains the project, deployment pipeline, supported backends,
   final measured results, trade-offs, DR1 capabilities and quick-start path in
   a 30-second scan.
2. Final benchmark numbers are read only from
   `results/final/authoritative_results.json` and formal rows are not replaced
   by Task038/039 integration timings.
3. Mermaid architecture and deployment-flow diagrams are present.
4. A one-to-two-minute demo script, shot list and screenshot/results inventory
   point to existing evidence without adding binary copies.
5. NPU scope is accurate: the vendor face path is an
   `Alnpu | ALHardNPU` functional control with no CPU fallback, while custom
   YOLOv5n remains `WAITING_FOR_VENDOR_INPUT`.
6. The deterministic validator and focused tests pass, as do Markdown-link,
   syntax, repository-hygiene and `git diff --check` checks.

## Allowed files

`README.md`, `TASKS.md`, `tasks/041_final_readme_project_presentation.md`,
`docs/PROJECT_PRESENTATION.md`, `scripts/validate_task041_presentation.py`,
`tests/python/test_task041_presentation.py`.

## Forbidden changes

Do not modify Task 001–040 evidence, models, engines, source inference code,
benchmark values or NPU assets.  Do not add videos, screenshots, SDKs, models,
credentials or vendor binaries.  Do not claim a camera run is a realtime
benchmark, use the face NPU control as a YOLO speed result, or imply that custom
YOLOv5n ran on NPU.  Do not push, create a PR, merge, rebase or reset.

## Execution record

- Started: 2026-08-13 Asia/Shanghai; branch `dev`.
- The worktree already contains the uncommitted Task040 presentation/evidence
  freeze.  Those allowed files are preserved while Task041 adds its own
  presentation files; no prior evidence is being rewritten.
- `python3 scripts/validate_task041_presentation.py` passed with 24 local
  Markdown links checked and all eight presentation/hygiene checks green.
- `PYTHONPATH=python .venv/bin/python -m unittest
  tests.python.test_task041_presentation -v` passed `3/3`.
- The complete offline Python suite passed `171/171`; Python syntax and
  `git diff --check` passed.  No benchmark, board run, NPU run or asset build
  was performed.
- Final status: `Completed` / `FINAL_PROJECT_PRESENTATION_READY`.  The
  Task040/041 presentation changes were initially left uncommitted because this
  task did not request a commit; the later user-requested combined finalization
  commit covers them together with Task042, and its SHA is reported in the final
  handoff.  No push or PR was created.

## Resume instructions

Run `python3 scripts/validate_task041_presentation.py`, then the focused and
full Python tests.  Keep Task040's authoritative manifest immutable and do not
add binary demo artifacts.
