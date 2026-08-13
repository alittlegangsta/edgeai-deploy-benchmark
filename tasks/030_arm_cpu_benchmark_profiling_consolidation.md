# Task 030

## Title

ARM CPU benchmark and profiling consolidation.

## Status

Completed

## Dependencies

Tasks 009, 012, 017, 018, and 029 (`Completed`).

## Recommended Branch

`dev` (the user explicitly selected this consolidation on the current `dev`
branch; no branch switch is authorized).

## Recommended Commit

`docs(benchmark): consolidate ARM CPU profiling results`

## Goal

Create a reproducible, read-only consolidation of the approved PC ONNX Runtime
and DR1 ARM ncnn YOLOv5n measurements. The consolidation must preserve the
historical evidence files, independently recompute the requested statistics,
and make the correctness and scope boundaries clear for documentation use.

## Frozen workload and comparison boundary

Both rows use the YOLOv5n v7.0 workload contract: the same fixed reference
image, 640x640 batch-1 preprocessing, FP32 semantics, confidence threshold
0.25, NMS IoU threshold 0.45, COCO-80 classes, and the no-in-graph-NMS output
contract. The PC row is the approved C++ ONNX Runtime CPU execution provider;
the ARM row is the approved Task 018 `recommended-dual-thread` ncnn CPU profile
(`ncnn 20240410`, OpenMP-enabled, configured threads 2). The ncnn param/bin are
the validated conversion of the same frozen YOLOv5n v7.0 weights, not the ONNX
file itself; this relationship is disclosed rather than hidden.

Task 030 does not rewrite or remeasure Tasks 009/012/017/018. It consumes their
retained raw samples and independently derives mean, nearest-rank P50/P95,
minimum, maximum, sample SD, aggregate FPS, CPU utilization, Peak RSS, and
frequency/temperature availability. The different historical sample counts
(PC: 600; ARM: 100) and environments are disclosed. No hardware speedup claim
is made from cross-platform rows.

## Unified measurement protocol

Each source campaign uses explicit process isolation, 10 warmups, repeated
timed samples, and the stage boundary:

`pipeline = preprocess + inference + postprocess`.

Image decoding, model/session load, correctness checks, rendering, and output
writes are excluded from the timed pipeline and reported separately where the
source contains them. Percentiles use nearest-rank; sample SD uses denominator
`count - 1`; FPS is `1000 / mean pipeline_ms`. CPU utilization is the recorded
process user+system CPU time divided by wall time on a one-core basis. RSS is a
process-level high-water mark. Unavailable CPU-frequency and temperature fields
remain JSON `null` and are not converted to zero.

## Correctness gate

Every included source campaign must retain before/after correctness checks with
five detections, finite and valid boxes, class agreement, minimum class-matched
IoU >= 0.99, and confidence delta <= 0.01 (the stricter source threshold is
preserved where applicable). A failed correctness gate makes the consolidated
row ineligible for benchmark publication.

## Backend status matrix boundary

The report includes these independent statuses:

| Backend | Status | Scope |
| --- | --- | --- |
| PC C++ ORT YOLOv5n | `BENCHMARKED_CORRECT` | WSL2 CPUExecutionProvider |
| ARM ncnn YOLOv5n | `BENCHMARKED_CORRECT` | DR1M90 CPU-only recommended dual-thread profile |
| DR1 vendor face NPU control | `FUNCTIONAL_CONTROL_ONLY` | Task 026 one-shot control; not YOLOv5n and not benchmarked |
| DR1 YOLOv5n NPU | `NOT_BENCHMARKED` | Task 028/029 vendor dependency blocker; no performance claim |

