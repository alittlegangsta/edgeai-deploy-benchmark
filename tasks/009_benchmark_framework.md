# Task 009

## Title

Create a unified, auditable PC benchmark framework.

## Status

Completed

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

The approved policy is single-image sequential CPU execution with one explicit
ORT intra-op thread, one explicit ORT inter-op thread, one OpenCV thread, 10
warmup iterations, and 100 measured iterations per independent process. Run five
independent processes per backend in the approved alternating order, for 500
formal samples per backend. The approved values are frozen evidence and must not
be changed after measurement begins.

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
  monotonic clocks. For each raw sample, define pipeline total as the exact sum
  of the three unrounded nanosecond stage measurements; never sum rounded
  millisecond summaries.
- Exclude image read, model/session creation, visualization, image/video writing,
  and video encoding from pipeline total. Document any separately measured
  end-to-end value under a distinct name.
- Preserve all 100 raw samples from each round and all 500 samples per backend.
  A single Python summarizer must calculate count, mean, nearest-rank P50 and P90,
  minimum, and maximum for every stage, per round and across all five rounds.
- Record every round's model-load time, fastest and slowest aggregate sample
  identity, and the maximum relative difference among the five pipeline means,
  defined as `(maximum mean - minimum mean) / minimum mean * 100`.
- For batch 1 sequential runs, define pipeline FPS as
  `1000 / mean(pipeline_total_ms)`. Do not use inference-only FPS or reciprocal
  mean-of-reciprocals under the same label.
- Preserve warmup separately and exclude it from reported distributions.
- Use identical thread/warmup/repeat/configuration across Python and C++, or stop.
  Explicitly use ORT 1.18.1, CPUExecutionProvider, intra-op 1, inter-op 1,
  sequential execution, ORT_ENABLE_ALL graph optimization, and OpenCV thread 1.
- Record `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
  `NUMEXPR_NUM_THREADS=1`. Record CPU affinity as scheduler managed, CPU pinning
  disabled, and environment WSL2; do not describe it as a bare-metal or pinned-
  core microbenchmark.
- Each round must be a separate process that reads the reference image once,
  creates one ORT session outside timing, records model load/session creation,
  executes 10 full-pipeline warmups, executes 100 full-pipeline measurements,
  writes its raw samples, and exits. No preprocessed tensor may be cached.
- Run an untimed correctness comparison against the fixed golden result before
  warmup and after the measured loop. The timed postprocess stage must still
  perform decode, filtering, class-aware NMS, inverse mapping, and clipping.
- For each round, measure process CPU over exactly the 100 formal pipelines as
  `100 * delta(user + system CPU time) / delta(wall-clock time)`. Record Linux
  `getrusage(RUSAGE_SELF).ru_maxrss * 1024` after measurement as process-lifetime
  peak RSS. State that RSS is process-level rather than model-only: Python
  includes interpreter/modules and C++ includes executable/dynamic-library cost.
- Alternate independent processes exactly: round 1 Python/C++, round 2 C++/Python,
  round 3 Python/C++, round 4 C++/Python, round 5 Python/C++.
- Preserve every outlier. If the five pipeline means for either backend have a
  maximum relative difference above 10 percent, or obvious system-load anomalies
  appear, stop for human review without publishing a formal conclusion.
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

Run in the approved alternating order without changing system or task
configuration. Each invocation is an independent process and appends exactly one
round to its backend JSON:

```bash
mkdir -p results/benchmarks results/evidence/009 results/logs
rm -f \
  results/benchmarks/pc_python_ort.json \
  results/benchmarks/pc_cpp_ort.json \
  results/benchmarks/pc_ort_summary.csv \
  results/evidence/009/benchmark_validation.json \
  results/logs/009_python_ort_benchmark.log \
  results/logs/009_cpp_ort_benchmark.log
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Round 1: Python ORT -> C++ ORT
PYTHONPATH=python .venv/bin/python python/apps/benchmark_ort.py --benchmark-config configs/benchmark_pc.json --round 1 --output results/benchmarks/pc_python_ort.json 2>&1 | tee -a results/logs/009_python_ort_benchmark.log
./build/pc-benchmark-release/edgeai_benchmark_ort --benchmark-config configs/benchmark_pc.json --round 1 --output results/benchmarks/pc_cpp_ort.json 2>&1 | tee -a results/logs/009_cpp_ort_benchmark.log

