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
configs/benchmark_anlogic_arm_threading_openmp.json
cpp/CMakeLists.txt
cpp/apps/benchmark_ncnn.cpp
cpp/src/backends/ncnn_detector.cpp
cpp/tests/test_ncnn_detector.cpp
scripts/vendor/run_anlogic_arm_threading_experiment.sh
scripts/vendor/build_anlogic_aarch64_ncnn_openmp.sh
scripts/vendor/validate_anlogic_arm_threading_experiment.py
tests/python/test_anlogic_arm_threading_experiment.py
.knowledge/manifests/anlogic_arm_cpu_threading_experiment.yaml
docs/vendor/ANLOGIC_ARM_CPU_THREADING_EXPERIMENT.md
results/evidence/018/experiment_contract.json
results/evidence/018/execution_order.json
results/evidence/018/threads1_raw_samples.json
results/evidence/018/threads2_raw_samples.json
results/evidence/018/process_environment.json
results/evidence/018/threads1_summary.json
results/evidence/018/threads2_summary.json
results/evidence/018/comparison_summary.json
results/evidence/018/experiment_validation.json
results/evidence/018/thread_backend_audit.json
results/evidence/018/thread_diagnostic_threads1.json
results/evidence/018/thread_diagnostic_threads2.json
results/evidence/018/openmp/instrument_correction.json
results/evidence/018/openmp/build_provenance.json
results/evidence/018/openmp/experiment_contract.json
results/evidence/018/openmp/thread_diagnostic_threads1.json
results/evidence/018/openmp/thread_diagnostic_threads2.json
results/evidence/018/openmp/threads1_raw_samples.json
results/evidence/018/openmp/threads2_raw_samples.json
results/evidence/018/openmp/process_environment.json
results/evidence/018/openmp/threads1_summary.json
results/evidence/018/openmp/threads2_summary.json
results/evidence/018/openmp/comparison_summary.json
results/evidence/018/openmp/experiment_validation.json
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
sources consulted: Task 017 protocol/raw/summary/validation; Tasks 013-015 build, board, and correctness evidence; fixed ncnn 20240410 source; actual VM ncnn CMake cache/generated header/library symbols; shared producer/adapter; real-board diagnostic evidence
documented facts: Task 017 is the approved one-thread historical baseline; Task 018 session 2 is retained but not approved as a multithread comparison
source-code facts: ncnn ARM operators use OpenMP pragmas parameterized by opt.num_threads; NCNN_THREADS alone is not an operator parallel-for backend
assumptions: none
conflicts: local SDK_2025_07 is not proof of an exact official repository SDK tag
unresolved blockers: user decision on a separate multithread-enabled ncnn build
proposed action: retain session 2 as OpenMP-off parameter sensitivity evidence and do not publish it as a hardware multithread comparison
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

### Formal collection and automatic validation

Recorded in WSL: `2026-07-28T19:38:35+08:00`

This is evidence record time, not board runtime time. The board clock remained
unsynchronized.

Build provenance:

```text
source archive SHA256:
540773f59afda16baa89538b33b5c5a8889f4105818a30e53e8c7b3b84a12f57

AArch64 benchmark ELF SHA256:
40fdd3b777fccaf3bd45f3a9c59842de53e7bf42bcbd285fa73c37b86b457f2a

identity:
ELF64 AArch64; interpreter /lib/ld-linux-aarch64.so.1

version requirements:
GLIBC_2.17; GLIBCXX through 3.4.21

dependencies:
private OpenCV 4.7.0 core/imgproc/imgcodecs plus board libstdc++, libm,
libgcc_s, libpthread, libc, and libdl; no not found
```

The build used CMake `3.16.9`, Linaro GCC/G++ `7.5.0`, the existing glibc
sysroot, and the unchanged static ncnn library
`5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a`.

Repair attempt 2:

```text
failing command:
ANLOGIC_ARM_BUILD_OUTPUT=<isolated-build-output>
bash scripts/vendor/run_anlogic_arm_threading_experiment.sh --execute

exit code:
1

error:
ncnn benchmark error: existing ncnn benchmark round identity differs

diagnosis:
Task 018 inserts pair/order/thread metadata between round and process_id, while
the inherited append validator searched for the Task 017 adjacency marker
{"round":N,"process_id":...}.

repair:
use the Task 018 {"round":N,"pair_index":N,...} marker, rebuild a new ELF, and
restart from pair 1 in a new isolated session.

evidence retention:
session 1, pair 1 accepted outputs, and all three pair 2 failed attempts remain
on the board/external log workspace. No session 1 round entered session 2.

result:
PASS in real cross-round board persistence
```

Repair attempt 3:

```text
failing command:
python3 scripts/vendor/validate_anlogic_arm_threading_experiment.py summarize ...

exit code:
1

error:
Task 018 validation error: before correctness rank differs

diagnosis:
the real producer and frozen golden use ranks 1..5, while the validator's
synthetic fixture and expected-rank loop used 0..4.

repair:
make the validator and synthetic fixtures use the real 1-based rank contract,
rerun all 12 focused tests, then regenerate summaries from the unchanged
session 2 raw samples.

result:
PASS; no board process or sample was rerun
```

Session 2 is the only candidate session:

```text
valid independent processes: 10/10
invalid attempts: 0
threads=1: 5 processes, 100 samples
threads=2: 5 processes, 100 samples
execution order: exact frozen alternating order
all latency samples retained: PASS
```

Aggregate statistics:

| Threads | Stage | Mean ms | P50 ms | P90 ms | Min ms | Max ms | Sample SD ms |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | preprocess | 43.184844 | 42.474930 | 44.597880 | 41.846340 | 44.861520 | 1.150449 |
| 1 | inference | 3454.640931 | 3411.887794 | 3521.293595 | 3406.792144 | 3526.319855 | 54.530257 |
| 1 | postprocess | 54.479381 | 53.800650 | 55.517131 | 53.738580 | 55.615560 | 0.845584 |
| 1 | pipeline | 3552.305157 | 3507.941614 | 3621.351036 | 3502.856314 | 3626.291916 | 56.510796 |
| 2 | preprocess | 43.889654 | 43.348470 | 44.781991 | 43.206931 | 45.175291 | 0.716340 |
| 2 | inference | 3452.370362 | 3412.009714 | 3524.030555 | 3405.674524 | 3526.573205 | 54.430014 |
| 2 | postprocess | 54.456765 | 53.804430 | 55.520760 | 53.742901 | 56.405010 | 0.839741 |
| 2 | pipeline | 3550.716782 | 3509.071055 | 3624.286566 | 3502.723445 | 3627.243066 | 55.950511 |

Comparison:

```text
threads1 FPS: 0.2815073468486081
threads2 FPS: 0.28163327612748756
threads1 maximum Peak RSS: 142572 KiB
threads2 maximum Peak RSS: 142872 KiB
threads1 mean model load: 644.9032742 ms
threads2 mean model load: 647.9484844 ms
pipeline speedup: 1.0004473392268058
inference speedup: 1.000657684049391
FPS gain: 0.04473392268058429%
RSS change: 0.2104199983166355%
threads1 five-round spread: 3.343810125550009% (PASS)
threads2 five-round spread: 3.2791492082843625% (PASS)
Task 017 mean difference: 1.0902927421182582% (PASS)
candidate classification: NEUTRAL
```

Every before/after correctness check passed with five detections, minimum
golden IoU `0.9999855075776749`, and maximum confidence delta
`0.0000050067901611328125`. Cross-condition correctness is `PASS_TARGET` with
IoU `1.0` and confidence delta `0.0`.

All 200 frequency and all 200 temperature observations are JSON `null` because
the board exposes no readable matching nodes. No null was changed to zero. The
20 process environment events preserve the observed load. No governor,
frequency, affinity, system library, service, model, input, threshold, Runtime,
or Task 017 evidence was modified.

Candidate evidence SHA256:

```text
threads1_raw_samples.json:
7a2f96346f289860b0033ffdd5c635f572cd4c52306a9a13c2e39ec9f24f833c
threads2_raw_samples.json:
d385cf4055b54da915fe710855a9e434e07f4434723b4a9a1bc6aa70e4005125
process_environment.json:
14ce7a366527d5bb63db77233e16724130aacb7d44c2cffe1a58a48a08f8f9b2
threads1_summary.json:
5b5039f6ce5bc663d93d4a3bd3732fd0996338027bf4667a076d59b7b4958ede
threads2_summary.json:
520c99e8c1fe54929642c7247ccd2fbd09d3292650e3f26cd2c0b0440111590a
comparison_summary.json:
3ac735e4ff474ec2f515b39cd7758e3289d94f028c54406609f54b2f63042de3
experiment_validation.json:
de908a24ca5a2cc23648f16ca649a4b62c3cd3410468e0009c2a31a72de794b3
```

Automatic status:

```text
validator: PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW
raw statistical classification: NEUTRAL
human_review: PENDING
candidate_approved: false
Task 018: In Progress
```

Final offline validation before human review:

