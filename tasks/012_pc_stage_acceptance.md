# Task 012

## Title

Complete the PC-stage comparison, README, and acceptance report.

## Status

Completed

## Batch

Batch C

## Dependencies

Task 011 (`Completed`).

## Recommended Branch

`feature/pc-batch-c-ncnn-acceptance`

## Recommended Commit

`docs(pc): complete stage acceptance report`

## Goal

Validate all immutable PC-stage evidence, rerun representative Python ORT, C++
ORT, and C++ ncnn paths, generate the truthful three-backend performance table,
and document reproducible PC usage and an explicit acceptance matrix.

## Why This Task Exists

A stage is complete only when its commands, artifacts, comparisons, methodology,
environment, limitations, and unresolved risks are understandable without chat
history. This task consolidates evidence without rewriting it.

## Knowledge Covered

- Evidence-chain and hash validation.
- Cross-backend functional/performance reporting.
- Reproducible build/run documentation.
- Acceptance-matrix design.
- Honest scope and limitation statements.

## Scope

Create a new order-balanced, six-round benchmark campaign for Python ORT, C++
ORT, and C++ ncnn without changing the approved Task 009/011 campaigns. Run one
fresh representative single-image inference for each backend, validate all three
against frozen comparisons, generate the benchmark and acceptance summaries,
update README/roadmap/changelog accurately, and complete Checkpoint C.

Do not change implementations, models, manifests, golden results, thresholds,
comparison tolerances, benchmark measurements/method, completed-task evidence, or
claim any ARM/board-stage completion.

## Allowed Files

```text
configs/benchmark_pc_three_backend.json
TASKS.md
tasks/012_pc_stage_acceptance.md
README.md
ROADMAP.md
CHANGELOG.md
docs/pc_stage_acceptance.md
scripts/generate_pc_acceptance.py
tests/python/test_pc_acceptance.py
results/acceptance/python_ort_reference.png
results/acceptance/python_ort_reference.json
results/acceptance/cpp_ort_reference.png
results/acceptance/cpp_ort_reference.json
results/acceptance/cpp_ncnn_reference.png
results/acceptance/cpp_ncnn_reference.json
results/benchmarks/pc_three_backend_python_ort.json
results/benchmarks/pc_three_backend_cpp_ort.json
results/benchmarks/pc_three_backend_cpp_ncnn.json
results/benchmarks/pc_three_backend_summary.json
results/benchmarks/pc_three_backend_summary.csv
results/evidence/012/three_backend_benchmark_validation.json
results/evidence/012/pc_acceptance.json
results/logs/012_pc_acceptance.log
```

All implementation, model, fixture, Task 002–011 evidence, and source benchmark
JSON files are read-only inputs. Build directories are ignored and reproducible.

## Forbidden Files

- Any Python/C++ inference implementation or CMake change.
- Model, manifest, converted artifact, fixed image/video, config, golden, tolerance,
  or existing benchmark/evidence change.
- New inference result presented as a replacement for completed-task evidence.
- ARM/Anlogic implementation or claim, new backend, download, dependency install,
  fabricated example, or hand-edited performance value.
- Any file outside Allowed Files.

## Inputs

- Completed Task 002–011 task records and preserved artifacts.
- Frozen model/image/config hashes and comparison tolerances.
- The approved Task 009 and Task 011 benchmark JSON as immutable historical
  evidence. They are not inputs to the Task 012 primary performance table.
- A new Task 012 six-round order-balanced campaign using the same fixed
  methodology, environment, model lineage, input, thresholds, and stage
  boundaries.
- Existing compatible Python, OpenCV, ONNX Runtime, ncnn, CMake, compiler, and
  Ninja environment.

Any missing, changed, incompatible, or unauthenticated evidence requires a stop;
do not recreate old evidence silently.

## Expected Outputs

- A complete README for Python ORT, C++ ORT, and C++ ncnn on PC.
- Three new 600-sample raw benchmark JSON files, a generated three-backend
  summary JSON/CSV, and machine validation based only on the Task 012 campaign.
- Fresh annotated reference image and structured detections for all three paths.
- `pc_stage_acceptance.md` with environment, commands, output links, differences,
  benchmark boundaries, limitations, risk register, and acceptance matrix.
- Machine-readable acceptance JSON and real validation log.

## Implementation Requirements

- Validate that Tasks 001–011 are `Completed`, required checkpoints A/B were
  human-approved, and every referenced artifact/hash exists and agrees with its
  immutable task record.
- Preserve the approved Task 009 and Task 011 raw JSON/CSV byte-for-byte. Never
  run their campaigns again, append to them, or use their filenames as Task 012
  outputs.
- Launch six independent processes per backend in this exact full-permutation
  order: `python_ort/cpp_ort/cpp_ncnn`,
  `python_ort/cpp_ncnn/cpp_ort`, `cpp_ort/python_ort/cpp_ncnn`,
  `cpp_ort/cpp_ncnn/python_ort`, `cpp_ncnn/python_ort/cpp_ort`, and
  `cpp_ncnn/cpp_ort/python_ort`. Each backend must occur twice in each position.