# Round 2: C++ ORT -> Python ORT
./build/pc-benchmark-release/edgeai_benchmark_ort --benchmark-config configs/benchmark_pc.json --round 2 --output results/benchmarks/pc_cpp_ort.json 2>&1 | tee -a results/logs/009_cpp_ort_benchmark.log
PYTHONPATH=python .venv/bin/python python/apps/benchmark_ort.py --benchmark-config configs/benchmark_pc.json --round 2 --output results/benchmarks/pc_python_ort.json 2>&1 | tee -a results/logs/009_python_ort_benchmark.log

# Round 3: Python ORT -> C++ ORT
PYTHONPATH=python .venv/bin/python python/apps/benchmark_ort.py --benchmark-config configs/benchmark_pc.json --round 3 --output results/benchmarks/pc_python_ort.json 2>&1 | tee -a results/logs/009_python_ort_benchmark.log
./build/pc-benchmark-release/edgeai_benchmark_ort --benchmark-config configs/benchmark_pc.json --round 3 --output results/benchmarks/pc_cpp_ort.json 2>&1 | tee -a results/logs/009_cpp_ort_benchmark.log

# Round 4: C++ ORT -> Python ORT
./build/pc-benchmark-release/edgeai_benchmark_ort --benchmark-config configs/benchmark_pc.json --round 4 --output results/benchmarks/pc_cpp_ort.json 2>&1 | tee -a results/logs/009_cpp_ort_benchmark.log
PYTHONPATH=python .venv/bin/python python/apps/benchmark_ort.py --benchmark-config configs/benchmark_pc.json --round 4 --output results/benchmarks/pc_python_ort.json 2>&1 | tee -a results/logs/009_python_ort_benchmark.log

# Round 5: Python ORT -> C++ ORT
PYTHONPATH=python .venv/bin/python python/apps/benchmark_ort.py --benchmark-config configs/benchmark_pc.json --round 5 --output results/benchmarks/pc_python_ort.json 2>&1 | tee -a results/logs/009_python_ort_benchmark.log
./build/pc-benchmark-release/edgeai_benchmark_ort --benchmark-config configs/benchmark_pc.json --round 5 --output results/benchmarks/pc_cpp_ort.json 2>&1 | tee -a results/logs/009_cpp_ort_benchmark.log

.venv/bin/python scripts/validate_benchmark.py \
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
- C++ benchmark is provably Release; Python and C++ run as ten alternating,
  independent processes in one unchanged recorded environment with identical
  settings, yielding exactly 500 formal samples per backend.
- Preprocess, inference, postprocess, and exact unrounded stage-sum pipeline-total
  samples are distinct; load/read/draw/write/encode are excluded and documented.
- Each stage has real count, mean, P50, P90, min, and max.
- FPS is labeled and computed exactly as `1000 / mean pipeline total ms` for batch
  1 sequential execution.
- CPU/environment information, peak memory, and the frozen CPU-utilization metric
  are present and genuine.
- Warmup samples are excluded; each process records model load, CPU-window and
  process peak RSS; repeat counts and all sample/stat relationships pass validation.
- Per-round and 500-sample aggregate statistics, fastest/slowest identities and
  five-round mean relative difference are produced by the same nearest-rank
  summarizer for both backends; every outlier remains present.
- Untimed golden-result correctness checks pass before and after every round.
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
- Python OpenCV 4.10.0 and C++ OpenCV 4.6.0 limit single-cause attribution of
  preprocess timing differences even though correctness/tensor alignment passed.
- `process_cpu_percent_one_core_basis` may exceed 100 percent because a process
  can have limited additional Runtime/system thread activity despite library
  thread settings of 1.

## Completion Report Format

Report files, frozen methodology, environment/Release proof, commands, real
stage-stat table and FPS definition, memory/CPU metrics, validator/tests, outliers,
human decision, attempts, risks, Checkpoint B package, and final Git status. Stop
and await explicit Batch C approval.

## Execution Record

Started: `2026-07-21T14:10:07+08:00`

