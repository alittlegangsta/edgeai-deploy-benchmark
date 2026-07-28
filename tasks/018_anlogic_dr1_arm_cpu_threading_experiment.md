# Task 018

## Title

Anlogic DR1 ARM CPU threading experiment.

## Status

In Progress

## Stage

Stage 2 CPU experiment

## Dependencies

Task 017 (`Completed`).

## Recommended Branch

`feature/arm-cpu-threading-experiment`

## Recommended Commit

`feat(benchmark): freeze DR1 CPU threading experiment`

## Goal

Compare one-thread and two-thread execution of the frozen YOLOv5n ncnn
pipeline on the real MLK-F3P-CZ02-DR1M90 under a paired, alternating, and
preregistered protocol. Freeze the producer, collector, raw evidence, statistics,
classification, and offline tests before any Task 018 performance data is
collected.

## Scope

The only experimental variable is `configured_threads`, with values `1` and
`2`. Both conditions use the same AArch64 ELF, board deployment directory,
ncnn `20240410` build, model, fixed input, CPU-only FP32 path, batch 1,
`640x640` input, thresholds, OpenCV thread count, timing boundaries,
statistics, and correctness reference.

This task excludes model/input/threshold/runtime revision changes, FP16, BF16
runtime storage, INT8, Vulkan, NPU, video, camera, governor or frequency
changes, affinity or pinning, compiler/NEON tuning, concurrent requests,
asynchronous pipelining, and system modification. Task 017 evidence is immutable
historical baseline data and is not replaced by this experiment.

## Frozen Inputs

```text
ncnn tag: 20240410
ncnn commit: 56775de50990ab7f16627efdcf5529b49541206f
ncnn param SHA256: 72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
ncnn bin SHA256: 658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0
fixed input SHA256: 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
inference config SHA256: 82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d
PC C++ ncnn golden SHA256: fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9
```

The ignored `.param` and `.bin` remain external deployment inputs and must pass
their hashes before packaging and after transfer.

## Paired Sampling Protocol

Each condition uses five independent processes. Every process performs one
correctness check, 10 untimed warmups, 20 measured pipelines, a second
correctness check, evidence serialization, and normal exit:

```text
pair 1: threads=1 -> threads=2
pair 2: threads=2 -> threads=1
pair 3: threads=1 -> threads=2
pair 4: threads=2 -> threads=1
pair 5: threads=1 -> threads=2

per condition: 5 processes, 10 warmups/process, 20 samples/process
total: 10 processes and 200 formal samples
```

One process cannot change its thread count or represent more than one
condition/round. Task 018 contemporaneously remeasures one thread so date,
load, and thermal state are paired with two threads. The Task 017 one-thread
result remains a historical consistency reference only.

## Timing and Statistics

Integer nanoseconds are authoritative:

```text
pipeline_ns = preprocess_ns + inference_ns + postprocess_ns
```

Image decode, model load, correctness, warmup, resource sampling, output writes,
process startup, and transfer stay outside the pipeline. Each condition is
independently summarized with count, mean, nearest-rank P50/P90, minimum,
maximum, sample standard deviation, aggregate-mean FPS, model-load time, Peak
RSS, and five-round pipeline-mean spread. No latency sample is removed.

The comparison is recomputed from raw evidence:

```text
pipeline_speedup = threads1_mean_pipeline_ms / threads2_mean_pipeline_ms
inference_speedup = threads1_mean_inference_ms / threads2_mean_inference_ms
fps_gain_percent = (threads2_fps / threads1_fps - 1) * 100
rss_change_percent = (threads2_peak_rss_kib / threads1_peak_rss_kib - 1) * 100
```

## Correctness, Stability, and Classification

Before warmup and after measurement, every process must exit zero and retain
five finite detections with valid boxes, class match, minimum class-matched IoU
at least `0.99`, and confidence delta at most `0.01`. The validator also
class-matches the captured one-thread and two-thread detections against each
other using the same targets.

Each condition independently applies the Task 017 stability gate:

```text
maximum process-round mean difference <= 10%
```

Classification is exhaustive:

- `BENEFICIAL`: correctness and both stability gates pass,
  `pipeline_speedup >= 1.05`, the two-thread P90 is no greater than the
  one-thread P90, and no new dependency/system change is reported.
- `NEUTRAL`: correctness and stability pass and
  `0.98 <= pipeline_speedup < 1.05`.
- `REGRESSION`: `pipeline_speedup < 0.98`, either correctness/stability gate
  fails, an unacceptable runtime/resource issue is reported, or a nominal
  speedup of at least `1.05` comes with worse two-thread P90 tail latency.

Peak RSS change is always disclosed. No RSS rejection threshold is invented.

