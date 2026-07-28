# Anlogic DR1 ARM CPU threading experiment

## Status

Task 018 is `Completed`. The user approved the corrected OpenMP-enabled
real-board session as `BENEFICIAL` after independent validation of 10 valid
processes and 200 retained samples. The earlier OpenMP-off session remains
byte-preserved as thread-parameter sensitivity evidence and is invalid for
multithread performance comparison. Task 017 remains the immutable approved
one-thread historical baseline and is not a direct Task 018 experimental group.

## Question and only variable

The experiment asks whether configuring the frozen ncnn CPU pipeline with two
threads changes correctness, latency, throughput, stability, and process Peak
RSS relative to a contemporaneous one-thread run on the real
MLK-F3P-CZ02-DR1M90.

```text
only variable: configured_threads = 1 or 2
```

Both conditions use the same executable, board directory, ncnn `20240410`
commit `56775de50990ab7f16627efdcf5529b49541206f`, CPU FP32 path, batch 1,
`640x640` input, model, image, thresholds, OpenCV thread count, environment
variables, timing boundaries, and statistics. The runner does not modify CPU
affinity, governor, frequency, thermal state, services, or system libraries.

The local vendor asset identity is `SDK_2025_07`; it is not evidence of an exact
official repository SDK tag match. This experiment is bound to the already
validated compiler, sysroot, ELF, runtime, and board identities instead.

## Frozen assets

| Asset | SHA256 |
| --- | --- |
| ncnn manifest | `9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff` |
| ncnn param | `72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4` |
| ncnn bin | `658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0` |
| fixed input | `625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071` |
| inference config | `82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d` |
| PC C++ ncnn golden | `fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9` |
| Task 018 config | `901628d80a63ee5fa34d8a62db21d65796bb9e8c6284207c2490dc44379d13f9` |
| execution order | `cf924d46e6bac1bba342ab9aac93bb62ad1703b81cca9aa443e84643e8d1c8a4` |

Model binaries, the rebuilt ARM ELF, private OpenCV libraries, deployment
package, and full logs remain outside Git.

## Paired schedule

Task 018 remeasures one thread instead of reusing Task 017 values. This controls
for date, background load, and warm/thermal state and permits alternating
within each pair:

| Pair | First process | Second process |
| ---: | --- | --- |
| 1 | threads 1 | threads 2 |
| 2 | threads 2 | threads 1 |
| 3 | threads 1 | threads 2 |
| 4 | threads 2 | threads 1 |
| 5 | threads 1 | threads 2 |

Each table cell is a new process: golden correctness, 10 warmups, 20 measured
pipelines, golden correctness, then exit. Each condition therefore has five
processes and 100 samples; the experiment has 10 processes and 200 samples.
Pair, execution order, condition, process ID, model load, Peak RSS, environment,
stderr, exit code, and raw timings are retained.

## Timing and resources

The shared Task 014/017 path remains:

- preprocess: image letterbox, BGR-to-RGB, normalization, HWC-to-CHW;
- inference: ncnn input, extract, validation, and output copy;
- postprocess: decode, confidence filtering, coordinate restoration, NMS;
- pipeline: exact integer-nanosecond sum of the three stages.

Image decode, model load, correctness checks, warmup, sysfs reads, process
startup, serialization, and transfer are excluded. Model load and Peak RSS are
reported separately. Frequency and temperature observations are outside timed
pipelines. An unavailable sensor is JSON `null`, never zero.

## Statistics and comparison

Each condition independently uses count, mean, nearest-rank P50/P90, minimum,
maximum, sample standard deviation, aggregate-mean pipeline FPS, model-load
statistics, maximum Peak RSS, and the five-round pipeline-mean spread.

```text
pipeline_speedup = threads1 mean pipeline / threads2 mean pipeline
inference_speedup = threads1 mean inference / threads2 mean inference
fps_gain_percent = (threads2 FPS / threads1 FPS - 1) * 100
rss_change_percent = (threads2 Peak RSS / threads1 Peak RSS - 1) * 100
```

