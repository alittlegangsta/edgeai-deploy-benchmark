# Task 017

## Title

Anlogic DR1 ARM CPU benchmark.

## Status

In Progress

## Stage

Stage 2 benchmark

## Dependencies

Tasks 013, 014, and 015 (`Completed`).

## Recommended Branch

`feature/arm-cpu-benchmark`

## Recommended Commit

`feat(benchmark): freeze DR1 ARM CPU benchmark protocol`

## Goal

Measure the frozen YOLOv5n ncnn single-image pipeline on the real
MLK-F3P-CZ02-DR1M90 ARM CPU under a preregistered and reproducible protocol.
Protocol, collector, and validator behavior must be frozen before any formal
measurement is collected or published.

## Scope

This task may:

- freeze the already approved ncnn, model, input, configuration, PC golden, and
  one-thread CPU/FP32 identities;
- reuse the existing shared C++ preprocess, ncnn inference, and postprocess path;
- add a backward-compatible ARM mode to the existing C++ ncnn benchmark target;
- freeze five independent process rounds, ten warmups per round, and twenty
  measured iterations per round;
- collect exact stage durations, model-load time, process Peak RSS, CPU
  frequency, temperature, and before/after environment evidence;
- retain every valid and failed round record without latency-based filtering;
- add an explicit offline-checkable runner and deterministic validator;
- collect and validate formal evidence only in a separately authorized
  real-board execution turn.

This task does not include video, camera, Vulkan, FP16/BF16/INT8 runtime,
multi-thread tuning, CPU affinity changes, governor or frequency changes, NPU,
model conversion, threshold changes, system-image changes, or comparison of
alternative optimization settings.

Single-run Task 014 timing is diagnostic only and is not Task 017 benchmark
evidence. Correctness validation protects the benchmark but does not substitute
for formal measurement. Any later optimization experiment requires a separate
contract and may not overwrite this unoptimized baseline.

## Frozen Runtime and Workload

```text
board: MLK-F3P-CZ02-DR1M90
architecture: AArch64
board CPU: two cores, CPU part 0xd04
board OS: Buildroot 2022.02.6
board kernel: 6.1.111-rt42
board userspace: glibc 2.25

ncnn tag: 20240410
ncnn commit: 56775de50990ab7f16627efdcf5529b49541206f
runtime: CPU-only
precision: FP32
batch: 1
input: 640x640
threads: 1
Vulkan: off
FP16 storage/arithmetic: off
BF16 storage: off
INT8 inference: off

input blob: in0
output blob: out0
confidence threshold: 0.25
NMS IoU threshold: 0.45
classes: COCO-80
```

```text
ncnn param SHA256:
72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4

ncnn bin SHA256:
658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0

fixed input SHA256:
625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071

inference config SHA256:
82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d

PC C++ ncnn golden JSON SHA256:
fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9
```

The ignored `.param` and `.bin` remain external deployment inputs. They must
pass the frozen hashes before packaging, after transfer, and before each formal
process.

## Formal Sampling Protocol

```text
independent process rounds: 5
warmup iterations per round: 10
measured iterations per round: 20
valid measured samples required: 100
threads: 1
```

Each round is a newly started process. It loads the same model and image,
records `model_load_ms` separately, runs one untimed correctness check, performs
ten untimed warmups, records twenty complete pipelines, runs a second untimed
correctness check, writes one machine-readable round fragment, and exits zero.
The next round must start a new process. A process may not append more than its
single assigned round.

The core stages are timed with `std::chrono::steady_clock` in integer
nanoseconds:

```text
preprocess = shared BGR-to-RGB, letterbox, normalize, and HWC-to-CHW path
inference = ncnn input bind, extract, output validation, and output copy
postprocess = shared YOLO decode, confidence filter, coordinate restore, and NMS
pipeline = preprocess + inference + postprocess
```

Image read/decode, model load, correctness checks, warmups, environment
collection, drawing, JSON serialization, PNG writing, SSH transfer, and process
startup are excluded from `pipeline`. Formal iterations do not draw or write an
annotated image. Model load is preserved only as `model_load_ms`.

## Statistics