- Each process reads the image once, loads its model/runtime, records
  `model_load_ms`, runs 10 untimed warmups, and preserves 100 measured complete
  pipelines. Each backend therefore has exactly 6 rounds and 600 samples.
- Existing Task 009/011 per-process executables remain read-only. The Task 012
  orchestrator may invoke each against a fresh one-round temporary fragment and
  embed the complete unmodified process payload in the new campaign JSON while
  assigning outer campaign round, sequence, and position metadata. This avoids
  changing completed implementation while preserving every raw sample.
- Generate, never hand-enter, the final performance table from the three new
  Task 012 raw JSON files. Reject method/config/environment/hash mismatch.
- The table must include Python ORT, C++ ORT, and C++ ncnn and show preprocess,
  inference, postprocess, pipeline-total mean/P50/P90/min/max, defined pipeline
  FPS, peak memory, CPU-utilization metric, threads, warmup, and repeat.
- Label all units and repeat the exact FPS/stage-boundary definitions. Produce
  per-round and aggregate nearest-rank mean/P50/P90/min/max, model-load/resource
  records, fastest/slowest sample identities, six-round mean spread, and grouped
  position-1/2/3 means plus position-mean spread.
- Require each backend's six-round pipeline-mean spread to be at most 10 percent.
  Preserve every outlier; never selectively rerun or replace a process.
- Require untimed correctness before and after every process. ORT uses its frozen
  golden tolerances. ncnn must reach target IoU `>= 0.99` and confidence delta
  `<= 0.01`; hard-floor-only results require an immediate human stop and may not
  support a performance conclusion.
- Run fresh reference-image inference for all three backends into Task 012 paths;
  do not overwrite completed-task evidence.
- Validate fresh detections against frozen references/tolerances and require human
  visual review of the three output images.
- README must include project/current PC status, frozen model/version/SHA, input
  contract, environment/dependencies, exact build commands, exact run commands,
  output examples, result differences, benchmark methodology, real performance
  table or generated link, known limitations, and evidence/report links.
- README and acceptance report must say Stage 2 Anlogic DR1 ARM is planned and
  unimplemented; never imply ARM performance or deployment exists.
- Acceptance matrix must cover Tasks 001–012 with actual evidence path, command or
  check, pass/fail state, and human-review state. No row may be marked passed from
  static inspection alone.
- Record unresolved risks without converting them into success claims.
- The generator must fail on missing fields/files, hash drift, non-finite metrics,
  schema mismatch, incomplete comparisons, unapproved checkpoints, or inconsistent
  task status.

## Build Commands

```bash
python3 -m py_compile \
  scripts/generate_pc_acceptance.py \
  tests/python/test_pc_acceptance.py
rm -rf build/pc-acceptance-release
cmake \
  -S cpp \
  -B build/pc-acceptance-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root> \
  -DNCNN_ROOT=<verified-local-ncnn-root>
cmake --build build/pc-acceptance-release --parallel
```

## Run Commands

```bash
mkdir -p \
  results/acceptance \
  results/benchmarks \
  results/evidence/012 \
  results/logs

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

PYTHONPATH=python .venv/bin/python scripts/generate_pc_acceptance.py run-campaign \
  --config configs/benchmark_pc_three_backend.json \
  --base-config configs/benchmark_pc.json \
  --python .venv/bin/python \
  --python-benchmark python/apps/benchmark_ort.py \
  --cpp-ort build/pc-acceptance-release/edgeai_benchmark_ort \
  --cpp-ncnn build/pc-acceptance-release/edgeai_benchmark_ncnn \
  --ncnn-manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --reference-detections results/evidence/007/cpp_ort_detections.json \
  --python-output results/benchmarks/pc_three_backend_python_ort.json \
  --cpp-ort-output results/benchmarks/pc_three_backend_cpp_ort.json \
  --cpp-ncnn-output results/benchmarks/pc_three_backend_cpp_ncnn.json \
  --summary results/benchmarks/pc_three_backend_summary.json \
  --csv results/benchmarks/pc_three_backend_summary.csv \
  --validation results/evidence/012/three_backend_benchmark_validation.json \
  --log results/logs/012_pc_acceptance.log

PYTHONPATH=python .venv/bin/python python/apps/ort_image.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/acceptance/python_ort_reference.png \
  --output-json results/acceptance/python_ort_reference.json
./build/pc-acceptance-release/edgeai_ort_image \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/acceptance/cpp_ort_reference.png \
  --output-json results/acceptance/cpp_ort_reference.json
./build/pc-acceptance-release/edgeai_ncnn_image \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/acceptance/cpp_ncnn_reference.png \
  --output-json results/acceptance/cpp_ncnn_reference.json
PYTHONPATH=python .venv/bin/python scripts/generate_pc_acceptance.py generate-report \
  --config configs/benchmark_pc_three_backend.json \
  --tasks tasks \
  --benchmark-inputs \
    results/benchmarks/pc_three_backend_python_ort.json \
    results/benchmarks/pc_three_backend_cpp_ort.json \
    results/benchmarks/pc_three_backend_cpp_ncnn.json \
  --benchmark-summary results/benchmarks/pc_three_backend_summary.json \
  --benchmark-validation results/evidence/012/three_backend_benchmark_validation.json \
  --fresh-results \
    results/acceptance/python_ort_reference.json \
    results/acceptance/cpp_ort_reference.json \
    results/acceptance/cpp_ncnn_reference.json \
  --image-paths \
    results/acceptance/python_ort_reference.png \
    results/acceptance/cpp_ort_reference.png \
    results/acceptance/cpp_ncnn_reference.png \
  --acceptance-json results/evidence/012/pc_acceptance.json \
  --acceptance-report docs/pc_stage_acceptance.md \
  --readme README.md
```