The validator reads raw samples and recomputes every value; it does not trust a
producer summary. Peak RSS change is disclosed without a post-hoc rejection
threshold.

## Correctness and stability

Every process must pass before/after correctness against the PC ncnn golden:
exit zero, five detections, matching classes, finite values, valid boxes,
minimum IoU `>= 0.99`, and maximum confidence delta `<= 0.01`. Task 018 raw
rounds also carry the five small detection snapshots, allowing the validator to
class-match one-thread and two-thread output directly.

The Task 017 `10%` maximum round-mean spread gate applies independently to each
condition. A slow valid sample remains in the dataset. A failed process retains
its attempt evidence and can be replaced only as a complete process for that
same pair/condition.

## Result classification

- `BENEFICIAL`: correctness and both stability gates pass, pipeline speedup is
  at least `1.05`, two-thread P90 is no worse, and no dependency/system change
  occurred.
- `NEUTRAL`: correctness and stability pass and speedup is from `0.98`
  inclusive to `1.05` exclusive.
- `REGRESSION`: speedup is below `0.98`; correctness, stability, or runtime
  safety fails; or an average speedup of at least `1.05` has worse two-thread
  P90 tail latency.

The classification records the result; it does not guarantee that two threads
will help.

## Historical consistency

Task 017 remains:

```text
pipeline mean: 3513.99235361 ms
FPS: 0.2845766010198282
```

The contemporaneous Task 018 one-thread mean is compared against it. Absolute
mean drift above `10%` produces `WARNING_ENVIRONMENT_DRIFT`; it does not delete
samples, alter Task 017, or by itself decide the thread comparison.

## Entry points and evidence

Offline modes do not call VM/board wrappers:

```bash
bash scripts/vendor/run_anlogic_arm_threading_experiment.sh --check
bash scripts/vendor/run_anlogic_arm_threading_experiment.sh --dry-run
```

The authorized collection turn rebuilt the shared AArch64
`edgeai_benchmark_ncnn` target, created an isolated package and board path,
executed the frozen schedule, retained failed attempts, returned hash-checked
raw files, and called the validator. It did not reuse or overwrite
`results/evidence/017/`. Do not rerun collection merely to complete human
review; approval is an offline decision over the preserved candidate.

Preregistered evidence:

- [`experiment_contract.json`](../../results/evidence/018/experiment_contract.json)
- [`execution_order.json`](../../results/evidence/018/execution_order.json)

Reserved formal evidence:

```text
threads1_raw_samples.json
threads2_raw_samples.json
process_environment.json
threads1_summary.json
threads2_summary.json
comparison_summary.json
experiment_validation.json
```

Those seven formal files now contain the complete session 2 candidate.
Synthetic fixtures live only in temporary unittest objects and are not
performance evidence.

## Automatic candidate

Recorded in WSL at `2026-07-28T19:38:35+08:00`. This is evidence record time,
not board runtime time; the board clock was unsynchronized.

The hash-verified executable is
`40fdd3b777fccaf3bd45f3a9c59842de53e7bf42bcbd285fa73c37b86b457f2a`.
It is ELF64 AArch64, uses `/lib/ld-linux-aarch64.so.1`, requires at most
`GLIBC_2.17`, and resolved all private OpenCV 4.7 and board system dependencies.
Both conditions used this same executable.

Each table row is independently recomputed from all 100 retained samples:

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

| Metric | Threads 1 | Threads 2 |
| --- | ---: | ---: |
| Sequential batch-1 FPS | 0.281507347 | 0.281633276 |
| Maximum Peak RSS KiB | 142572 | 142872 |
| Model-load mean ms | 644.903274 | 647.948484 |
| Model-load min ms | 630.293556 | 635.196576 |
| Model-load max ms | 675.432396 | 658.532376 |
| Five-round mean spread | 3.343810% (`PASS`) | 3.279149% (`PASS`) |

The paired comparison is:

```text
pipeline_speedup: 1.0004473392268058
inference_speedup: 1.000657684049391
fps_gain_percent: 0.04473392268058429
rss_change_percent: 0.2104199983166355
raw statistical classification: NEUTRAL
validator status: PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW
```

That `NEUTRAL` value is the unchanged output of the preregistered statistical
classifier. It is not the publication classification after the build-capability
audit.

Both conditions pass correctness before and after every process with five
detections, minimum golden IoU `0.9999855075776749`, and maximum confidence
delta `0.0000050067901611328125`. Their captured detections match each other
exactly (`IoU=1.0`, confidence delta `0.0`). The contemporaneous one-thread
pipeline mean differs from Task 017 by `1.090292742%`, passing the historical
10% drift check.

All 200 per-sample frequency and temperature observations are JSON `null`
because those sysfs nodes were unavailable. The 20 process environment events
retain observed load averages. No governor, frequency, affinity, service,
system library, model, threshold, or Runtime setting was modified.

The first collection session is preserved outside the formal candidate. Pair 1
completed, then pair 2's two-thread process exposed a producer append-validator
defect on three retained attempts. That session was not spliced with later
data. After correcting the Task 018 round marker and rebuilding a new ELF,
session 2 restarted at pair 1 in a new board/shared directory and completed
10/10 processes with no invalid attempt.

Candidate evidence:

- [`threads1_raw_samples.json`](../../results/evidence/018/threads1_raw_samples.json)
- [`threads2_raw_samples.json`](../../results/evidence/018/threads2_raw_samples.json)
- [`process_environment.json`](../../results/evidence/018/process_environment.json)
- [`threads1_summary.json`](../../results/evidence/018/threads1_summary.json)
- [`threads2_summary.json`](../../results/evidence/018/threads2_summary.json)
- [`comparison_summary.json`](../../results/evidence/018/comparison_summary.json)
- [`experiment_validation.json`](../../results/evidence/018/experiment_validation.json)

## Fixed-revision thread-backend audit

The user withheld approval because the frozen Task 013 build recorded
`NCNN_OPENMP=OFF`. The audit used the exact ncnn `20240410` commit
`56775de50990ab7f16627efdcf5529b49541206f`, not a current branch.

Source-code facts:

- the root CMake file defines `NCNN_OPENMP`, `NCNN_SIMPLEOMP`, and
  `NCNN_THREADS` as separate options;
- ARM inference operators contain OpenMP parallel-for regions parameterized by
  `opt.num_threads`;
- `NCNN_SIMPLEOMP` implements a minimal OpenMP runtime only when the OpenMP
  compilation path is enabled;
- `NCNN_THREADS` provides pthread-backed mutex, condition variable, thread, and
  thread-local-storage primitives. It is not a separate operator
  parallel-for backend;
- the application correctly writes `network.opt.num_threads` before
  `load_param`, but that value cannot activate compiled-out OpenMP regions.

The real VM build records:

```text
NCNN_OPENMP=OFF
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
OpenMP_CXX_FOUND=NOT_EVALUATED_BECAUSE_NCNN_OPENMP_OFF
```

Its ncnn compile flags contain `-pthread` but not `-fopenmp`. The installed
`platform.h` defines `NCNN_THREADS 1` and `NCNN_SIMPLEOMP 0`; the installed
CMake config records `NCNN_OPENMP OFF`. `libncnn.a` has pthread mutex/TLS
references but no GOMP, libomp, or kmp symbols. Although the archive contains
`simpleomp.cpp.o`, that guarded object has no implementation symbols in this
build. The final executable link uses `-pthread` and no `libgomp` or `libomp`.

The capability-aware diagnostic rebuild has SHA256
`46b2b33d6854ec20dc9922d884f38d5df81c348699cbd4da4c1466f1faa39578`.
It is ELF64 AArch64, uses `/lib/ld-linux-aarch64.so.1`, requires at most
`GLIBC_2.17`, and reports:

```json
{
  "ncnn_openmp_compiled": false,
  "ncnn_threads_compiled": true,
  "ncnn_simpleomp_compiled": false,
  "compiler_openmp_macro_defined": false,
  "effective_parallel_backend": "none"
}
```

Two isolated short diagnostics used the unchanged model, input, pipeline, and
correctness gates. Each performed two warmups and three measured pipelines;
these are diagnostic observations, not formal benchmark values:

| Configured threads | Internal threads before/after | External maximum | CPU time / wall time | Correctness |
| ---: | --- | ---: | ---: | --- |
| 1 | 1 / 1 | 1 | 0.992759102 | `PASS_TARGET` |
| 2 | 1 / 1 | 1 | 0.968817704 | `PASS_TARGET` |

The first external monitor attempt had a shell-quoting defect and recorded
zeroes. It remains preserved outside Git. A separate retry corrected only the
monitor command, wrote new evidence paths, and observed one process thread for
both conditions. The application-level CPU and thread evidence was already
valid in the first attempt.

Audit evidence:

- [`thread_backend_audit.json`](../../results/evidence/018/thread_backend_audit.json)
- [`thread_diagnostic_threads1.json`](../../results/evidence/018/thread_diagnostic_threads1.json)
- [`thread_diagnostic_threads2.json`](../../results/evidence/018/thread_diagnostic_threads2.json)

The combined source, CMake-cache, generated-header, compile/link, symbol, CPU
time, and `/proc` observations establish:

```text
OPENMP_OFF_THREAD_PARAMETER_SENSITIVITY: PASS
MULTITHREAD_PERFORMANCE_COMPARISON: INVALID
publication classification: INVALID_FOR_MULTITHREAD_PERFORMANCE_COMPARISON
```

Session 2 remains complete and byte-preserved. Its raw classifier result remains
`NEUTRAL`, but it must not be presented as evidence that hardware two-thread
execution is neutral.

## Historical post-audit boundary

At this audit point, the original automatic collection was retained,
`human_review` was `PENDING`, `candidate_approved` was `false`, and Task 018
remained `In Progress`. The subsequently approved instrument correction and
paired OpenMP session are recorded below. Neither changed Task 017 nor spliced
the original session.
Video, camera, affinity tuning, NEON rewriting, Vulkan, FP16/BF16/INT8 runtime,
quantization, NPU, and system modification remain out of scope. NPU remains
`HOLD`.

## Approved experiment-instrument correction

The user approved a new, isolated OpenMP-enabled ncnn build. This corrects the
instrument shared by both thread conditions; it does not change the sole
experimental variable, `configured_threads`.

The statistical protocol, alternating order, sample counts, timing boundaries,
correctness/stability gates, classification rules, frozen assets, and PC golden
remain unchanged. Both conditions must use the same new ELF, ncnn archive, and
private OpenMP runtime. The standard Linaro libgomp route has priority;
simpleomp is a fallback only if standard libgomp fails a technical gate.

Original session 2 remains under `results/evidence/018/` with publication
classification `INVALID_FOR_MULTITHREAD_PERFORMANCE_COMPARISON`. Corrected
evidence uses the separate `results/evidence/018/openmp/` namespace. Neither
Task 017 nor the original session may be rewritten, deleted, or spliced into
the corrected session.