All one hundred valid samples are summarized together and by round for
preprocess, inference, postprocess, and pipeline:

```text
count
mean
P50
P90
minimum
maximum
sample standard deviation
```

P50 and P90 use nearest-rank:

```text
sorted_values[ceil(percentile * count) - 1]
```

Sample standard deviation uses a denominator of `count - 1`. Pipeline FPS is:

```text
1000 / aggregate mean pipeline_ms
```

It is not the mean of per-sample FPS and is not video throughput. Every round
also records mean, P50, P90, minimum, maximum, process order, exit code,
`model_load_ms`, and `peak_rss_kib`.

## Environment and Resources

The runner captures before and after:

- board model/compatible identity, architecture, OS, kernel, and glibc;
- CPU count, `/proc/cpuinfo` summary, memory totals/availability, uptime, and
  load average;
- every readable CPU governor, available-frequency, and current-frequency
  sysfs node;
- every readable thermal-zone type and temperature.

Missing commands or sysfs nodes are represented by `null` or `unavailable`,
never by zero. The runner is read-only with respect to governor, frequency,
thermal state, services, networking, and the system image.

The benchmark process records `getrusage(RUSAGE_SELF).ru_maxrss` as
`peak_rss_kib`. This is a process-level high-water mark from process start, not
model-only memory. Each formal sample records the maximum readable current CPU
frequency and maximum readable thermal-zone temperature immediately after the
pipeline; unavailable values are JSON `null`.

## Correctness Guardrails

Before warmup and after formal measurement, the identical pipeline is compared
with the approved PC C++ ncnn golden. Both checks require:

```text
exit code: 0
detections: 5
class match: PASS
finite values: PASS
valid boxes: PASS
minimum class-matched IoU >= 0.99
maximum confidence delta <= 0.01
```

The known low-confidence earbud-case `mouse` false positive must remain. The
formal benchmark is `FAIL` and performance must not be published if the
before/after result differs, any output is non-finite, or any box is invalid.
Correctness PNG/JSON output is produced in separate pre/post validation stages,
not during each measured iteration.

## Invalid Rounds and Outliers

All measurements and failure evidence are retained. High latency is never a
reason to remove or replace a sample.

A round may be marked invalid only for a nonzero process exit, SSH disconnect,
model/input/config hash mismatch, malformed JSON, system reboot, or a proven
collector failure. Its original fragment, stdout, stderr, exit code, and reason
remain evidence. One replacement process with the next attempt number may be
added. The final accepted dataset still requires exactly five valid independent
rounds and one hundred valid samples; invalid attempts are excluded from
statistics only because their explicit failure status makes them non-samples.

## Result Contract

Formal evidence is reserved under:

```text
results/evidence/017/
  benchmark_contract.json
  benchmark_environment_before.json
  benchmark_environment_after.json
  benchmark_raw_samples.json
  benchmark_summary.json
  benchmark_validation.json
```