## Test Commands

```bash
set -o pipefail
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
ctest --test-dir build/pc-acceptance-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest tests/python/test_pc_acceptance.py
.venv/bin/python -m json.tool results/evidence/012/pc_acceptance.json >/dev/null
.venv/bin/python -m json.tool results/benchmarks/pc_three_backend_python_ort.json >/dev/null
.venv/bin/python -m json.tool results/benchmarks/pc_three_backend_cpp_ort.json >/dev/null
.venv/bin/python -m json.tool results/benchmarks/pc_three_backend_cpp_ncnn.json >/dev/null
.venv/bin/python -m json.tool results/benchmarks/pc_three_backend_summary.json >/dev/null
.venv/bin/python -m json.tool results/evidence/012/three_backend_benchmark_validation.json >/dev/null
test -s results/acceptance/python_ort_reference.png
test -s results/acceptance/cpp_ort_reference.png
test -s results/acceptance/cpp_ncnn_reference.png
git diff --check
```

## Acceptance Criteria

- All Task 001–011 records/evidence validate without modifying prior evidence,
  and the approved Task 009/011 campaign hashes remain unchanged.
- Release build and complete Python/C++ test suites pass in the recorded environment.
- Fresh Python ORT, C++ ORT, and C++ ncnn runs succeed on identical frozen inputs.
- Fresh detection comparisons pass the already frozen tolerances.
- All three output images are nonempty/decodable and receive human visual review.
- The new campaign follows all six approved backend permutations with 18
  independent processes, 600 samples per backend, two appearances per position,
  complete before/after correctness, exact stage sums, and all outliers retained.
- Generated performance table contains all three backends and every required real
  metric/settings/environment/position field; no number was typed or inferred
  manually and no Task 009/011 number substitutes for Task 012 data.
- README contains the real PC environment, builds, runs, outputs, differences,
  performance/method, limitations, and evidence links.
- Acceptance matrix has an auditable real check/evidence and accurate state for
  every Task 001–012 row.
- No completed evidence, model/config/golden, code, tolerance, or benchmark source
  was changed.
- Documentation explicitly says ARM/Anlogic Stage 2 is not implemented.
- Tests, generator, artifact validation, and `git diff --check` pass with only
  Allowed Files changed.
- Unresolved risks are listed; Checkpoint C is presented; Codex then stops.

## Evidence to Preserve

Validated task/evidence hashes, actual environment and dependency versions,
Release build/tests, fresh commands/detections/images and cross-checks, all 1,800
new raw samples, process order/position metadata, generated three-backend
CSV/JSON, benchmark method and source hashes, acceptance matrix, human
visual/performance/checkpoint decisions, attempts, and final Git status.

## Automatic Retry Rules

At most three complete repair loops may fix only report-generator, acceptance-test,
or documentation defects in Allowed Files. Never repair by altering implementation,
old evidence, model/config/golden, tolerances, benchmark inputs, or measured values.
Such a need is an immediate stop and requires reopening the owning task explicitly.

## Human Stop Conditions

Stop for any missing/drifted evidence, incomplete prior approval, build/test/run
failure owned by an earlier task, fresh-result mismatch, hard-floor-only or failed
ncnn comparison, campaign interruption, incomplete samples, six-round spread over
10 percent, image judgment, performance interpretation, benchmark inconsistency,
proposed ARM claim, or protocol condition. The first complete candidate campaign
must stop for human performance review before Task 012 can be completed. Task
completion triggers mandatory Checkpoint C and no automatic Stage 2 work.

## Codex Responsibilities

Validate rather than rewrite history, generate tables from real inputs, run fresh
representative paths, keep documentation accurate, assemble Checkpoint C, and stop.

## User Responsibilities

Review three output images, performance table/method, complete README, acceptance
matrix, and risks; approve or reject Checkpoint C; decide separately whether and
how Stage 2 begins.