```text
independent process-environment regeneration: PASS; byte-identical
independent summary/validation regeneration: PASS; byte-identical
runner --check: PASS; rebuilt ELF output hash verified
runner --dry-run: PASS; no VM, board, inference, or benchmark command
focused Task 018 synthetic tests: PASS (12/12)
model-independent Release build: PASS
model-independent CTest: PASS (4/4)
full default-options Release build: PASS
full CTest: PASS (12/12)
full Python unittest discovery: PASS (85/85)
YAML parse: PASS (30 files)
JSON parse: PASS (59 files)
manifest/evidence SHA256 reconciliation: PASS
raw integrity: PASS (10 processes, 200 samples)
JSON-null frequency/temperature preservation: PASS (200/200 each)
tracked/non-ignored Bash syntax: PASS (20 files)
board POSIX sh syntax: PASS
tracked/non-ignored Python py_compile: PASS (33 files)
Markdown local links: PASS (56 files, 22 links)
sensitive-material scan: PASS (17 candidate files)
candidate file type/size policy: PASS; largest candidate is 65979 bytes
Task 017 immutability: PASS
git diff --check: PASS
```

### Thread-backend audit after withheld approval

Recorded in WSL: `2026-07-28T20:04:29+08:00`

The user withheld candidate approval because the frozen ncnn build recorded
`NCNN_OPENMP=OFF`. The complete session 2 data remains byte-preserved and its
raw statistical classifier still says `NEUTRAL`; neither fact establishes that
two CPU threads actually ran.

Fixed-source evidence from ncnn tag `20240410`, commit
`56775de50990ab7f16627efdcf5529b49541206f`:

```text
ARM operator parallelism:
#pragma omp parallel for num_threads(opt.num_threads)

NCNN_THREADS:
pthread-backed mutex, condition variable, thread and TLS primitives;
not an independent operator parallel-for backend

NCNN_SIMPLEOMP:
minimal OpenMP runtime implementation guarded by NCNN_SIMPLEOMP
```

Real VM build evidence:

```text
NCNN_OPENMP=OFF
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
OpenMP_CXX_FOUND=NOT_EVALUATED_BECAUSE_NCNN_OPENMP_OFF
compile flags: -pthread; no -fopenmp
link: pthread only; no libgomp/libomp
symbols: pthread lock/TLS references; no GOMP/OMP/KMP implementation
simpleomp.cpp.o: guarded empty object
```

The application does set `network.opt.num_threads` before `load_param`.
However, because the ARM operator parallel regions were compiled without
OpenMP or simpleomp, changing that value from one to two cannot activate
operator parallelism in this library.

The capability-aware diagnostic rebuild used the same static ncnn library:

```text
source archive SHA256:
d5b5a6afe02243b96f15c527539303f1aae0252c7f8b9afcf5fb0fcdc7052849

diagnostic ELF SHA256:
46b2b33d6854ec20dc9922d884f38d5df81c348699cbd4da4c1466f1faa39578

identity:
ELF64 AArch64; /lib/ld-linux-aarch64.so.1; maximum GLIBC_2.17

reported capability:
OPENMP=false, THREADS=true, SIMPLEOMP=false, compiler _OPENMP=false,
effective_parallel_backend=none
```

The real board then ran one independent diagnostic process per condition with
two warmups and three measured pipelines. These measurements are diagnostic,
not a replacement formal session:

```text
configured_threads=1:
  max observed /proc process threads: 1
  internal threads before/after measured region: 1/1
  user CPU seconds: 10.365416000000002
  system CPU seconds: 0.07906999999999997
  wall seconds: 10.520665064
  CPU-time/wall-time ratio: 0.9927591018688856
  correctness before/after: PASS_TARGET/PASS_TARGET

configured_threads=2:
  max observed /proc process threads: 1
  internal threads before/after measured region: 1/1
  user CPU seconds: 10.465954999999999
  system CPU seconds: 0.06934300000000002
  wall seconds: 10.874386338
  CPU-time/wall-time ratio: 0.9688177035962872
  correctness before/after: PASS_TARGET/PASS_TARGET
```

The first external `/proc` monitor command had a shell-quoting defect and
recorded zeroes. Those diagnostic files are retained outside Git. A separate
retry corrected only the monitor read, used new output paths, and observed one
thread for both conditions. No formal session or Task 017 evidence was rerun.

Audit result:

```text
CURRENT_BUILD_HAS_NO_EFFECTIVE_CPU_OPERATOR_PARALLEL_BACKEND
OPENMP_OFF_THREAD_PARAMETER_SENSITIVITY: PASS
MULTITHREAD_PERFORMANCE_COMPARISON: INVALID
publication classification: INVALID_FOR_MULTITHREAD_PERFORMANCE_COMPARISON
candidate_session_retained: true
human_review: PENDING
candidate_approved: false
Task 018: In Progress
```

Evidence:

```text
results/evidence/018/thread_backend_audit.json
results/evidence/018/thread_diagnostic_threads1.json
results/evidence/018/thread_diagnostic_threads2.json
```

