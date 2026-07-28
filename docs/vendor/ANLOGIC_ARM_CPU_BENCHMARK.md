# Anlogic DR1 ARM CPU benchmark protocol

## Status

Task 017 is `Completed`. The frozen protocol produced one real-board
five-process/100-sample session that passes the automated validator and user
review. It is published as the unoptimized default DR1 CPU-only FP32,
single-thread baseline. The existing Task 014 single-run timings remain
diagnostic and are not benchmark evidence.

## Purpose and baseline

This protocol measures the unoptimized correctness-approved Task 014 pipeline
on the real MLK-F3P-CZ02-DR1M90. It does not compare tuning choices. The
workload is ncnn `20240410` commit
`56775de50990ab7f16627efdcf5529b49541206f`, CPU-only FP32, batch 1,
`640x640`, and one ncnn/OpenCV thread. Vulkan, FP16, BF16 storage, INT8,
video, camera, and NPU are off.

The local vendor asset is identified as `SDK_2025_07`; that identity is not
proof of an exact official repository SDK tag. The CPU benchmark is instead
bound to the verified compiler/sysroot/runtime and board identities preserved
by Tasks 013–015.

## Frozen assets

| Asset | SHA256 |
| --- | --- |
| ncnn manifest | `9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff` |
| ncnn param | `72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4` |
| ncnn bin | `658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0` |
| input | `625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071` |
| inference config | `82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d` |
| PC C++ ncnn golden JSON | `fb343f605218a5fa30a825a3f14e4d00137d6275e1b1af99c9029956e2492fa9` |
| CPU-only static `libncnn.a` | `5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a` |
| benchmark config | `51ffd0db29be98e74767ee5cf5d03d97f8392ebd42749aa4c9c46bb8162f20c1` |

The `.param` and `.bin`, ARM executables, SDK, ncnn source/install tree, and
deployment package stay outside Git.

## Formal process protocol

Five independent processes run in order. Each process loads the same model and
input, records model load separately, performs one untimed golden comparison,
runs 10 warmups, records 20 measured pipelines, repeats the golden comparison,
writes a round fragment, and exits. This gives 100 formal samples:

```text
5 process rounds × 20 measured iterations = 100 samples
```

Each process is new; process ID and process-start timestamp must be unique.
Thread-related environment variables, ncnn threads, and OpenCV threads are
all fixed to one.

## Timing boundaries

The C++ producer reuses the same modules as Task 014:

- preprocess: image letterbox, BGR-to-RGB, normalization, and HWC-to-CHW;
- inference: ncnn input binding, extraction, output validation, and copy;
- postprocess: YOLO decode, confidence filtering, coordinate restoration, and
  class-aware NMS;
- pipeline: the exact integer-nanosecond sum of those three stages.

Image read/decode, model load, correctness, warmup, sysfs sampling, process
startup, rendering, JSON/PNG writes, and transfer are excluded. Frequency and
temperature are sampled after a measured pipeline and therefore are not
included in that pipeline duration; the sampling overhead occurs between
iterations and is retained as a declared measurement limitation.

Formal sampling does not write a PNG or per-iteration log.

## Statistics

The validator independently computes each stage by round and over all 100
samples:

```text
count, mean, nearest-rank P50, nearest-rank P90,
minimum, maximum, sample standard deviation
```

Nearest-rank selects `sorted[ceil(p * count) - 1]`. Sample standard deviation
uses `count - 1`. Sequential batch-1 pipeline FPS is:

```text
1000 / aggregate mean pipeline_ms
```

This is not a mean of per-sample FPS and is not video throughput. The PC
benchmark's 10 percent maximum round-mean spread gate is retained.

## Resources and environment

`getrusage(RUSAGE_SELF).ru_maxrss` records process Peak RSS in KiB. It is a
process high-water mark from startup, not model-only memory. Model load is
recorded in milliseconds but excluded from FPS.

Before and after the campaign the runner records board/ABI identity, CPU count,
memory, uptime, load average, governor, available/current frequency, and thermal
zones. After each formal pipeline the producer records the maximum readable
current CPU frequency and thermal-zone temperature. Missing nodes become JSON
`null` or empty observed lists; they are never invented as zero. The protocol
does not write governor, cpufreq, thermal, affinity, service, or system-image
state.

The board clock was previously unsynchronized. Process ordering therefore uses
the captured round order and monotonic timing, not wall-clock accuracy.

## Correctness and validity

Every process compares before warmup and after measurement against the PC C++
ncnn golden. Both checks require five detections, matching classes, finite
values, valid boxes, minimum class-matched IoU at least `0.99`, and maximum
confidence delta at most `0.01`. The low-confidence earbud-case `mouse` false
positive remains part of the contract.

A nonzero process exit, SSH disconnect, asset-hash mismatch, malformed JSON,
system reboot, or proven collector failure invalidates a round. The failed
stdout, stderr, exit code, and reason remain evidence. A later replacement may
provide the missing valid round. High latency is never an invalidation reason;
all valid samples and outliers remain in the raw dataset.

## Evidence layout