## Known Risks

- Old evidence may have been moved, ignored, or generated under a changed system.
- Documentation can become stale if commands or paths drift.
- Three-backend numbers are valid only for the recorded PC environment/method.
- PC acceptance does not predict ARM compatibility or performance.

## Completion Report Format

Report files, evidence validation, environment/build/tests, three fresh inference
results and visual review, generated performance table/method/source hashes,
README sections, acceptance matrix, unresolved risks, attempts/skips, Checkpoint C,
and final Git status. Explicitly state that ARM remains unimplemented and stop.

## Execution Record

Started: `2026-07-22T10:30:12+08:00`

Branch: `feature/pc-batch-c-ncnn-acceptance`

Starting commit: `59e4450` (`feat(ncnn): add image video and benchmark inference`)

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output). Tasks 001–011 are `Completed`; Task 009 records Checkpoint B approval,
and Task 010/011 local atomic commits are present.

The user approved a new Task 012 primary benchmark contract that supersedes the
old cross-campaign table plan without changing any completed evidence. It uses
six full permutations, 18 independent processes, warmup 10 and repeat 100 per
process, 600 samples per backend, fixed WSL2 CPU/FP32/thread settings, exact stage
boundaries, nearest-rank statistics, position-effect reporting, and a 10 percent
stability gate. The existing Task 009 and Task 011 campaign files are immutable.

Startup audit verified the required branch and clean worktree. The fixed model,
input, SDK, and historical campaign hashes matched their completed records.
Python is 3.12.3 with ONNX Runtime 1.18.1 and CPUExecutionProvider; CMake is
3.28.3, Ninja 1.11.1, GCC 13.3.0, Python OpenCV 4.10.0, and C++ OpenCV 4.6.0.
The approved local ORT SDK and ncnn 20240410 runtime/package are present with no
missing dynamic dependency. No benchmark process has run and no Task 012 result
has been generated at this state transition.

Two `apply_patch` invocations failed atomically while updating this contract
because their expected context did not match the real Allowed Files/Run Commands
text. They changed no file. The update was split against the observed content and
applied successfully; these were editing-orchestration errors, not build, test,
inference, or benchmark attempts.

### Pre-Campaign Implementation and Validation

The Task 012 outer configuration, campaign/acceptance generator, and focused
tests were added without changing any Python/C++ inference implementation or
CMake file. The orchestrator launches the completed backend programs as 18
independent child processes. Because those per-process programs intentionally
freeze Task 009's aggregate round count, each child writes one fresh source-round
fragment with the unchanged 10/100 process contract. Task 012 embeds the complete
parsed payload plus fragment and canonical-payload SHA256, and assigns only outer
campaign round, sequence, and position metadata. It never rewrites stage values,
correctness, environment, CPU/RSS, model load, or samples.

Focused validation passed 6/6 tests. It covers configuration and position
balance, all three existing process schemas, 600-sample aggregation, 200 samples
per position, nearest-rank summaries, exact stage-sum rejection, LF CSV output,
and the absence of any ARM-completion claim. `py_compile`, `git diff --check`,
and the current Allowed Files audit passed.

The complete Release configuration used GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1,
OpenCV 4.6.0, ONNX Runtime 1.18.1, and ncnn 1.0.20240410. Configuration and all
39 build steps exited zero with no project warning. CTest passed 12/12 and the
full Python unittest discovery passed 64/64.

Fresh Task 012 single-image inference ran on the identical frozen input and new
output paths. All backends produced the same five detections and classes. Python
ORT versus C++ ORT passed with minimum class-matched IoU
`0.999999982537` and maximum confidence delta `1.64833068306e-08`. C++ ORT
versus C++ ncnn reached `PASS_TARGET` with IoU `0.999997080011` and delta
`2.02655792236e-06`. All three decoded PNGs are 1280x960 and have SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.
Each is pixel-for-pixel identical to its previously human-approved backend image,
so no new visual difference was introduced; Checkpoint C still retains final
human image review.

Fresh JSON SHA256 values before the campaign:

```text
Python ORT: 2e005e95e229368bf8b415aa4f162e03a3a75d0b128cec4db94a9ba9d3fa79f3
C++ ORT:    3c4f8b3890f3066ac7212bf60d3c44c0f18637c41f4663c20c4eccc0371b4db5
C++ ncnn:   fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9
```

All six immutable Task 009/011 campaign hashes were rechecked immediately before
formal execution and matched the Task 012 config. No formal Task 012 sample had
been generated at this point.

### First Order-Balanced Candidate Campaign

Stopped: `2026-07-22T10:49:38+08:00`

The Task 012 campaign ran exactly once from empty new output paths. All 18
independent processes exited zero in the approved order:

```text
Round 1: Python ORT -> C++ ORT -> C++ ncnn
Round 2: Python ORT -> C++ ncnn -> C++ ORT
Round 3: C++ ORT -> Python ORT -> C++ ncnn
Round 4: C++ ORT -> C++ ncnn -> Python ORT
Round 5: C++ ncnn -> Python ORT -> C++ ORT
Round 6: C++ ncnn -> C++ ORT -> Python ORT
```

Each backend appears twice in each position. Every process read the fixed image
once, loaded the fixed model/runtime, recorded model load, completed 10 excluded
warmups, and retained 100 full preprocess/inference/postprocess samples. Each
backend therefore has 6 process rounds and 600 formal samples. All 1,800 samples,
minima, maxima, and outliers remain present. All 36 before/after correctness
checks passed: ORT reports `PASS` and ncnn reports `PASS_TARGET`.

Candidate aggregate results generated from the raw nanosecond samples:

```text
backend     pipeline mean  P50        P90        min        max        FPS        round spread  position spread
python_ort  54.881306 ms   54.640382  56.898155  51.590660  65.453303  18.221141  3.098913%     1.156671%
cpp_ort     51.802986 ms   51.595426  53.627128  48.863992  65.671301  19.303907  3.221212%     1.383173%
cpp_ncnn    77.865349 ms   77.618684  80.776143  73.478461  85.075339  12.842683  1.727134%     0.438557%
```

Aggregate stage means:

```text
backend     preprocess  inference   postprocess  pipeline
python_ort  3.356562    45.898201   5.626543     54.881306 ms
cpp_ort     1.833570    45.849137   4.120279     51.802986 ms
cpp_ncnn    1.815537    71.941530   4.108283     77.865349 ms
```

Position-group pipeline means, each based on 200 samples:

```text
backend     position 1  position 2  position 3
python_ort  54.472042   55.102104   55.069772 ms
cpp_ort     52.163539   51.451871   51.793547 ms
cpp_ncnn    77.956484   77.649513   77.990051 ms
```

All three six-round stability gates pass the approved 10 percent limit. The
candidate CPU measurements are approximately 99.94–100.00 percent on the
`process_cpu_percent_one_core_basis`; they are preserved without correction.
Peak RSS ranges are 178225152–181420032 bytes for Python ORT,
153935872–155078656 bytes for C++ ORT, and 187768832–188178432 bytes for C++
ncnn. These are complete process peaks, not model-only memory.

The fastest/slowest preserved pipeline samples are:

```text
python_ort: aggregate 140 (round 2, position 1, iteration 40) 51.590660 ms;
            aggregate 70 (round 1, position 1, iteration 70) 65.453303 ms
cpp_ort:    aggregate 62 (round 1, position 2, iteration 62) 48.863992 ms;
            aggregate 503 (round 6, position 2, iteration 3) 65.671301 ms
cpp_ncnn:   aggregate 3 (round 1, position 3, iteration 3) 73.478461 ms;
            aggregate 202 (round 3, position 3, iteration 2) 85.075339 ms
```

New candidate evidence SHA256 values:

```text
Python ORT raw: 7cf24818fe722a7c1ecc169a2f458f66a4f903b3cf0499cde8ae95fd7731390e
C++ ORT raw:    a047eee174b7ae355613c6f3f95bfac3c2d681467cd16333de1b8d3261bad085
C++ ncnn raw:   64ec3a8a9e7c3b9ed4c89e3a7836b9caa349dfa7325af24a8bf1401e38f2fc7c
summary JSON:   e0419a12a4f9e3e2d815733c26566e5af5f878d585ffd1be4437d47144376126
summary CSV:    a14e66928dc7f89181e240ca8873175a293cc23f06f0c212893ad3260861eb9a
validation:     f50c139fef074c11bff5879ab6cd49a26097843800d523ee409f77c1c20550a8
campaign log:   40ac3ada6b1e107fad1a5e3f62d5ba228964c1e997eb1223777402cb3e5215bf
```

The immutable Task 009/011 hashes remained exactly unchanged after the campaign.
An independent re-derivation under `build/task012-deterministic-audit` validated
all 18 source-fragment hashes and embedded canonical payloads, all 1,800 exact
stage sums, process order, positions, correctness, resources, and statistics.
The regenerated summary JSON and CSV were byte-for-byte equal to repository
outputs; the validation document was semantically equal after excluding only its
temporary derived-output paths. The CSV contains 120 data rows.

No Task 009 or Task 011 benchmark was rerun. No Task 012 process or round was
selectively rerun, replaced, removed, or adjusted. README, ROADMAP, CHANGELOG,
the final acceptance JSON/report, Task completion, staging, and commit remain
unperformed because the user required an immediate stop after the first complete
candidate campaign.

### Candidate Performance Human-Review Blocking Report