The preferred standard-libgomp route passed its build, ABI, private dependency,
correctness, and observed-parallelism gates, so the simpleomp fallback was not
used. The selected build has `NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, and
`NCNN_SIMPLEOMP=OFF`; its benchmark ELF SHA256 is
`19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2`.

The short diagnostic was not a formal benchmark. With the same ELF and private
libgomp, the one-thread run observed one process thread and CPU/wall ratio
`0.9926010969416309`; the two-thread run observed two process threads and
ratio `1.8452701642847376`. Both passed the frozen correctness gate. Together
with the compiler macros, link evidence, and `ldd` result, this is sufficient
to proceed with a new complete paired session.

## Corrected OpenMP candidate session

The corrected session used one hash-identical ELF and private libgomp for both
conditions. All ten independent processes completed without an invalid attempt;
each condition retained five processes and 100 formal samples. No outlier or
slow sample was removed.

| Metric | threads=1 | threads=2 |
| --- | ---: | ---: |
| Preprocess mean (ms) | 43.220097 | 43.436489 |
| Inference mean (ms) | 3535.475920 | 1871.134707 |
| Postprocess mean (ms) | 55.509524 | 54.830994 |
| Pipeline mean (ms) | 3634.205540 | 1969.402190 |
| Pipeline P50 (ms) | 3635.311207 | 1973.123870 |
| Pipeline P90 (ms) | 3640.145197 | 1976.094379 |
| Pipeline FPS | 0.275163 | 0.507768 |
| Peak RSS maximum (KiB) | 142796 | 142668 |
| Model load mean (ms) | 657.063877 | 584.943234 |
| Five-round mean spread | 0.370811% | 0.824824% |

The complete formal pipeline distribution is:

| Condition | Mean ms | P50 ms | P90 ms | Min ms | Max ms | Sample SD ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| threads=1 | 3634.205540 | 3635.311207 | 3640.145197 | 3626.020746 | 3641.313787 | 4.527992 |
| threads=2 | 1969.402190 | 1973.123870 | 1976.094379 | 1958.800699 | 1977.787789 | 6.577660 |

The independently recomputed comparison is:

```text
pipeline speedup: 1.845334365110893
inference speedup: 1.8894823055760568
FPS gain: 84.53343651108935%
Peak RSS change: -0.08963836522031254%
cross-condition correctness: PASS_TARGET
minimum cross-condition class-matched IoU: 1.0
maximum cross-condition confidence delta: 0.0
threads=1 stability: PASS
threads=2 stability: PASS
automatic candidate classification: BENEFICIAL
```

The contemporaneous one-thread pipeline mean differs from the Task 017
historical mean by `3.4209860034698747%`, within the preregistered 10% warning
threshold. This is a historical consistency check only because Task 017 used a
different ncnn build without effective operator parallelism.

The board exposed no readable cpufreq or thermal values, so those sample fields
remain JSON `null`. Load average progressed from `0.08, 0.07, 0.03` in the
first before-event to `1.64, 1.28, 0.86` in the final after-event. The runner
did not modify governor, frequency, affinity, services, or system libraries.
The shared experiment instrument includes private `libgomp.so.1` in its
isolated deployment directory; it is explicitly recorded as a shared private
runtime, not as a condition-specific dependency or a system installation.

## User-approved formal result

The user approved the corrected candidate at
`2026-07-28T21:24:36+08:00`. This timestamp is the WSL approval record time,
not board runtime time; Codex did not perform the human review.

```text
validator_status: PASS
classification: BENEFICIAL
human_review: PASS
human_review_source: user
candidate_approved: true
Task 018: Completed
```

With the same OpenMP-enabled ncnn `20240410` build, private libgomp, frozen
model/input, and timing boundaries, changing only `configured_threads` from
one to two reduced mean pipeline latency from `3634.205540 ms` to
`1969.402190 ms`. This is `1.845334365110893x` pipeline speedup and
`84.53343651108935%` FPS gain. It is a beneficial result, not ideal `2x`
linear scaling: serial preprocessing and postprocessing, thread scheduling,
and other nonparallel work remain.

The build identity is:

```text
NCNN_OPENMP=ON
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
effective_parallel_backend=openmp
libncnn.a SHA256=bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3
private libgomp.so.1 SHA256=87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
benchmark ELF SHA256=19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2
```

The private runtime was used only through the isolated package and
`LD_LIBRARY_PATH`; no board system library was replaced. The board clock was
unsynchronized, and all 200 frequency and temperature fields remain JSON
`null`, never zero.

Original session 2 remains separately retained and invalid for multithread
performance comparison. It is not merged with or reclassified by this
corrected candidate.