Branch: `feature/pc-batch-b-cpp-ort`

Starting commit: `07fb482`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output after the Task 008 atomic commit).

Dependency: Task 008 is `Completed` in local commit `07fb482`. Task 009 is
`In Progress`, but no configuration, framework code, benchmark execution,
latency, FPS, memory, or CPU measurement has been created. The mandatory
pre-measurement methodology approval remains unresolved.

### Methodology Decision and Blocking Report

Stopped: `2026-07-21T14:10:54+08:00`

Read-only feasibility checks found Linux x86_64 under WSL2, `20` logical CPUs,
and an Intel Core i5-14600KF. Python and C++ can both use standard Linux
`getrusage`; Python also exposes monotonic `perf_counter_ns` and process CPU
`process_time_ns`. Therefore peak RSS and process CPU utilization can be
measured without installing a dependency, but their exact definitions still
require human approval before formal measurement.

Proposed frozen formal policy for approval:

```text
workload:
  fixed image: data/samples/images/pc_reference.jpg
  image SHA256: 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
  fixed model: models/yolov5n-v7.0/yolov5n.onnx
  model SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
  inference config: configs/yolov5n_v7_inference.json
  config SHA256: 82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d
  input: 640x640, batch 1, FP32
  providers: Python ORT CPUExecutionProvider; C++ ORT CPUExecutionProvider
  execution mode: sequential

threading:
  ORT intra-op threads: 1
  ORT inter-op threads: 1
  OpenCV threads: 1
  CPU affinity: not pinned

repetitions:
  warmup complete pipelines: 10, excluded from all reported distributions
  measured complete pipelines: 100
  backend order: Python ORT, then C++ ORT, back-to-back
  all measured samples retained; no outlier removal or retry for favorable data

timing clocks:
  Python: time.perf_counter_ns
  C++: std::chrono::steady_clock

measured stage boundaries:
  preprocess: fixed decoded BGR image -> letterboxed RGB NCHW FP32 tensor
  inference: backend inference call including tensor wrapper and output validation/copy
  postprocess: decode, threshold, class-aware NMS, inverse mapping, clipping
  pipeline_total: directly measured preprocess start through postprocess end
  excluded: image read/decode, model/session creation, visualization, drawing,
            output write, video I/O and encoding

statistics:
  raw samples preserved for every measured iteration and stage
  count, mean, minimum, maximum
  P50 and P90 use nearest-rank: sorted[ceil(p * count) - 1]
  pipeline FPS label: pipeline_fps_batch1_sequential
  FPS formula: 1000 / mean(pipeline_total_ms)
  no inference-only value may be called pipeline FPS

resource metrics:
  process_cpu_utilization_percent =
    100 * delta(process user+system CPU seconds) / delta(monotonic wall seconds)
  CPU window: all 100 measured full-pipeline iterations only
  CPU value is process utilization and may exceed 100% if actual runtime uses
    more than one logical CPU despite the requested thread settings
  peak_rss: Linux getrusage(RUSAGE_SELF).ru_maxrss converted from KiB to bytes
  peak RSS scope: process lifetime through completion of measured iterations;
    includes interpreter/runtime, decoded input, model, session and benchmark data

outlier policy:
  preserve every sample
  report max/P90 ratios and raw samples
  do not automatically discard, winsorize, rerun or replace any outlier
  stop after validation for human interpretation of observed distributions

environment stability:
  one unchanged WSL instance and working tree
  no intentional concurrent heavy workload, suspend/resume or environment change
  run Python then C++ immediately using the task commands
  record OS/kernel/architecture/CPU/logical CPUs/compiler/Python/OpenCV/ORT/build
```

The policy intentionally does not use Task 008 container `30 FPS` or its
single-run timings. It does not include video, image read, visualization, or
encoding. No benchmark config or result has been created before approval.