The preregistered contract is
[`benchmark_contract.json`](../../results/evidence/017/benchmark_contract.json).
Its freeze-time `formal_data_collected: false` and
`published_performance_values: false` fields are immutable preregistration
facts, not the current task state. Current collection and publication state is
recorded in the generated summary, validation, task, and manifest.
Formal collection added:

```text
results/evidence/017/
├── benchmark_environment_before.json
├── benchmark_environment_after.json
├── benchmark_raw_samples.json
├── benchmark_summary.json
└── benchmark_validation.json
```

Raw stage durations are authoritative integer nanoseconds. Millisecond fields
are exact derived representations. The validator regenerates summary and
validation files; those values must not be entered manually.

## Formal user-approved baseline

The baseline was collected on the real MLK-F3P-CZ02-DR1M90 using five new
processes and the hash-verified AArch64 executable
`6fc9f99a62ef57231a29bce59657a9cf69bffb1e0a4a329b6e7f64b75ac1512a`.
All 100 valid samples are retained:

| Stage | Mean ms | P50 ms | P90 ms | Min ms | Max ms | Sample SD ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| preprocess | 41.933673 | 41.805690 | 42.164101 | 41.718330 | 43.284000 | 0.395643 |
| inference | 3418.092005 | 3406.781914 | 3411.752194 | 3403.005634 | 3575.035295 | 35.039276 |
| postprocess | 53.966676 | 53.790330 | 54.231390 | 53.733600 | 55.551871 | 0.497635 |
| pipeline | 3513.992354 | 3502.465775 | 3507.337445 | 3498.901385 | 3672.449047 | 35.862174 |

Sequential batch-1 FPS is `0.284576601`. Maximum process Peak RSS is
`142476 KiB`; mean model load is `633.450396 ms` and remains excluded from FPS.
The five round pipeline means differ by `1.688017802%`, passing the frozen 10%
gate. The pipeline mean is about `3.514` seconds per image and inference is the
dominant stage.

Every process passed correctness before warmup and after measurement with five
detections, minimum class-matched IoU `0.999985507578`, and maximum confidence
delta `0.00000500679016113`. Frequency, governor, available-frequency, and
thermal sysfs nodes were unavailable; all 100 per-sample frequency and
temperature observations are JSON `null`, not zero.

The user approved the complete candidate. The approval record is:

```text
human_review: PASS
human_review_source: user
candidate_approved: true
recorded_at: 2026-07-28T18:00:25+08:00
```

That timestamp is the WSL approval record time, not board runtime time. The
board clock was not synchronized. Evidence ordering uses process rounds,
monotonic durations, and WSL record time. The pre-session load average was
`0.09, 0.24, 0.17`; the post-session load average was `1.00, 0.90, 0.58`.
No governor, frequency, system-library, or service setting was changed.

The first collection attempt is retained outside Git because its second process
exposed an append-parser defect after a valid first round. The repaired
executable ran a completely new five-process session; no round from the failed
session was mixed into the approved baseline. The failed attempt is not an
invalid round in the approved session and its evidence was not deleted. A later
checksum-path defect occurred only after board collection and was repaired by
resuming the same accepted session without rerunning any process.

## Entry points

Offline checks do not access the VM or board:

```bash
bash scripts/vendor/run_anlogic_arm_benchmark.sh --check
bash scripts/vendor/run_anlogic_arm_benchmark.sh --dry-run
```

The existing ARM build entry now exports both the Task 014 single-image target
and `edgeai_benchmark_ncnn`. Rebuilding requires WSL and the VM:

```bash
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh --execute
```

Formal board collection requires a separate authorization and WSL plus the
powered board:

```bash
bash scripts/vendor/run_anlogic_arm_benchmark.sh --execute
```

That mode validates hashes, packages the benchmark target and required private
OpenCV libraries, uses an isolated board directory, performs five process
rounds, returns evidence, and runs the deterministic validator. It does not
build ncnn, alter system libraries, or change board power/governor/frequency.

Candidate approval is an explicit WSL-only validator operation; omitting the
approval arguments always regenerates a pending-review candidate:

```bash
python3 scripts/vendor/validate_anlogic_arm_benchmark.py summarize \
  --raw results/evidence/017/benchmark_raw_samples.json \
  --environment-before results/evidence/017/benchmark_environment_before.json \
  --environment-after results/evidence/017/benchmark_environment_after.json \
  --summary results/evidence/017/benchmark_summary.json \
  --validation results/evidence/017/benchmark_validation.json \
  --approve-candidate \
  --human-review-source user \
  --human-review-recorded-at 2026-07-28T18:00:25+08:00
```

The complete candidate stopped for human review and was approved before Task
017 was marked `Completed` and the values above were published.

## Known limitations

- The baseline is one thread, one fixed image, CPU FP32, and one board.
- Frequency and thermal sampling is observational and does not lock the CPU.
- Linux scheduling, background work, ambient conditions, and board warm state
  can influence results.
- Peak RSS is process-level.
- FPS is single-image pipeline throughput, not video throughput.
- The approved result is an unoptimized default baseline, not a tuned result.
- Video, camera, Vulkan, quantization, and NPU remain out of scope; NPU is
  `HOLD`.