The raw file preserves round/process identity, every integer-nanosecond stage
duration and derived millisecond value, sampled CPU frequency and temperature,
round resources, model-load time, asset hashes, and correctness gates. Summary
and validation files are generated only by
`scripts/vendor/validate_anlogic_arm_benchmark.py`; measured values must never
be typed into documentation or hand-edited.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
tasks/017_anlogic_dr1_arm_cpu_benchmark.md
configs/benchmark_anlogic_arm.json
cpp/apps/benchmark_ncnn.cpp
cpp/src/common/benchmark.cpp
cpp/tests/test_benchmark.cpp
scripts/vendor/build_anlogic_aarch64_yolov5n.sh
scripts/vendor/run_anlogic_arm_benchmark.sh
scripts/vendor/validate_anlogic_arm_benchmark.py
tests/python/test_anlogic_arm_benchmark.py
.knowledge/manifests/anlogic_arm_cpu_benchmark.yaml
docs/vendor/ANLOGIC_ARM_CPU_BENCHMARK.md
results/evidence/017/benchmark_contract.json
```

Repository-external build/deployment/result files are allowed only under
ignored task-owned build or shared directories and a task-owned board
deployment directory. Formal returned results become allowed only after the
separate board-collection turn explicitly authorizes them.

## Forbidden Files and Actions

- Do not modify Tasks 001–016, their evidence, PC benchmark data, model
  manifests, frozen assets, thresholds, or PC golden files.
- Do not commit ARM ELF files, `libncnn.a`, model `.param`/`.bin`, SDK content,
  VM build trees, deployment packages, large logs, or credentials.
- Do not access the VM or board during protocol freeze.
- Do not run or publish a formal benchmark during protocol freeze.
- Do not modify governor, affinity, frequency, thermal controls, services,
  networking, system libraries, boot media, or the system image.
- Do not use video, camera, Vulkan, quantization, NPU, or model conversion.
- Do not delete outliers, weaken correctness thresholds, fabricate unavailable
  metrics, or replace failed evidence silently.

## Build Commands

Protocol-freeze validation uses the model-independent local Release build:

```bash
cmake -S cpp -B build/ci-cpp-local-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-cpp-local-release --parallel
```

The AArch64 benchmark target is rebuilt in the VM only in the separately
authorized formal-collection turn through the existing ARM build entry point.

## Run Commands

The only runner commands allowed during protocol freeze are:

```bash
bash scripts/vendor/run_anlogic_arm_benchmark.sh --check
bash scripts/vendor/run_anlogic_arm_benchmark.sh --dry-run
```

Formal collection later uses the explicitly gated execution mode documented by
the runner and Task 017 benchmark guide.

## Test Commands

```bash
bash -n scripts/vendor/run_anlogic_arm_benchmark.sh
python3 -m py_compile \
  scripts/vendor/validate_anlogic_arm_benchmark.py \
  tests/python/test_anlogic_arm_benchmark.py