```text
Current Task: Task 009
Current Status: Blocked
Last Successful Step: Task 008 completed and committed as 07fb482; Task 009 dependency, branch, clean-worktree and resource-metric feasibility checks passed
Failed Command: none; mandatory pre-measurement methodology approval is unresolved
Exit Code: N/A
Relevant Error: thread/warmup/repeat policy, percentile definition, CPU/RSS metric boundaries, outlier handling and environment-stability conditions are not yet human-approved
Files Changed: TASKS.md; tasks/009_benchmark_framework.md
Attempts Made: 0 repair attempts; stopped before configuration, implementation, build or measurement
Why Automatic Recovery Is Unsafe: choosing benchmark methodology changes the meaning and comparability of formal latency, FPS, CPU and memory results; the task explicitly requires user approval before the first formal run
Exact Human Action Required: approve the complete proposed frozen policy above or specify exact replacements for threading, affinity, warmup, repeat, backend order, percentile method, timing inclusions/exclusions, CPU-utilization window/formula, peak-RSS scope, outlier policy and environment-stability conditions
Commands to Resume: repeat startup audit and read this Blocked record; verify hashes/environment again; record the approved policy verbatim in configs/benchmark_pc.json and docs/benchmark_methodology.md before implementation; do not run formal benchmarks until configuration/tests/validator and Release proof pass
Git Status: only TASKS.md and tasks/009_benchmark_framework.md contain the legal Task 009 Blocked-state record; no files are staged and no Task 009 commit or benchmark result exists
```

### Approved Methodology and Recovery

Resumed: `2026-07-21`

The user approved the final formal method. It replaces the earlier single-pair
proposal with five independent process rounds per backend in the exact alternating
order documented in Run Commands. Each process uses warmup 10 and repeat 100;
therefore each backend must preserve 500 formal samples. ORT 1.18.1 CPU execution,
intra/inter-op thread counts of 1, sequential mode, all graph optimizations,
OpenCV thread count 1, FP32 batch-1 640 by 640 input, scheduler-managed affinity,
disabled CPU pinning, WSL2, and all four thread environment variables set to 1
are frozen.

The fixed CPU formula, Linux peak-RSS conversion and scope, exact stage timing
boundaries, nearest-rank statistics, aggregate FPS formula, pre/post correctness
checks, outlier retention, and 10 percent five-round stability stop are now
approved. The missing `ONNXRUNTIME_ROOT` shell variable observed during recovery
was not treated as an SDK failure: the previously approved read-only SDK at
`/home/dministrator/opt/onnxruntime/onnxruntime-linux-x64-1.18.1` was verified
directly, including headers, x86-64 library, and dynamic dependencies. Formal
build commands must explicitly supply that fixed root.

Task 009 is restored to `In Progress`. No formal benchmark data exists at this
point. After the first complete ten-process run and generated validation outputs,
the task must stop for human review and remain non-Completed.

### Repair Attempt 1

Failure: The first ten-process formal command stopped after completing round 4,
leaving 400 raw samples per backend instead of the required 500. All eight
completed processes reported successful correctness checks and wrote valid JSON;
there was no application error in either backend log.

Root Cause: The long-running command session was ended by the command execution
harness before round 5 started. This was an orchestration interruption, not a
measured performance failure or backend failure.

Files Modified: No source/configuration file was modified to address the failure.
The incomplete generated JSON and logs are diagnostic task outputs only.

Fix Applied: Restart the complete approved sequence from empty output files in a
single command with a sufficient execution yield window. Do not append only round
5, select samples, or retain the incomplete sequence as formal evidence.

Commands Re-run: Full Release incremental build, all CTest tests, Python benchmark
statistics tests, then the complete alternating five-round sequence from round 1.

Result: The full restart completed successfully with 500 new formal samples per
backend. The incomplete 400-sample files were replaced only as part of this full
from-round-1 restart; no individual sample or favorable round was selected.

### Formal Run and Validation Evidence

Completed automatic validation: `2026-07-21T14:37:35+08:00`

Release configuration used GCC 13.3.0, system OpenCV 4.6.0, and the approved
read-only ONNX Runtime 1.18.1 SDK. The build completed without warnings. CTest
passed 7/7, the Python repository suite passed 50/50 before formal execution,
and the focused benchmark statistics suite passed 7/7 both before and after the
formal run. The final JSON parse checks and `git diff --check` passed.

The full restart launched ten independent processes in the approved order:

```text
Round 1: Python ORT -> C++ ORT
Round 2: C++ ORT -> Python ORT
Round 3: Python ORT -> C++ ORT
Round 4: C++ ORT -> Python ORT
Round 5: Python ORT -> C++ ORT
```

