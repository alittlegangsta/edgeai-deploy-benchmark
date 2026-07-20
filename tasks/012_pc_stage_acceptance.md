# Task 012

## Title

Complete the PC-stage comparison, README, and acceptance report.

## Status

Planned

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

Create a generated PC acceptance summary from completed Tasks 002–011, run one
fresh representative single-image inference for each backend, validate all three
against frozen comparisons, update README/roadmap/changelog accurately, and
complete Checkpoint C.

Do not change implementations, models, manifests, golden results, thresholds,
comparison tolerances, benchmark measurements/method, completed-task evidence, or
claim any ARM/board-stage completion.

## Allowed Files

```text
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
results/benchmarks/pc_all_summary.csv
results/evidence/012/pc_acceptance.json
results/logs/012_pc_acceptance.log
```

All implementation, model, fixture, Task 002–011 evidence, and source benchmark
JSON files are read-only inputs. Build directories are ignored and reproducible.

## Forbidden Files

- Any Python/C++ implementation or CMake change.
- Model, manifest, converted artifact, fixed image/video, config, golden, tolerance,
  or existing benchmark/evidence change.
- New inference result presented as a replacement for completed-task evidence.
- ARM/Anlogic implementation or claim, new backend, download, dependency install,
  fabricated example, or hand-edited performance value.
- Any file outside Allowed Files.

## Inputs

- Completed Task 002–011 task records and preserved artifacts.
- Frozen model/image/config hashes and comparison tolerances.
- Approved benchmark JSON from Python ORT, C++ ORT, and C++ ncnn produced in one
  valid methodology/environment chain.
- Existing compatible Python, OpenCV, ONNX Runtime, ncnn, CMake, compiler, and
  Ninja environment.

Any missing, changed, incompatible, or unauthenticated evidence requires a stop;
do not recreate old evidence silently.

## Expected Outputs

- A complete README for Python ORT, C++ ORT, and C++ ncnn on PC.
- A generated three-backend performance CSV based only on real benchmark JSON.
- Fresh annotated reference image and structured detections for all three paths.
- `pc_stage_acceptance.md` with environment, commands, output links, differences,
  benchmark boundaries, limitations, risk register, and acceptance matrix.
- Machine-readable acceptance JSON and real validation log.

## Implementation Requirements

- Validate that Tasks 001–011 are `Completed`, required checkpoints A/B were
  human-approved, and every referenced artifact/hash exists and agrees with its
  immutable task record.
- Generate, never hand-enter, the performance table from Task 009 Python/C++ ORT
  and Task 011 C++ ncnn JSON. Reject method/config/environment/hash mismatch.
- The table must include Python ORT, C++ ORT, and C++ ncnn and show preprocess,
  inference, postprocess, pipeline-total mean/P50/P90/min/max, defined pipeline
  FPS, peak memory, CPU-utilization metric, threads, warmup, and repeat.
- Label all units and repeat the exact FPS/stage-boundary definitions.
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
PYTHONPATH=python python3 python/apps/ort_image.py \
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
python3 scripts/generate_pc_acceptance.py \
  --tasks tasks \
  --benchmark-inputs \
    results/benchmarks/pc_python_ort.json \
    results/benchmarks/pc_cpp_ort.json \
    results/benchmarks/pc_cpp_ncnn.json \
  --fresh-results \
    results/acceptance/python_ort_reference.json \
    results/acceptance/cpp_ort_reference.json \
    results/acceptance/cpp_ncnn_reference.json \
  --csv results/benchmarks/pc_all_summary.csv \
  --json results/evidence/012/pc_acceptance.json \
  2>&1 | tee results/logs/012_pc_acceptance.log
```

## Test Commands

```bash
set -o pipefail
PYTHONPATH=python python3 -m unittest discover -s tests/python -p 'test_*.py' -v
ctest --test-dir build/pc-acceptance-release --output-on-failure
PYTHONPATH=python python3 -m unittest tests/python/test_pc_acceptance.py
python3 -m json.tool results/evidence/012/pc_acceptance.json >/dev/null
test -s results/acceptance/python_ort_reference.png
test -s results/acceptance/cpp_ort_reference.png
test -s results/acceptance/cpp_ncnn_reference.png
git diff --check
```

## Acceptance Criteria

- All Task 001–011 records/evidence validate without modifying prior evidence.
- Release build and complete Python/C++ test suites pass in the recorded environment.
- Fresh Python ORT, C++ ORT, and C++ ncnn runs succeed on identical frozen inputs.
- Fresh detection comparisons pass the already frozen tolerances.
- All three output images are nonempty/decodable and receive human visual review.
- Generated performance table contains all three backends and every required real
  metric/settings/environment field; no number was typed or inferred manually.
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
Release build/tests, fresh commands/detections/images and cross-checks, generated
three-backend CSV/JSON, benchmark method and source hashes, acceptance matrix,
human visual/performance/checkpoint decisions, attempts, and final Git status.

## Automatic Retry Rules

At most three complete repair loops may fix only report-generator, acceptance-test,
or documentation defects in Allowed Files. Never repair by altering implementation,
old evidence, model/config/golden, tolerances, benchmark inputs, or measured values.
Such a need is an immediate stop and requires reopening the owning task explicitly.

## Human Stop Conditions

Stop for any missing/drifted evidence, incomplete prior approval, build/test/run
failure owned by an earlier task, fresh-result mismatch, image judgment, performance
interpretation, benchmark inconsistency, proposed ARM claim, or protocol condition.
Task completion triggers mandatory Checkpoint C and no automatic Stage 2 work.

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

Not started. No PC-stage acceptance result or three-backend table has been generated.