PYTHONPATH=python .venv/bin/python -m unittest \
  tests/python/test_anlogic_arm_benchmark.py -v
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests/python -p 'test_*.py' -v
ctest --test-dir build/ci-cpp-local-release --output-on-failure
git diff --check
```

Synthetic validator tests must use generated temporary data clearly labelled
as fixtures. They are not measured evidence and may not be placed in formal
result paths.

## Acceptance Criteria

1. Tasks 013, 014, and 015 remain `Completed` and their evidence is unchanged.
2. Frozen runtime, model, input, configuration, PC golden, thread, precision,
   and feature identities pass hash/schema validation.
3. Five independent processes, ten warmups, twenty formal iterations, and one
   hundred samples are enforced by the C++ producer, runner, and validator.
4. Core timing boundaries and exclusions are exact and pipeline is the integer
   sum of preprocess, inference, and postprocess.
5. All raw samples, valid/invalid attempts, nearest-rank statistics, sample
   standard deviation, aggregate FPS, Peak RSS, model load, and environment
   fields are preserved and independently recomputed.
6. Before/after correctness gates both pass against the frozen PC ncnn golden.
7. The formal board run yields five valid rounds, one hundred valid samples,
   parseable raw/environment evidence, and zero unexplained process failure.
8. No latency outlier is removed, and any replacement round retains the failed
   attempt plus an allowed invalid reason.
9. The board identity, ABI, hashes, runtime configuration, governor,
   frequencies, temperatures, memory, uptime, and load evidence are complete or
   explicitly unavailable.
10. Summary and validation are generated from raw evidence and are not
    hand-entered.
11. Repository build, CTest, Python tests, schema, documentation, sensitive
    material, artifact-policy, and diff checks pass.
12. No formal value is published before the complete candidate dataset and
    environment receive the task's required human review.

Criteria 1–5 and the offline portions of 9–11 may pass during protocol freeze.
Criteria 6–8 and the real-board portions of 9–12 require the separately
authorized formal collection. Task 017 remains `In Progress` until every
criterion passes in real execution and the user reviews the complete candidate
dataset.

## Repair Rules

At most three complete repair loops may address producer, runner, environment
capture, transfer, schema, or validator defects. Every attempt records the
failing command, exact error, diagnosis, files changed, rebuild/redeploy, and
retest. Never repair by changing frozen assets, thresholds, Runtime, sample
counts, timing boundaries, statistics, or retained observations.

## Human Stop Conditions

Stop for human direction if:

- board power, physical network, IP, or credentials require intervention;
- root/system changes, package installation, image flashing, or SDK mutation
  would be required;
- frozen ncnn, model, input, config, threshold, or PC golden would need to
  change;
- PC benchmark definitions conflict with the ARM contract in a way that cannot
  preserve both;
- correctness before/after fails or only reaches a separately defined hard
  floor;
- the complete first candidate dataset requires performance review;
- three complete safe repair attempts fail or the technology route must change.

Ordinary CLI, schema, formatting, path, test, and documentation errors are
repairable within the Allowed Files.

## Evidence Brief

```text
task: Task 017 Anlogic DR1 ARM CPU benchmark protocol
board: MLK-F3P-CZ02-DR1M90
SDK tag: SDK_2025_07 local asset identity; exact official repository tag compatibility unproven
repository tag/commit: ncnn 20240410 / 56775de50990ab7f16627efdcf5529b49541206f
sources consulted: Tasks 009, 011, 012, 013, 014, and 015; their tracked manifests and evidence; existing benchmark and ARM application source
documented facts: the board and ABI passed Tasks 013-015; no formal ARM benchmark exists
source-code facts: the existing ncnn benchmark target reuses shared preprocessing, ncnn inference, and postprocessing but its original protocol is PC-specific
assumptions: none
conflicts: the exact official repository SDK tag corresponding to the local SDK_2025_07 asset remains unproven and is not needed for this CPU benchmark identity
unresolved blockers: real-board formal collection and human review are pending
proposed action: freeze and locally validate protocol/tooling, then run one separately authorized real-board campaign
```

## Execution Record

Started: `2026-07-28T16:47:58+08:00`

Branch: `feature/arm-cpu-benchmark`

Starting commit: `bd9f995bfca52e0ced2fdbde9d7c5927b6cede93`

Starting status: clean; HEAD equals local `dev`.

Initial audit:

- Tasks 013–015 are `Completed`; Task 015 explicitly assigns formal ARM
  benchmarking to future Task 017.
- PC Task 011/012 use independent processes, untimed correctness before/after,
  integer-nanosecond stage sums, nearest-rank P50/P90, aggregate-mean pipeline
  FPS, model-load time, and process Peak RSS.
- The existing `edgeai_benchmark_ncnn` shares the Task 014 inference path but
  hard-codes WSL2, five rounds with 100 measured iterations, Task 011 evidence
  naming, and no per-sample frequency/temperature.
- No VM or board was accessed and no performance process was run during this
  audit.

Resume instructions: implement the backward-compatible ARM producer mode,
freeze config/manifest/documentation, add the offline runner and deterministic
validator with synthetic fixtures, run only local checks, and leave Task 017
`In Progress` pending formal real-board collection.

### Protocol Freeze Implementation

Recorded: `2026-07-28T17:05:39+08:00`

The existing `edgeai_benchmark_ncnn` target was retained instead of adding a
second inference implementation. Its original Task 011 PC mode still accepts
schema 1, WSL2, five rounds, 10 warmups, and 100 measured iterations. The new
schema 2 Task 017 mode:

- requires the AArch64 board identity at runtime;
- requires explicit hash-validated param/bin paths suitable for an isolated
  deployment package;
- freezes five rounds, 10 warmups, and 20 measured iterations;
- writes a Task 017 evidence type without changing Task 011 evidence naming;
- records authoritative nanoseconds plus derived milliseconds;
- records process Peak RSS in KiB and bytes;
- samples readable CPU-frequency and thermal sysfs nodes after each pipeline;
- writes missing sensor values as JSON `null`;
- performs the same PC-golden comparison before warmup and after measurement.

Sensor paths are discovered once before correctness/warmup/formal sampling.
Only readable paths are sampled in the formal loop. Sensor reads are outside
the timed pipeline but occur between iterations; this measurement influence is
declared rather than hidden.

The shared benchmark comparison now rejects non-finite confidence/box values
and non-positive source-coordinate boxes explicitly. New C++ tests cover both
guards. This strengthens Task 017 correctness without changing the IoU or
confidence tolerance.

The existing ARM application build script now includes, inspects, hashes, and
exports `edgeai_benchmark_ncnn` alongside the Task 014 image target. It was not
run because this turn forbids VM access. The currently shared Task 014 build
output therefore does not yet contain the benchmark ELF; offline checks report
`BUILD_REQUIRED_IN_FORMAL_COLLECTION_TURN` without claiming an AArch64 build.

The new runner has three explicit modes:

```text
--check: local contract and frozen-asset validation only
--dry-run: the same offline validation plus the side-effect plan
--execute: separately authorized build-output packaging, isolated board
           deployment, environment capture, five process rounds, collection,
           and deterministic summarization