Each process completed 10 excluded warmups, 100 retained formal pipelines, and
untimed golden-result comparisons before and after measurement. All 20
correctness comparisons passed. The validator confirmed exactly 500 samples per
backend, exact integer stage sums, distinct process IDs, frozen hashes, ORT CPU
provider/settings, Release C++, required environment variables, and the approved
process order.

Candidate aggregate results awaiting human approval:

```text
Python ORT pipeline total (500 samples):
  mean 50.566201402 ms; P50 50.255584 ms; P90 52.321040 ms
  min 47.851400 ms; max 61.066230 ms
  pipeline FPS 19.7760553942
  five-round means: 50.64641718, 51.52583861, 50.09389432,
                    50.16144741, 50.40340949 ms
  maximum round-mean relative difference: 2.858520603 percent (PASS)
  fastest aggregate sample 252 (round 3, iteration 52)
  slowest aggregate sample 139 (round 2, iteration 39)

C++ ORT pipeline total (500 samples):
  mean 46.868422690 ms; P50 46.713867 ms; P90 48.182646 ms
  min 45.058795 ms; max 50.014768 ms
  pipeline FPS 21.3363271603
  five-round means: 47.11677256, 46.83252539, 46.88986484,
                    46.72138633, 46.78156433 ms
  maximum round-mean relative difference: 0.846263908 percent (PASS)
  fastest aggregate sample 310 (round 4, iteration 10)
  slowest aggregate sample 132 (round 2, iteration 32)

Candidate comparison (not yet an approved conclusion):
  C++ aggregate mean pipeline latency is 7.312747664 percent lower.
  Python-mean / C++-mean latency ratio is 1.078897016.
  C++ calculated pipeline FPS is 7.889701637 percent higher.
```

All outliers remain in the raw JSON. Python per-round model load was
`26.649479, 24.515147, 26.627728, 24.200770, 25.804319 ms`; C++ was
`46.127253, 47.157786, 48.423678, 47.222859, 47.605719 ms`. Python process CPU
was `111.041790` to `111.109887` percent on the one-core basis and peak RSS was
`178692096` to `181534720` bytes. C++ process CPU was `111.097875` to
`111.109806` percent and peak RSS was `154054656` to `154705920` bytes. These
are process-level values: Python includes interpreter/modules and C++ includes
the executable/dynamic libraries. The consistent values above 100 percent are
reported without alteration and require human interpretation under WSL2.

The recorded environment is WSL2 kernel
`6.6.87.2-microsoft-standard-WSL2`, Intel Core i5-14600KF, x86_64, 20 logical
CPUs, scheduler-managed affinity, and disabled pinning. Python used OpenCV 4.10.0;
C++ used system OpenCV 4.6.0. Both used ORT 1.18.1, CPUExecutionProvider,
intra/inter-op 1, sequential execution, all graph optimization, OpenCV thread 1,
and all four required environment variables set to 1.

Generated evidence SHA256:

```text
benchmark config: 64596e3fd469227c25c2e8c397aade0079867ef3e5e238eec83c50c3536c536d
Python raw JSON: 125f1fa1eb2f2ab46268fb9bdb7cd37d7092543a29d6b41527f885d41e417c41
C++ raw JSON: 8b8a6cfb444dd4047a43165c256c7a854b406079f8cfb93479039733af7c5c8e
summary CSV: 4ac971e42f718807fd802c3df9e69cf1a4acc3766f1457e2f86b57fc4d35be63
validation JSON: b3edd6664db4f3c9a9f9e7359687b3d43e826e092b3237e57f9f323d0602fcfc
```

One post-run shell group mistakenly invoked bare `python` without activating the
virtual environment; those three JSON pretty-print commands failed with
`python: command not found`. No artifact was modified. The required checks were
immediately rerun with `.venv/bin/python` and all passed. This was not used to
discard or regenerate measurement data.

### Repair Attempt 2

Failure: The final no-index whitespace check reported that the generated summary
CSV used CRLF line endings, which conflicts with the repository LF policy.

Root Cause: Python's default `csv` writer dialect emits CRLF even when the file is
opened with `newline=""`.