```text
Current Task: Task 012, PC-stage comparison, README, and acceptance report
Current Status: Blocked
Last Successful Step: the first complete 18-process, six-round, order-balanced campaign and independent deterministic validation passed with 600 samples per backend and all stability/correctness gates passing
Failed Command: none; the candidate campaign and every automatic validation command exited zero
Exit Code: 0 for all 18 benchmark processes, campaign aggregation, JSON parsing, hash checks, and deterministic re-derivation
Relevant Error: no execution error; the first real three-backend performance data requires the user-mandated human review before documentation may present it as the final PC result
Files Changed: TASKS.md; tasks/012_pc_stage_acceptance.md; configs/benchmark_pc_three_backend.json; scripts/generate_pc_acceptance.py; tests/python/test_pc_acceptance.py; six results/acceptance image/JSON files; three new raw campaign JSON files; results/benchmarks/pc_three_backend_summary.json; results/benchmarks/pc_three_backend_summary.csv; results/evidence/012/three_backend_benchmark_validation.json; ignored results/logs/012_pc_acceptance.log
Attempts Made: 0 benchmark repair attempts and no selective rerun; two earlier apply_patch context mismatches changed no file and are recorded as editing-orchestration errors
Why Automatic Recovery Is Unsafe: accepting backend differences, outliers, order effects, WSL2 CPU/RSS values, and the final interpretation is an explicit human performance gate; continuing would generate the final README and acceptance conclusion before that decision
Exact Human Action Required: review the three raw JSON files, summary JSON/CSV, validation JSON, campaign log, aggregate/stage/position tables above, all min/max samples, six-round stability, approximately 100% process CPU values, process-level RSS scope, model relationship, and the three pixel-identical fresh images; explicitly approve this exact candidate or reject it with a reason requiring a full Round-1 restart under a separately authorized evidence-preservation plan
Commands to Resume: repeat branch/status/protocol/Task 012 audit; verify the seven new hashes and six immutable Task 009/011 hashes; rerun deterministic derivation only against the unchanged raw Task 012 JSON without launching a benchmark process; after explicit approval restore Task 012 to In Progress, generate README/docs/acceptance JSON from the approved files, update ROADMAP/CHANGELOG, rerun all tests/checks, mark Completed, create the prescribed local atomic commit, and stop at Checkpoint C
Git Status: only Task 012 Allowed Files are modified or untracked; the build/audit directories and campaign log are ignored; nothing is staged or committed
```

### Approved Campaign Recovery

Resumed: `2026-07-22`

The user approved the exact first Task 012 campaign as the final PC-stage
benchmark result. Approval covers all 18 independent processes, the full six-
permutation order, 10 warmups and 100 measured iterations per process, 600
samples per backend, all 1,800 retained samples and outliers, all correctness
checks, all three stability gates, process-level CPU/RSS definitions, WSL2 and
OpenCV-version limitations, and the distinct ORT/ncnn serialized-model lineage.
No benchmark process may be rerun and no approved raw or derived campaign file
may be modified.

Recovery reverified the seven approved SHA256 values exactly, including the
ignored campaign log. The six Task 009/011 historical campaign hashes also
remain unchanged. A deterministic re-derivation from the three unchanged raw
Task 012 JSON files produced a byte-identical summary JSON and CSV and a
semantically identical validation report after normalizing only the temporary
derived-output paths. It reconfirmed 18 process identities, the approved order,
600 samples per backend, exact stage sums, `PASS_TARGET` correctness, and all
round/position spread values.

One initial read-only comparison assertion exited `1` because the audit script
compared the repository and temporary derived-output filenames as semantic
content. The generated summary JSON and CSV were already byte-identical. The
check was corrected to normalize only those derived-output paths and then
passed; no source, raw sample, summary, validation, image, or log was modified.
This was an audit-orchestration error, not a benchmark or product repair.

Task 012 is restored to `In Progress` only to generate the approved final README,
acceptance report, and machine-readable acceptance candidate; update the
roadmap/changelog; and rerun non-benchmark build, tests, schema, documentation,
Allowed Files, and Git checks. The existing campaign log remains immutable, so
the report command no longer appends to it. Final README, acceptance matrix,
risks, and image presentation remain the explicit Checkpoint C documentation
review. Task 012 must stop before staging or commit for that review, and Stage 2
must not start.

### Final Documentation Validation and Checkpoint C Stop

Stopped: `2026-07-22`

The approved benchmark was not rerun, overwritten, filtered, or edited during
recovery. The final report generator produced README, the PC acceptance report,
and machine-readable acceptance evidence from the unchanged approved files.
ROADMAP and CHANGELOG now describe the real PC status without claiming Task 012,
Checkpoint C, or ARM completion.

Repair attempt 1:

```text
Failure: the focused generated-Markdown test failed because the literal phrase "Stage 2" was split across a template line break
Root Cause: the Current status source line wrapped between "Stage" and "2"; the rendered meaning was correct but the required explicit phrase was absent
Files Modified: scripts/generate_pc_acceptance.py
Fix Applied: place "Stage 2" together on one line without changing the status meaning or any measured value
Commands Re-run: py_compile; all 6 focused Task 012 unittests; report generation; later the complete 64-test Python suite and documentation checks
Result: PASS; 6/6 focused tests and 64/64 full Python tests passed
```

