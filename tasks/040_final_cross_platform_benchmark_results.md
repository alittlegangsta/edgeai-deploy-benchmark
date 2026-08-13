# Task 040 — Final Cross-platform Benchmark & Results Freeze

Status: Completed
Dependency: Task 039
Recommended branch: `dev`

## Objective

Freeze the authoritative, provenance-linked YOLOv5n benchmark and accuracy
results from Tasks 030, 033, 035, 036, 037, 038 and 039.  This task consolidates
existing evidence only; it does not introduce a backend, model, quantization
method, optimization, or new performance run.

## Acceptance criteria

1. Every authoritative number is sourced from an existing structured evidence
   file whose current SHA256 is recorded.
2. Formal benchmark, integration evidence, functional control and
   vendor-blocked status are distinct and cannot be confused in the final
   tables.
3. The final manifest contains PC ORT, RTX TensorRT FP32/FP16, DR ncnn FP32/EQ
   INT8, DR face Alnpu control and custom DR YOLOv5n NPU status.
4. The accuracy/performance trade-off table uses the corrected Task035 COCO
   gate and Task037 COCO gate; the older single-image diagnostics remain
   secondary evidence.
5. Task039 camera and Task038 unified-app timings are explicitly integration
   evidence, not formal realtime or cross-platform benchmark claims.
6. README-ready tables, a provenance document, a deterministic validator and
   focused tests are present.
7. JSON/YAML parsing, focused tests, the full Python suite, Markdown links,
   sensitive-material/repository hygiene checks and `git diff --check` pass.
8. Task 001–039 evidence is not modified.

## Allowed files

`TASKS.md`, `README.md`, `tasks/040_final_cross_platform_benchmark_results.md`,
`results/final/authoritative_results.json`,
`results/final/README_READY_TABLES.md`, `results/final/validation.json`,
`docs/FINAL_BENCHMARK_RESULTS.md`,
`scripts/validate_task040_final_results.py`,
`tests/python/test_task040_final_results.py`.

## Forbidden changes

Do not modify Task 001–039 evidence, models, engines, SDKs, runtime files or
benchmark measurements.  Do not rerun a benchmark merely to align numbers, do
not claim cross-hardware speedups with mismatched protocols, do not classify
camera integration as a realtime benchmark, and do not use the face NPU control
as a YOLOv5n speed result.  Do not add binaries, models, videos, datasets,
credentials or vendor packages.  Do not push, merge, rebase or reset.

## Execution record

- Started: 2026-08-13 Asia/Shanghai; branch `dev`; initial worktree clean after
  Task039 commit `94315a18f62edccd6c9848fa373e59a29fa2deb7`.
- Source evidence is being read and aggregated without rerunning PC, DR, GPU,
  camera or NPU workloads.  The generated manifest records WSL generation time
  as record time, not benchmark time.
- `python3 scripts/validate_task040_final_results.py --write` generated the
  authoritative manifest, README-ready tables, provenance report and validation
  record.  It captured 17 existing source evidence files and recomputed each
  SHA256.
- Task037 timing provenance was reconciled from `results/evidence/037/benchmark.json`
  and the TensorRT C++ timing implementation: `inference_wall_ms` is the
  backend-call wall boundary (3.71244466/3.71610421 ms, including H2D,
  `enqueueV3`, D2H and synchronization), while `gpu_inference_ms` is the CUDA
  event around `enqueueV3` only (1.6742607927/1.37037856 ms).  Task038's
  integration values (4.2555388/7.3970642 ms) remain non-formal and are not
  used in the formal rows.
- `python3 scripts/validate_task040_final_results.py` passed.  Focused tests
  passed `4/4` with `PYTHONPATH=python .venv/bin/python -m unittest
  tests.python.test_task040_final_results -v`.
- The full offline Python suite passed `168/168` using
  `PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p
  'test_*.py'`.  An initial invocation without `PYTHONPATH=python` produced
  four import errors; no source was changed and the repository-standard command
  immediately passed.
- Prior read-only validators passed: Task030 consolidation, all retained Task
 033 profiler rows, Task034 parser self-test, Task035 INT8, Task036 face,
  Task037 TensorRT, Task038 unified and Task039 video/camera.
- Tracked JSON/YAML parsing passed (`299` JSON, `44` YAML); Python syntax,
  Markdown links, sensitive-material scan, Task040 allowed-file/repository
  hygiene and `git diff --check` passed.  No Task001–039 evidence path changed.
- No C++ build, GPU run, board access, camera run or benchmark rerun was needed:
  Task040 changes are reporting/validation only and prior build/run evidence is
  immutable.
- Provenance correction rerun: `python3 scripts/validate_task040_final_results.py
  --write` and the default validator both passed.  The focused suite now passes
  `4/4`; the full offline suite passes `168/168` using the repository
  `PYTHONPATH=python .venv/bin/python` command.  The explicit timing policy
  records Task037 backend-call wall values (3.71244466/3.71610421 ms), CUDA
  execution values (1.6742607927/1.37037856 ms), and separate Task038
  integration values (4.2555388/7.3970642 ms).  An initial exploratory
  invocation of the Task036 validator at a non-existent root path exited 2;
  the correct `scripts/vendor/validate_task036_npu_face.py` invocation passed.
- Post-correction read-only validators passed: Task030 consolidation, Task033
  accepted profile, Task034 self-test, Task035 self-test, Task036, Task037,
  Task038 and Task039.  Tracked JSON/YAML parsing remains `299`/`44`, while
  the two new Task040 JSON files also parse successfully; Markdown links,
  Python syntax, sensitive-material/repository hygiene and `git diff --check`
  pass.
- Final generated files are `results/final/authoritative_results.json`,
  `results/final/README_READY_TABLES.md`, `results/final/validation.json` and
  `docs/FINAL_BENCHMARK_RESULTS.md`; README and TASKS index the freeze.
- Final worktree initially contained only the nine Task040 allowed paths and
  remained uncommitted by user instruction.  The user later requested one
  combined local finalization commit covering Tasks 040–042; its SHA is
  reported in the final handoff.

Final status: `Completed` / `FINAL_BENCHMARK_RESULTS_FROZEN`.  No benchmark
rerun, board access or prior-evidence rewrite occurred; the later combined
commit request is documentation-only finalization.

## Resume instructions

Run `python3 scripts/validate_task040_final_results.py` from the repository
root, inspect `results/final/validation.json`, then rerun the focused and full
offline test commands listed in the execution record.  Do not regenerate or
alter prior Task evidence.