Files Modified: `scripts/validate_benchmark.py` and the regenerated
`results/benchmarks/pc_ort_summary.csv`; the validation JSON was regenerated from
the unchanged raw inputs. No raw sample file was modified.

Fix Applied: Set the common CSV writer's `lineterminator` explicitly to `"\n"`.

Commands Re-run: Focused Python tests, CTest, unified validation/summary generation
from the existing two raw JSON inputs, JSON parsing, all tracked and untracked
whitespace checks, and final Git status.

Result: Passed. The regenerated CSV uses LF, the two raw JSON SHA256 values are
unchanged, unified validation still reports 500 samples per backend and both
stability gates passing, and all repeated tests/checks passed.

### Human Review Blocking Report

```text
Current Task: Task 009
Current Status: Blocked
Last Successful Step: full Release build, ten-process formal benchmark, unified 500-sample-per-backend validation, CSV generation, JSON checks, tests, and git diff check all passed
Failed Command: none in the benchmark or final acceptance commands; mandatory post-measurement human review is pending
Exit Code: N/A
Relevant Error: no automatic stability failure; candidate performance, CPU/RSS interpretation, outliers, environment record, and Python/C++ difference require human approval before publication
Files Changed: only Task 009 Allowed Files; generated logs are ignored and raw JSON/CSV/validation evidence are untracked
Attempts Made: 2 repair attempts; the first orchestration session ended after round 4 and the entire sequence was restarted from round 1 without selecting samples; the second fixed derived CSV line endings without changing raw data
Why Automatic Recovery Is Unsafe: approving formal performance and WSL2 process resource interpretation is the explicit Task 009 human gate and Checkpoint B decision
Exact Human Action Required: inspect configs/benchmark_pc.json, docs/benchmark_methodology.md, both raw JSON files, results/benchmarks/pc_ort_summary.csv, results/evidence/009/benchmark_validation.json, and both ignored logs; confirm sample counts/order, five-round stability, outliers, candidate Python/C++ comparison, and CPU/peak-RSS scope; then explicitly approve Task 009 and Checkpoint B or request a full new run without overwriting this evidence
Commands to Resume: repeat branch/status/protocol audit; verify evidence hashes above; rerun the validator and required tests without rerunning benchmark processes; after explicit approval only, mark Task 009 Completed, run staged checks, create the prescribed local atomic commit, and stop at Checkpoint B
Git Status: Task 009 source/config/docs/task records and generated JSON/CSV/evidence are unstaged; benchmark logs are present but Git-ignored; no Task 009 commit exists
```

### Human Approval Recovery

Resumed: `2026-07-21`

The user approved the preserved 500-sample Python ORT and 500-sample C++ ORT
data as the current formal PC ORT result. Approval explicitly covers all retained
raw samples and outliers, the five-round stability observations, the fixed WSL2
environment, and the documented timing/resource boundaries. It does not approve
a general language-level claim, a bare-metal result, another model, ARM, or a
different runtime/configuration.

Recovery revalidated the approved raw evidence before changing state:

```text
Python raw JSON SHA256: 125f1fa1eb2f2ab46268fb9bdb7cd37d7092543a29d6b41527f885d41e417c41
C++ raw JSON SHA256: 8b8a6cfb444dd4047a43165c256c7a854b406079f8cfb93479039733af7c5c8e
Python: 5 rounds, 500 samples, 5 distinct process IDs, 10/10 correctness checks PASS
C++: 5 rounds, 500 samples, 5 distinct process IDs, 10/10 correctness checks PASS
Actual round order: Python/C++, C++/Python, Python/C++, C++/Python, Python/C++
Unified validator: PASS
Overall stability gate: PASS
```

The validator was run against the unchanged raw inputs with outputs directed to
`/tmp`; the regenerated CSV and validation report compared byte-for-byte equal
to the repository evidence. SHA256 was checked both before and after this audit,
and neither raw JSON changed. Task 009 is restored to `In Progress` solely to add
the approved interpretation, rerun acceptance, and perform the authorized atomic
commit. The benchmark itself must not be rerun.

### Completion and Checkpoint B Record

Completed: `2026-07-21T15:21:19+08:00`

The approved raw benchmark was not rerun, truncated, replaced, or edited during
completion. Its SHA256 values remained:

```text
Python raw JSON: 125f1fa1eb2f2ab46268fb9bdb7cd37d7092543a29d6b41527f885d41e417c41
C++ raw JSON: 8b8a6cfb444dd4047a43165c256c7a854b406079f8cfb93479039733af7c5c8e
```

The machine validation report retains its historical
`PENDING_HUMAN_REVIEW` status because it is the byte-preserved output generated
before approval. The user's dated approval in this Execution Record satisfies
the separate human Acceptance Criterion and promotes the measured values to the
current formal PC ORT result without rewriting measured or derived evidence.

Fresh completion verification:

```text
branch: feature/pc-batch-b-cpp-ort
Release configure: exit 0; GCC 13.3.0; C++ OpenCV 4.6.0; ORT SDK 1.18.1
Release build: exit 0; 27/27 build steps; no warning emitted
Python environment: Python 3.12.3; pip check PASS
Python full suite: 50/50 PASS
focused benchmark statistics: 7/7 PASS
CTest: 7/7 PASS
benchmark executable RUNPATH: approved local ORT 1.18.1 SDK
benchmark executable build proof: Release
JSON parse checks: PASS
unified validation regenerated under /tmp: PASS
regenerated CSV versus preserved CSV: byte-for-byte equal
regenerated validation JSON versus preserved validation JSON: byte-for-byte equal
git diff --check: PASS
benchmark processes rerun during completion: none
```

The formal aggregate stage table is in `docs/benchmark_methodology.md` and was
confirmed from the unchanged raw JSON:

```text
Python ORT (mean / P50 / P90 / min / max, ms)
preprocess:    3.208576 / 3.143332 / 3.625834 / 2.573579 / 5.031788
inference:    42.185939 / 41.979068 / 43.452668 / 40.109507 / 51.634398
postprocess:   5.171687 / 5.060641 / 5.779656 / 4.423278 / 7.848948
pipeline:     50.566201 / 50.255584 / 52.321040 / 47.851400 / 61.066230

C++ ORT (mean / P50 / P90 / min / max, ms)
preprocess:    1.655221 / 1.621770 / 1.768998 / 1.532662 / 2.144182
inference:    41.528575 / 41.383756 / 42.836305 / 39.795074 / 44.671321
postprocess:   3.684627 / 3.642040 / 3.841475 / 3.540840 / 4.740303
pipeline:     46.868423 / 46.713867 / 48.182646 / 45.058795 / 50.014768
```

Approved interpretation: under the fixed WSL2 CPU benchmark configuration, the
C++ ONNX Runtime complete pipeline achieved 46.87 ms mean latency versus 50.57 ms
for Python ONNX Runtime, or 7.31 percent lower mean pipeline latency in this
implementation and environment. The claim is not generalized to language-level
performance, inference kernels, bare-metal Linux, other machines, ARM, models,
or configurations. Pipeline FPS excludes file reading, model/session creation,
drawing, labels, writing, and encoding.

Python used OpenCV 4.10.0 and C++ used OpenCV 4.6.0. Correctness and input-tensor
alignment passed, so this does not invalidate the complete-pipeline comparison;
it prevents attributing the preprocess difference to one cause or the complete
performance difference solely to Python versus C++.

`process_cpu_percent_one_core_basis` is retained as the CPU metric. ORT intra-op
and inter-op threads were 1, execution was sequential, OpenCV threads were 1,
affinity was scheduler managed, pinning was disabled, and the platform was WSL2.
Approximately 100 percent represents sustained use of one logical CPU; values
near 111 percent show limited additional Runtime/system thread activity. A thread
setting of 1 does not force the whole process to have exactly one thread, and this
is not a fixed-physical-core strict single-thread microbenchmark.

Peak RSS remains process-level rather than model-only. Python includes the
interpreter, modules, Runtime, model, and Session; C++ includes the executable,
dynamic libraries, Runtime, model, and Session.

All Acceptance Criteria passed, including the human performance review. Task 009
is `Completed`. Batch B stops at Checkpoint B; Task 010 remains `Planned` and was
not started. The required local atomic commit is created after explicit staging
and cached-diff review and is the commit containing this Execution Record.