Two additional large `apply_patch` attempts during recovery failed atomically
because escaped-backslash or task-tail context did not match the real files.
They changed no file; smaller patches against observed boundaries succeeded.
Together with the two pre-campaign context mismatches, Task 012 has four recorded
editing-context mismatches. They are not benchmark or product repair attempts.

Fresh completion validation, without formal benchmark execution:

```text
Release configure/build: PASS; CMake 3.28.3, GCC 13.3.0, Ninja 1.11.1,
  C++ OpenCV 4.6.0, ONNX Runtime 1.18.1, ncnn 1.0.20240410; 39/39 build steps;
  no project warning
CTest: 12/12 PASS
Python unittest discovery: 64/64 PASS
Task 012 focused Python tests: 6/6 PASS
JSON parse checks: PASS
CSV: 120 data rows, LF, expected round/position/aggregate structure PASS
raw samples: 600 per backend, 1,800 total, exact stage sum PASS
Markdown fences, relative links, bash syntax, required paths and claims: PASS
Allowed Files: PASS; exactly 22 modified or untracked paths
tracked and untracked whitespace checks: PASS
git diff --check: PASS
```

Three new non-benchmark single-image audit runs wrote only under the ignored
`build/task012-runtime-audit` directory. They reproduced five detections per
backend, Python/C++ ORT `PASS` at IoU `0.999999982537` and confidence delta
`1.64833068306e-08`, and ORT/ncnn `PASS_TARGET` at IoU `0.999997080011` and
delta `2.02655792236e-06`. Their three PNGs reproduced the approved SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.
The printed timings were explicitly diagnostic and were not recorded as formal
benchmark data.

```text
Current Task: Task 012, PC-stage comparison, README, and acceptance report
Current Status: Blocked
Last Successful Step: approved benchmark evidence was deterministically revalidated; final README, acceptance report, machine-readable matrix, roadmap, changelog, Release build, runtime audits, tests, schema/CSV/Markdown/Allowed Files/Git checks all passed
Failed Command: none; the task reached its explicit final README/acceptance-matrix/risk human review checkpoint
Exit Code: N/A; the human stop follows successful automatic commands
Relevant Error: no product or evidence error; final documentation and Checkpoint C approval remain a human decision
Files Changed: exactly the 22 Task 012 Allowed Files shown by git status; the approved campaign log and ignored build audit outputs are not staged
Attempts Made: 1 completed documentation repair loop; 0 benchmark repair attempts and no benchmark rerun; 4 atomic apply_patch context mismatches across Task 012 changed no files
Why Automatic Recovery Is Unsafe: marking Task 012 Completed and committing before the user reviews the complete README, acceptance matrix, risk wording, output presentation, and Checkpoint C package would bypass the task's explicit User Responsibilities and the user's current instruction
Exact Human Action Required: review README.md and docs/pc_stage_acceptance.md; confirm the final performance/stage/position/resource tables, model-lineage wording, reproduction commands, acceptance matrix, limitations, unresolved risks, image references, and that Stage 2 remains unimplemented; explicitly approve final Task 012 documentation and Checkpoint C
Commands to Resume: repeat branch/status/protocol/Task 012 audit; verify all seven approved campaign hashes plus immutable Task 009/011 hashes; do not run any benchmark; restore Task 012 to In Progress after explicit approval; regenerate only the report/matrix if needed; rerun focused/full tests and Git checks; mark Completed; stage only the explicit 22 Allowed Files; run cached diff checks; create the prescribed local atomic commit; stop without starting Stage 2
Git Status: Task 012 Allowed Files only; nothing staged or committed; Task 009/011 evidence and all approved Task 012 benchmark files retain their recorded hashes
```

### Final Documentation and Checkpoint C Approval Recovery

Resumed: `2026-07-22T11:29:58+08:00`

The user approved the final README, PC acceptance report, machine-readable
acceptance evidence, remaining Task 012 Allowed Files, and Checkpoint C. The
approval confirms the final three-backend performance interpretation,
correctness conclusions, model-lineage wording, resource definitions,
limitations, and the explicit boundary that Stage 2 ARM remains planned and
unimplemented. This approval does not authorize Task 013 or any ARM work.

Recovery verified the branch, empty staging area, and exactly 22 changed or
untracked Task 012 Allowed Files. The seven approved Task 012 evidence SHA256
values, including the ignored campaign log, matched their recorded identities.
All four immutable Task 009 evidence hashes and all four immutable Task 011
evidence hashes also matched. No benchmark process was launched and no approved
sample, summary, validation file, image, or log was modified.

A deterministic re-derivation from the three unchanged raw Task 012 JSON files
produced a byte-identical summary JSON and CSV and a semantically identical
validation document after normalizing only its temporary derived-output paths.
It reconfirmed 600 samples per backend and the approved pipeline statistics,
round spreads, and position spreads.

