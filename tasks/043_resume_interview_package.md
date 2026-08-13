# Task 043 — Resume & Interview Package

Status: Completed
Dependency: Task 042
Recommended branch: `dev`

## Objective

Create interview-ready career material from the frozen Task040 results and
validated Task evidence.  This task is documentation-only: it adds no backend,
model, benchmark, optimization, board run or NPU experiment.

## Acceptance criteria

1. Five career documents exist under `docs/career/`.
2. Resume bullets, pitches, Q&A and stories use only traceable evidence and
   state the NPU boundary accurately.
3. `FINAL_PROJECT_FACTS.md` is the single short list of permitted numbers and
   claims for future resume/interview use.
4. A deterministic validator checks required sections, authoritative values,
   source links and forbidden NPU overclaims.
5. Markdown links, focused tests, Python syntax, JSON parsing,
   sensitive-material scanning and `git diff --check` pass.

## Allowed files

`TASKS.md`, `tasks/043_resume_interview_package.md`,
`docs/career/RESUME_PROJECT.md`, `docs/career/PROJECT_PITCH.md`,
`docs/career/INTERVIEW_QA.md`, `docs/career/PROJECT_STORIES.md`,
`docs/career/FINAL_PROJECT_FACTS.md`,
`scripts/validate_task043_career_package.py`,
`tests/python/test_task043_career_package.py`, plus minimal allow-list
extensions in `scripts/validate_task041_presentation.py` and
`scripts/validate_task042_demo_release.py` so the cumulative offline suite can
recognize this documentation-only task.

## Forbidden changes

Do not modify Task040/041/042 evidence, README, models, backends, benchmark
values, NPU runtime, board files or source inference code.  Do not add
credentials, vendor binaries, model files, screenshots or new measurements.
Do not claim custom YOLOv5n ran on the DR1 NPU, claim a face-model speedup over
CPU/GPU YOLOv5n, or reopen the vendor dependency.

## Execution record

- Started: 2026-08-13 Asia/Shanghai; branch `dev`; starting worktree clean after
  combined finalization commit `8f49b3a42ba8c35882668654bb4d09c7eb61d17a`.
- Source authority is `results/final/authoritative_results.json`; supporting
  facts are linked to existing Task evidence only.
- No model, board, NPU, benchmark or performance command is run by this task.
- Historical Task041/042 validator changes, if needed for cumulative path
  hygiene, are limited to allow-lists and committed-artifact existence
  semantics; they do not change their presentation assertions or evidence.
- `python3 scripts/validate_task043_career_package.py` passed with the frozen
  Task040 SHA256 `d18208ac620edf97719ba25d49b0c9dc19a1d3a4d483ef0b222b580c0c95f416`
  and 13 local Markdown links checked.  Task040, Task041 and Task042 validators
  also passed.
- Focused Task043 tests passed `3/3`; the complete offline Python suite passed
  `177/177` using `PYTHONPATH=python .venv/bin/python`.  Python syntax, JSON
  parsing, career Markdown links, sensitive-material scan and `git diff --check`
  passed.
- A clean-worktree rerun after the first local commit exposed a validator
  assumption that career files were still dirty.  The validator now accepts
  either changed or tracked career files; the focused `3/3` and full `177/177`
  suites pass in the clean committed state.
- No model, backend, benchmark, board, NPU or performance command was run.

## Final state

`Completed` / `RESUME_INTERVIEW_PACKAGE_READY`.  The package is documentation-only
and introduces no new experiment or technical result.

## Resume instructions

The package is complete.  Future edits must continue to use the authoritative
Task040 manifest and preserve the explicit NPU boundary.