Face-NPU timings, if present in historical evidence, are never substituted for
YOLOv5n NPU results.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/030_arm_cpu_benchmark_profiling_consolidation.md
docs/benchmark/ARM_CPU_BENCHMARK_PROFILING_CONSOLIDATION.md
scripts/validate_task030_benchmark_consolidation.py
tests/python/test_task030_benchmark_consolidation.py
.knowledge/manifests/arm_cpu_benchmark_profiling_consolidation.yaml
results/evidence/030/benchmark_contract.json
results/evidence/030/pc_ort_benchmark.json
results/evidence/030/arm_ncnn_benchmark.json
results/evidence/030/backend_status_matrix.json
results/evidence/030/benchmark_comparison.json
results/evidence/030/validation.json
```

The source evidence under Tasks 009/012/017/018 and all NPU evidence under
Tasks 026/028/029 are immutable and are not allowed to change.

## Forbidden Files and Actions

- Do not modify Task 017, 018, 026, 028, or 029 evidence.
- Do not change the frozen model, input, thresholds, preprocessing, runtime
  semantics, or correctness tolerances.
- Do not use a different model or input to manufacture a cross-platform speedup.
- Do not benchmark NPU YOLOv5n, use the face control as a substitute, or reopen
  Task 028/029.
- Do not access the VM or board merely to regenerate existing measurements.
- Do not commit model, SDK, ELF, library, rootfs, or other binary assets.
- Do not push, create a PR, merge, rebase, reset, or delete user data.

## Acceptance Criteria

1. The contract, PC row, ARM row, comparison, and backend matrix are valid JSON
   and reference existing immutable source evidence with SHA256 identities.
2. The consolidation validator independently reads source raw samples and
   recomputes all four stage summaries, including nearest-rank P95, aggregate
   FPS, CPU utilization, RSS, and null resource availability.
3. Both YOLOv5n rows pass the retained correctness gates and share the frozen
   input/config/model-weight identity; model representation differences are
   explicitly disclosed.
4. The backend matrix marks vendor face NPU as functional-only and YOLOv5n NPU
   as `NOT_BENCHMARKED`.
5. Focused tests, Python unittest, JSON/YAML parsing, syntax checks, Release
   CMake build, CTest, link/sensitive-material/repository-hygiene checks, and
   `git diff --check` pass.
6. Task 017/018/026/028/029 paths remain byte-for-byte unchanged.
7. The task file records actual commands, skipped commands, evidence paths,
   validation output, and the final local commit if one is created.

## Execution Record

Started: `2026-08-11` (Asia/Shanghai)

Branch: `dev`

Starting commit: `83b20aa docs(npu): prepare DR1 vendor enablement handoff`

Starting status: clean.

Initial plan: consume retained PC Task 012 and ARM Task 018 raw evidence,
independently derive P95 and resource summaries, add only Task 030 evidence and
documentation, and avoid VM/board/NPU access.

Commands and results will be appended during execution. No new hardware
measurement is claimed unless a command actually runs and its raw output is
retained.

Completion record (`2026-08-11`, Asia/Shanghai):

- `python3 scripts/validate_task030_benchmark_consolidation.py --write` exited
  0 and generated the six JSON files under `results/evidence/030/`.
- `python3 scripts/validate_task030_benchmark_consolidation.py` exited 0;
  independently recomputed PC C++ ORT (600 samples, pipeline mean
  `51.802985673 ms`, P95 `54.415443 ms`, FPS `19.303906657`) and ARM ncnn
  recommended dual-thread (100 samples, pipeline mean `1969.402190140 ms`,
  P95 `1977.062930 ms`, FPS `0.507768299`).
- Focused Task 030 unittest passed 3/3. Full project Python unittest passed
  138/138 with `PYTHONPATH=python .venv/bin/python`.
- Release CMake build and CTest passed 5/5. JSON/YAML parsing, Python/Bash
  syntax, Markdown links, sensitive-material/repository hygiene, historical
  Task 017/018/026/028/029 immutability, and `git diff --check` passed.
- No VM/board access, NPU execution, new performance collection, model change,
  or source-evidence rewrite occurred. The source campaigns remain the actual
  measured evidence and all unavailable frequency/temperature values remain
  null/unavailable.
- Final local commit is recorded below after explicit-path staging.

## Skipped / not-run commands

- No VM or board benchmark rerun: existing approved raw campaigns are the
  consolidation inputs and historical evidence is immutable.
- No NPU execution or benchmark: Task 028/029 are frozen external dependency
  handoff results.