The contemporaneous one-thread mean is compared with the Task 017
`3513.99235361 ms` historical mean. An absolute difference above `10%` is an
environment-drift warning, not a reason to alter or discard Task 018 samples.

## Result Contract

Preregistered files:

```text
results/evidence/018/experiment_contract.json
results/evidence/018/execution_order.json
```

Reserved formal outputs:

```text
results/evidence/018/threads1_raw_samples.json
results/evidence/018/threads2_raw_samples.json
results/evidence/018/process_environment.json
results/evidence/018/threads1_summary.json
results/evidence/018/threads2_summary.json
results/evidence/018/comparison_summary.json
results/evidence/018/experiment_validation.json
```

Raw and summary files are not created until a separately authorized real-board
turn. Unavailable frequency or temperature remains JSON `null`, never zero.
Invalid attempts stay outside the valid statistics but retain their original
stdout, stderr, exit code, and reason.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
tasks/018_anlogic_dr1_arm_cpu_threading_experiment.md
configs/benchmark_anlogic_arm_threading.json
cpp/apps/benchmark_ncnn.cpp
cpp/src/backends/ncnn_detector.cpp
cpp/tests/test_ncnn_detector.cpp
scripts/vendor/run_anlogic_arm_threading_experiment.sh
scripts/vendor/validate_anlogic_arm_threading_experiment.py
tests/python/test_anlogic_arm_threading_experiment.py
.knowledge/manifests/anlogic_arm_cpu_threading_experiment.yaml
docs/vendor/ANLOGIC_ARM_CPU_THREADING_EXPERIMENT.md
results/evidence/018/experiment_contract.json
results/evidence/018/execution_order.json
```

Task-owned external build, deployment, logs, and returned evidence are allowed
only in a separately authorized formal-collection turn.

## Forbidden Files and Actions

- Do not modify Task 017 config, evidence, task record, manifest, or published
  values.
- Do not modify frozen model/input/configuration assets, thresholds, Runtime
  revision, PC golden, SDK, board system state, or governor/frequency controls.
- Do not commit ARM ELF, ncnn/SDK content, model `.param`/`.bin`, private
  dynamic libraries, deployment packages, large logs, or credentials.
- Do not access the VM or board or collect/publish Task 018 performance data
  while freezing this protocol.
- Do not delete outliers, merge conditions, splice sessions, weaken correctness,
  turn JSON `null` into zero, or claim that two threads must be faster.

## Build Commands

Protocol freeze uses the existing local model-independent Release build:

```bash
cmake -S cpp -B build/ci-cpp-local-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-cpp-local-release --parallel
```

The shared AArch64 benchmark target is rebuilt in the VM only during the later
authorized collection turn.

## Run Commands

Only offline modes are allowed in this protocol-freeze turn:

```bash
bash scripts/vendor/run_anlogic_arm_threading_experiment.sh --check
bash scripts/vendor/run_anlogic_arm_threading_experiment.sh --dry-run
```

## Test Commands

```bash
bash -n scripts/vendor/run_anlogic_arm_threading_experiment.sh
python3 -m py_compile \
  scripts/vendor/validate_anlogic_arm_threading_experiment.py \
  tests/python/test_anlogic_arm_threading_experiment.py
