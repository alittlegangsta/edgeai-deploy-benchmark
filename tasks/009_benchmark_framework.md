# Task 009

## Title

Create a unified, auditable PC benchmark framework.

## Status

Planned

## Batch

Batch B

## Dependencies

Task 008 (`Completed`).

## Recommended Branch

`feature/pc-batch-b-cpp-ort`

## Recommended Commit

`feat(benchmark): add unified PC measurement framework`

## Goal

Define and execute one Release-only benchmark method for Python ORT and C++ ORT
that records comparable stage distributions, environment identity, resource
metadata, and an explicit FPS calculation. Make the schema reusable by ncnn.

## Why This Task Exists

Performance numbers are meaningless without fixed models, inputs, threading,
warmup, repeat counts, stage boundaries, build type, statistics, and environment.
A common schema prevents later backends from choosing favorable definitions.

## Knowledge Covered

- Benchmark design and warmup/repeat discipline.
- Monotonic timing and percentile calculation.
- Release-build verification.
- Resource/environment capture.
- Comparable machine-readable schema and honest FPS definitions.

## Scope

Implement a shared schema/config, Python ORT benchmark entry point, C++ benchmark
helpers and ORT entry point, validation/summarization script, and one real fixed-
image benchmark run for each existing backend. Design an extension point for ncnn
without implementing or estimating ncnn results.

Do not benchmark Debug builds, video encoding, visualization, model loading as
inference, ARM hardware, ncnn, or downloaded data. Do not publish unreviewed
performance as final conclusions.

## Allowed Files

```text
TASKS.md
tasks/009_benchmark_framework.md
configs/benchmark_pc.json
docs/benchmark_methodology.md
python/edgeai_benchmark/benchmark.py
python/apps/benchmark_ort.py
cpp/CMakeLists.txt
cpp/include/edgeai/common/benchmark.hpp
cpp/src/common/benchmark.cpp
cpp/apps/benchmark_ort.cpp
scripts/validate_benchmark.py
tests/python/test_benchmark_stats.py
cpp/tests/test_benchmark.cpp
results/benchmarks/pc_python_ort.json
results/benchmarks/pc_cpp_ort.json
results/benchmarks/pc_ort_summary.csv
results/evidence/009/benchmark_validation.json
results/logs/009_python_ort_benchmark.log
results/logs/009_cpp_ort_benchmark.log
```

Frozen model/image/config, completed backend implementations, and their evidence
are read-only inputs.

## Forbidden Files

- Task 002 model contract, preprocessing, postprocessing, thresholds, or golden
  result changes.
- ncnn or ARM implementation/results.
- Debug benchmark results presented as formal.
- Video read/write, image read, drawing, or encoding included in model inference.
- Hand-edited or fabricated benchmark measurements.
- Any file outside Allowed Files.

## Inputs

- Completed Python ORT and C++ ORT implementations using the same model, image,
  config, provider, and CPU.
- A human-approved `benchmark_pc.json` fixing input size 640 by 640, batch 1,
  FP32, thread count, warmup, repeat, clock, inclusion boundaries, and output paths.
- Unchanged machine/environment for the entire comparison.

The proposed starting policy is single-image sequential CPU execution, one
explicit runtime thread, 10 warmup iterations, and 100 measured iterations. The
user must confirm or change this policy before the first formal run; the selected
values then become frozen evidence, not assumptions.

## Expected Outputs

- A documented benchmark schema/method reusable by all PC backends.
- Real per-iteration or losslessly auditable stage samples for both ORT backends.
- Validated JSON for each backend, a generated comparison CSV, and validation log.
- Environment, CPU, dependency, model, input, and build identity.

## Implementation Requirements

- Reject non-Release C++ formal runs by checking build configuration in the
  executable and evidence.
- Record: backend, model identity, model SHA256, input size, batch, precision,
  provider, thread count, warmup, repeat, and clock.
- Record OS/kernel, CPU model, architecture, logical CPU count, relevant compiler,
  Python, OpenCV, ONNX Runtime, and build-type/version information.
- Record process peak resident memory and a clearly defined process CPU-utilization
  metric when it can be measured consistently. If the platform cannot provide one
  without new dependencies, stop before formal acceptance rather than invent it.
- Load/decode the image and create sessions outside measured repetitions.
- Measure preprocess, inference, postprocess, and pipeline total separately with
  monotonic clocks. Pipeline total is the directly measured contiguous
  preprocess-through-postprocess region, not the sum of rounded stage summaries.
- Exclude image read, model/session creation, visualization, image/video writing,
  and video encoding from pipeline total. Document any separately measured
  end-to-end value under a distinct name.
- Store count, mean, P50, P90, minimum, and maximum for every required stage in
  milliseconds; define nearest-rank or interpolated percentiles once and test it.
- For batch 1 sequential runs, define pipeline FPS as
  `1000 / mean(pipeline_total_ms)`. Do not use inference-only FPS or reciprocal
  mean-of-reciprocals under the same label.