One initial read-only summary-printing assertion exited nonzero after all three
derived-file comparisons had already passed because it looked for sample count
under `aggregate.sample_count` instead of the actual top-level `sample_count`.
The repository schema was inspected and the complete deterministic audit was
rerun successfully with the correct path. This changed only ignored files under
`build/task012-final-deterministic-audit`; it did not change product code or any
formal evidence and is recorded as an audit-orchestration error rather than a
benchmark or product repair.

Task 012 is restored to `In Progress` only to encode the approved final state,
run the required non-benchmark build/test/document checks, transition to
`Completed`, create the authorized local atomic commit, and stop at Checkpoint C.

### Final Completion Record

Completed: `2026-07-22T11:38:19+08:00`

The final README, acceptance report, machine-readable matrix, and Checkpoint C
approval are recorded. Tasks 001–012 are `Completed`, PC Stage 1 is complete,
and Stage 2 remains `Not implemented / Planned`; Task 013 was not started.

No formal benchmark command was run during this recovery. No Task 009, Task 011,
or Task 012 raw sample, summary, CSV, validation document, or campaign log was
overwritten, edited, filtered, or selectively rerun. A new single-image run was
also not required in this recovery: the Task 012 fresh runs and their later
non-benchmark runtime audit are already real, recorded, hash-verified, and
human-approved. The completion checks reused those immutable results rather than
creating timing-bearing replacements.

Final environment and build verification:

```text
Release configure: PASS; CMake 3.28.3, GCC 13.3.0, Ninja generator,
  C++ OpenCV 4.6.0, ONNX Runtime 1.18.1, ncnn 1.0.20240410
Release build: PASS; 39/39 steps; no project warning
CTest: 12/12 PASS
Python unittest discovery: 64/64 PASS
Task 012 focused unittest: 6/6 PASS
py_compile: PASS
JSON parse and CSV validation: PASS; 120 CSV data rows
raw campaign reconstruction: PASS; 6 rounds/backend, 600 samples/backend,
  1,800 total samples, exact integer-nanosecond stage sums
deterministic derivation: summary JSON/CSV byte-identical; validation
  semantically identical after normalizing only temporary output paths
Markdown fences, README Bash syntax, command paths, required claims, and
  prohibited-claim checks: PASS
Allowed Files: PASS; exactly 22 changed or untracked paths
staging area before local commit: empty
git diff --check: PASS
```

Approved Task 012 evidence remained byte-identical:

```text
Python ORT raw: 7cf24818fe722a7c1ecc169a2f458f66a4f903b3cf0499cde8ae95fd7731390e
C++ ORT raw: a047eee174b7ae355613c6f3f95bfac3c2d681467cd16333de1b8d3261bad085
C++ ncnn raw: 64ec3a8a9e7c3b9ed4c89e3a7836b9caa349dfa7325af24a8bf1401e38f2fc7c
summary JSON: e0419a12a4f9e3e2d815733c26566e5af5f878d585ffd1be4437d47144376126
summary CSV: a14e66928dc7f89181e240ca8873175a293cc23f06f0c212893ad3260861eb9a
validation JSON: f50c139fef074c11bff5879ab6cd49a26097843800d523ee409f77c1c20550a8
campaign log: 40ac3ada6b1e107fad1a5e3f62d5ba228964c1e997eb1223777402cb3e5215bf
```

All four Task 009 immutable hashes and all four Task 011 immutable hashes also
matched their completed records immediately before final staging.

#### Repair Attempt 2: final ARM-status wording

```text
Failure: the first focused generated-Markdown test in final recovery failed
Root Cause: the words "has not been implemented" were split across a source-template line break, so the exact test phrase was absent even though the rendered meaning and `Not implemented / Planned` status were correct
Files Modified: scripts/generate_pc_acceptance.py
Fix Applied: keep the no-ARM-completion sentence contiguous and retain the explicit `Not implemented / Planned` status without changing any measured value
Commands Re-run: py_compile; focused 6-test suite; git diff --check; final Release/CTest/full-unittest/document/schema/Allowed-Files checks
Result: PASS; focused 6/6, full Python 64/64, CTest 12/12, and every final document/evidence check passed
```

Two subsequent read-only document-audit assertions used exact strings without
normalizing Markdown line wrapping for the WSL2/bare-metal and PC-stage-complete
phrases. Named diagnostic output showed that the required statements were
present across line boundaries; the audit was corrected to normalize whitespace
and the complete check passed. These assertions changed no repository file or
evidence and are audit-orchestration errors, not additional product repairs.

Every Acceptance Criterion and the Checkpoint C human decision now pass. The
authorized local atomic commit is created after explicit 22-path staging,
cached whitespace/stat/diff review, and is reported to the user after Git assigns
its SHA. No push, PR, merge, rebase, branch change, Task 013, or ARM work follows.