```

Only `--check` and `--dry-run` ran. Neither invokes the VM or board wrapper.
Formal execution preserves numbered stdout/stderr/exit-code attempts. A failed
round can resume at the same round without deleting accepted earlier rounds;
latency never triggers replacement. A raw round found without its acceptance
marker stops rather than being overwritten or silently rerun.

The deterministic validator checks the frozen config/contract and, for real
evidence, requires five unique process identities, 100 samples, exact stage
sums, exact ns-to-ms conversion, frozen hashes/runtime flags, valid resource
fields, before/after `PASS_TARGET`, nearest-rank P50/P90, sample standard
deviation, aggregate-mean FPS, and the retained 10 percent round-mean spread
gate. It writes only generated summary/validation files. Seven synthetic
fixture tests exercise the pass path and rejection of incomplete rounds,
stage-sum drift, process reuse, correctness drift, and outlier-policy changes.
Synthetic values exist only in temporary test objects and are not formal
benchmark evidence.

### Repair Attempt 1: OpenCV configuration parser

```text
Failed command: .venv/bin/python inline cv2.FileStorage parse of configs/benchmark_anlogic_arm.json
Error: OpenCV persistence_json.cpp reported that JSON value null is unsupported
Diagnosis: the executable uses OpenCV FileStorage; Python's general JSON parser had accepted a documentation-only null in resources.missing_value
Files modified: configs/benchmark_anlogic_arm.json and its tracked hash references
Fix: encode the configuration description as the string "JSON null"; real missing sensor observations remain JSON null in raw evidence
Retest: OpenCV FileStorage parse, contract validator, 7 focused tests, runner --check, runner --dry-run, and git diff --check
Result: PASS
```

### Offline Validation

No VM, board, inference, or benchmark command ran.

```text
Task 017 config JSON parse: PASS
Task 017 contract JSON parse and hash reconciliation: PASS
all repository YAML: PASS (30 files / 30 documents)
all repository JSON outside ignored environments/builds: PASS (44 files)
Markdown relative links: PASS (12)
all tracked shell syntax: PASS
Task 017 Python py_compile: PASS
Task 017 focused unittest: PASS (7/7)
full Python unittest: PASS (71/71)
model-independent Release configure/build: PASS (8 build steps)
model-independent CTest: PASS (4/4)
fully configured PC benchmark target rebuild: PASS
fully configured PC CTest: PASS (12/12; invalid-argument tests only)
runner --check: PASS
runner --dry-run: PASS
frozen param/bin/input/config/PC-golden hashes: PASS
sensitive-material scan: PASS
single-file size check: PASS; no task file exceeds 35 KiB
git diff --check: PASS
```

Protocol identities:

```text
benchmark config SHA256:
51ffd0db29be98e74767ee5cf5d03d97f8392ebd42749aa4c9c46bb8162f20c1

tracked benchmark contract SHA256:
4eb3c024e58c9fbae0cf7554fa45dfaa248549b334886c632de3fdb6b9a95461
```

One `apply_patch` call for the sensor-path refinement failed atomically because
its expected context did not match the observed sample-writing lines. It
changed no file. The patch was split against the real content, then the
benchmark target and all focused tests were rebuilt successfully. This was an
editing-orchestration mismatch, not a producer, runner, benchmark, or evidence
repair attempt.

Task 017 remains `In Progress`. Protocol and offline tooling are ready. Formal
readiness still requires the separately authorized VM cross-build and AArch64
ELF inspection, followed by board preflight and the first complete candidate
campaign. No performance number is present or published.
