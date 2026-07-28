# Anlogic DR1 ARM CPU threading experiment

## Status

Task 018 is `In Progress`. The paired protocol, shared producer extension,
offline runner, deterministic validator, and synthetic fixtures are frozen.
Formal collection is `Pending`; this document contains no new measured ARM
performance value. Task 017 remains the immutable approved one-thread
historical baseline.

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

A later authorized `--execute` turn must first rebuild the shared AArch64
`edgeai_benchmark_ncnn` target because the old ELF predates explicit Task 018
thread metadata. The runner then creates a new isolated package and board path,
executes the frozen schedule, retains failed attempts, returns hash-checked raw
files, and calls the validator. It does not reuse or overwrite
`results/evidence/017/`.

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

Those seven formal files do not exist yet. Synthetic fixtures live only in
temporary unittest objects and are not performance evidence.

## Current boundaries

No VM or board was accessed, no AArch64 target was rebuilt, and no performance
sample was collected during protocol freeze. Video, camera, affinity tuning,
NEON rewriting, Vulkan, FP16/BF16/INT8 runtime, quantization, NPU, and system
modification remain out of scope. NPU remains `HOLD`.