Final offline validation of the retained candidate and thread-backend audit:

```text
independent session 2 summary/validation regeneration: PASS; byte-identical
runner --check: PASS
runner --dry-run: PASS; no VM, board, inference, or benchmark command
focused Task 018 tests: PASS (14/14)
model-independent Release build and CTest: PASS (4/4)
full default-options Release build and CTest: PASS (12/12)
full Python unittest discovery: PASS (87/87)
YAML parse: PASS (30 files)
JSON parse: PASS (62 files)
manifest/evidence SHA256 reconciliation: PASS (10 files)
frozen model/input SHA256 checks: PASS
Markdown local links: PASS (56 files, 25 links)
changed-file sensitive/binary/size hygiene: PASS (21 files)
tracked/non-ignored Bash syntax: PASS
tracked/non-ignored Python py_compile: PASS
Task 017 immutability: PASS
git diff --check: PASS
```

Resume instructions: a user technical-route decision is required. The proposed
next step is a separate reproducible ncnn build with a verified OpenMP or
simpleomp backend, followed by a new complete paired session using only that
new ELF. Do not alter Task 017, overwrite session 2, splice sessions, or publish
session 2 as a hardware multithread result.

### Approved experiment-instrument correction

Approval recorded in WSL on `2026-07-28`; this is a repository record date, not
board runtime time.

The user approved a separate OpenMP-enabled ncnn build after the audit proved
that the session 2 ELF had no effective operator-parallel backend. This changes
the common experimental instrument used by both thread conditions, not the
between-condition variable. The following remain frozen:

```text
ncnn tag/commit
model, input, thresholds, and PC golden
preprocess, inference, postprocess, and pipeline definitions
five alternating pairs
ten warmups and twenty measured samples per process
five independent processes and one hundred samples per condition
nearest-rank statistics, correctness gates, stability gate, and classification
```

The corrected experiment must use one hash-identical OpenMP-enabled ELF, one
ncnn library, and one private OpenMP runtime for both `configured_threads=1`
and `configured_threads=2`. Standard Linaro libgomp is preferred; simpleomp is
allowed only if standard libgomp fails its build, ABI, dependency, runtime,
correctness, or observed-parallelism gates.

The original session 2 evidence remains byte-preserved under
`results/evidence/018/`. New evidence must use
`results/evidence/018/openmp/`; it must not overwrite or splice the original
session. Task 017 remains immutable and Task 018 remains `In Progress`.

The isolated standard-libgomp build and the preregistered parallel-capability
gate have passed. The selected instrument has `NCNN_OPENMP=ON`,
`NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, `libncnn.a` SHA256
`bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3`,
private `libgomp.so.1` SHA256
`87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91`,
and benchmark ELF SHA256
`19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2`.

The non-formal diagnostic used two warmups and three measured pipelines per
condition. It observed one process thread and CPU-time/wall-time ratio
`0.9926010969416309` for `configured_threads=1`, versus two process threads
and ratio `1.8452701642847376` for `configured_threads=2`. Both conditions
passed correctness before and after measurement. This proves that the
experiment variable is effective; these short measurements are diagnostic
only and are not publishable performance results.

Implementation repairs:

1. The first build-evidence assertion expected `OpenMP_CXX_FOUND` as a
   persistent CMake 3.16 cache BOOL. CMake did not persist that variable. The
   assertion was corrected to use
   `OpenMP_COMPILE_RESULT_CXX_fopenmp=TRUE`, `OpenMP_CXX_FLAGS=-fopenmp`,
   the resolved `OpenMP_gomp_LIBRARY`, compile commands, and final link
   evidence. Rebuild: PASS.
2. A cached idempotent configure did not repeat CMake's one-time
   `Found OpenMP_CXX` console line. The transient console assertion was
   removed in favor of the persistent cache and binary evidence above.
   Rebuild: PASS.
3. The first new-ELF diagnostic rejected `configured_threads=2` before
   inference because the original session config correctly froze
   `OMP_NUM_THREADS=1`. No original file was changed. A separate
   `openmp-v2` config and contract were created before collecting corrected
   data; only `OMP_NUM_THREADS` follows `configured_threads`. Rebuild and both
   short diagnostic runs: PASS.

Validation completed before the corrected formal session:

```text
standard libgomp build/configure/install/export: PASS
ELF64 AArch64 and private libgomp ABI/dependency inspection: PASS
parallel-capability gate: PASS
correctness before/after for both conditions: PASS_TARGET
OpenMP instrument contract and original frozen contract tests: PASS
focused Task 018 tests: PASS (16/16)
model-independent Release build: PASS
model-independent CTest: PASS (4/4)
runner --check and --dry-run: PASS
Task 017 evidence hashes: unchanged
git diff --check: PASS
```