- Preserve warmup separately and exclude it from reported distributions.
- Use identical thread/warmup/repeat/configuration across Python and C++, or stop.
- Generate JSON/CSV from measured samples; validators must reject missing fields,
  non-finite/negative values, count mismatches, hash/config drift, and inconsistent
  totals.
- Formal results require human confirmation of methodology, environment stability,
  outliers, and interpretation before Task 009 can be marked Completed.

## Build Commands

```bash
rm -rf build/pc-benchmark-release
cmake \
  -S cpp \
  -B build/pc-benchmark-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root>
cmake --build build/pc-benchmark-release --parallel
```

## Run Commands

Run back-to-back without changing system or task configuration:

```bash
mkdir -p results/benchmarks results/evidence/009 results/logs
PYTHONPATH=python python3 python/apps/benchmark_ort.py \
  --benchmark-config configs/benchmark_pc.json \
  --output results/benchmarks/pc_python_ort.json \
  2>&1 | tee results/logs/009_python_ort_benchmark.log
./build/pc-benchmark-release/edgeai_benchmark_ort \
  --benchmark-config configs/benchmark_pc.json \
  --output results/benchmarks/pc_cpp_ort.json \
  2>&1 | tee results/logs/009_cpp_ort_benchmark.log
python3 scripts/validate_benchmark.py \
  --config configs/benchmark_pc.json \
  --inputs \
    results/benchmarks/pc_python_ort.json \
    results/benchmarks/pc_cpp_ort.json \
  --csv results/benchmarks/pc_ort_summary.csv \
  --report results/evidence/009/benchmark_validation.json
```

## Test Commands

```bash
PYTHONPATH=python python3 -m unittest tests/python/test_benchmark_stats.py
ctest --test-dir build/pc-benchmark-release --output-on-failure
python3 -m json.tool results/benchmarks/pc_python_ort.json >/dev/null
python3 -m json.tool results/benchmarks/pc_cpp_ort.json >/dev/null
python3 -m json.tool results/evidence/009/benchmark_validation.json >/dev/null
git diff --check
```

## Acceptance Criteria

- Method/config explicitly freezes backend, model/SHA, image/SHA, 640 input,
  batch 1, FP32, thread count, warmup, repeat, stage boundaries, and clock.
- C++ benchmark is provably Release; Python and C++ run in one unchanged recorded
  environment with identical settings.
- Preprocess, inference, postprocess, and directly measured pipeline-total samples
  are distinct; load/read/draw/write/encode are excluded and documented.
- Each stage has real count, mean, P50, P90, min, and max.
- FPS is labeled and computed exactly as `1000 / mean pipeline total ms` for batch
  1 sequential execution.
- CPU/environment information, peak memory, and the frozen CPU-utilization metric
  are present and genuine.
- Warmup samples are excluded; repeat counts and all sample/stat relationships
  pass validation.
- Tests, both real runs, schema validation, CSV generation, and
  `git diff --check` pass with only Allowed Files changed.
- A human confirms methodology, environment stability, outliers, and authentic
  performance before completion.
- Checkpoint B evidence is assembled, then Codex stops.

## Evidence to Preserve

Frozen config/hash, environment/CPU/dependency versions, Release proof, exact
commands, per-stage samples/statistics, FPS calculation, memory/CPU method and
values, validator/tests, outlier notes, human confirmation, attempts, and Git
status.

## Automatic Retry Rules

At most three complete repair loops may correct framework/statistics defects.
Never discard outliers, reduce repeats, alter thread counts/stage boundaries, use
Debug, or edit measured values to pass. Environment change, suspect results, or
methodology decisions require an immediate stop and a clean rerun after approval.

## Human Stop Conditions

Apply every benchmark and general protocol stop. In particular stop for Debug,
unspecified settings, environment drift, outliers, inseparable stages, inclusion-
boundary decisions, unavailable honest resource metrics, or performance review.

## Codex Responsibilities

Enforce the frozen method, generate evidence only through real runs, validate
schemas/statistics, label FPS accurately, surface outliers, assemble Checkpoint B,
and stop for review.

## User Responsibilities

Approve methodology before measurement, keep the machine stable, decide handling
of outliers and optional I/O boundaries, review real performance, approve Task
009/Checkpoint B, and explicitly authorize Batch C.

## Known Risks

- CPU frequency scaling, thermal state, and background WSL activity affect results.
- Runtime threading controls may not map identically across languages.
- First-use allocations can leak past insufficient warmup.
- Process CPU/memory APIs differ across platforms.

## Completion Report Format

Report files, frozen methodology, environment/Release proof, commands, real
stage-stat table and FPS definition, memory/CPU metrics, validator/tests, outliers,
human decision, attempts, risks, Checkpoint B package, and final Git status. Stop
and await explicit Batch C approval.

## Execution Record

Not started. No benchmark, latency, FPS, memory, or CPU measurement exists.