PYTHONPATH=python .venv/bin/python -m unittest \
  tests/python/test_anlogic_arm_threading_experiment.py -v
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests/python -p 'test_*.py' -v
ctest --test-dir build/ci-cpp-local-release --output-on-failure
git diff --check
```

Synthetic fixtures are temporary non-measured data and never enter the formal
result paths.

## Acceptance Criteria

1. Task 017 remains `Completed` and its tracked evidence is byte-unchanged.
2. Runtime, model, input, thresholds, PC golden, ABI, timing, and statistics
   are frozen; the only variable is `configured_threads`.
3. The shared producer accepts only explicit Task 018 threads 1/2 plus the
   exact pair/order metadata, while Task 017 and PC behavior remain compatible.
4. The runner freezes the alternating 10-process order, validates asset hashes,
   keeps conditions separate, supports offline `--check`/`--dry-run`, and does
   not silently access remote systems.
5. The validator independently checks two 100-sample datasets, process
   independence, order, exact stage sums, statistics, FPS, resource fields,
   correctness, cross-condition correctness, separate stability gates,
   speedup formulas, classification, and Task 017 drift warning.
6. Synthetic tests cover `BENEFICIAL`, `NEUTRAL`, `REGRESSION`, correctness and
   stability failures, insufficient samples, incorrect threads/order,
   historical drift warning, and JSON-null sensors.
7. All YAML/JSON, syntax, Release build, CTest, Python tests, links, sensitive
   material, repository hygiene, and whitespace checks pass.
8. No VM, board, inference, or performance collection runs during protocol
   freeze.

Criteria 1–8 freeze the protocol but do not complete the experiment. Formal
collection, validator results, and required human review remain pending, so
Task 018 stays `In Progress`.

## Repair Rules

At most three complete repair loops may address producer, runner, schema,
validator, tests, or documentation. Preserve all invariants and never pass by
changing the sample count, order, frozen assets, thresholds, statistics, or
Task 017 evidence.

## Human Stop Conditions

Stop if progress requires a model/input/runtime change, board/system/governor
change, credentials, `sudo`, flashing, a different technology route, or a
decision that cannot preserve both Task 017 history and the paired Task 018
contract. Ordinary code, schema, test, path, and documentation faults are
repairable.

## Evidence Brief

```text
task: Task 018 Anlogic DR1 ARM CPU threading experiment
board: MLK-F3P-CZ02-DR1M90
SDK tag: SDK_2025_07 local asset identity; exact official repository tag compatibility unproven
repository tag/commit: ncnn 20240410 / 56775de50990ab7f16627efdcf5529b49541206f
sources consulted: Task 017 protocol/raw/summary/validation; Tasks 013-015 build, board, and correctness evidence; shared ncnn producer and adapter source
documented facts: Task 017 is the approved one-thread historical baseline; Task 018 has not collected data
source-code facts: the existing adapter and producer previously accepted exactly one thread and require a backward-compatible Task 018 extension
assumptions: none
conflicts: local SDK_2025_07 is not proof of an exact official repository SDK tag
unresolved blockers: formal VM rebuild and real-board paired collection are pending
proposed action: freeze and test the offline contract, then run the complete paired session under separate authorization
```

## Execution Record

Started: `2026-07-28`

Branch: `feature/arm-cpu-threading-experiment`

Starting commit: `9d4f40f33ccafa2493c7d4b1c416b217dd58f2cd`

Starting status: clean; HEAD equals local `dev`.

Initial source audit:

- Task 017 is `Completed` with immutable five-process/100-sample evidence.
- Its C++ producer and ncnn adapter both enforce one thread in source.
- Task 018 therefore needs a new schema and explicit thread/pair/order metadata,
  not a second preprocessing/inference/postprocessing implementation.
- No VM, board, inference, or benchmark command has run in this task.

Protocol freeze completed: `2026-07-28T18:51:51+08:00`

Implemented:

- the shared ncnn adapter accepts only one or two threads;
- the existing benchmark producer retains Task 017 and PC schemas and adds the
  Task 018 schema, explicit thread/pair/order checks, and small correctness
  snapshots without duplicating the inference pipeline;
- the runner freezes asset hashes and the alternating schedule, keeps Task 017
  evidence immutable, and provides offline `--check`/`--dry-run` modes;
- the validator independently recomputes per-condition statistics, correctness,
  stability, speedup, classification, and the Task 017 drift warning;
- twelve synthetic tests cover all three classifications and the required
  failure/null-data cases.

Repair attempt 1:

```text
failing command:
cmake --build build/ci-default-options-release --parallel

error:
benchmark_ncnn.cpp indexed Box as an array; Box exposes x1/y1/x2/y2 members

repair:
serialize the four named Box members, rebuild, rerun CTest and Python tests

result:
PASS
```

Final offline validation:

```text
Task 018 contract/hash check: PASS
runner --check: PASS
runner --dry-run: PASS; no VM, board, SSH, inference, or benchmark access
focused Task 018 synthetic tests: PASS (12/12)
model-independent Release build: PASS
model-independent CTest: PASS (4/4)
full default-options Release build: PASS
full CTest: PASS (12/12)
full Python unittest discovery: PASS (85/85)
YAML parse: PASS (30 files)
JSON parse: PASS (52 files)
OpenCV FileStorage config parse: PASS
tracked/non-ignored Bash syntax: PASS (20 files)
board POSIX sh syntax: PASS
tracked/non-ignored Python py_compile: PASS (33 files)
Markdown local links: PASS (56 files, 15 local links)
sensitive-material scan: PASS (15 candidate files)
candidate file type/size policy: PASS; largest candidate is 42923 bytes
Task 017 evidence/config/task/manifest/document immutability: PASS
git diff --check: PASS
```

No formal Task 018 output file was created. The existing ARM benchmark ELF
predates this source change and is reported as
`PRESENT_REBUILD_REQUIRED_AFTER_TASK018_SOURCE_CHANGE`; it is not accepted for
future collection. Task 018 remains `In Progress`.

Resume instructions: in a separately authorized turn, use WSL, the VM, and the
real board to rebuild one shared AArch64 ELF, execute the complete paired
schedule, preserve every attempt, validate both conditions, and request human
review before changing the task state.
