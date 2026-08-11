# ARM CPU benchmark and profiling consolidation

Task 030 consolidates the retained, user-approved YOLOv5n v7.0 measurements
from the PC C++ ONNX Runtime CPU path and the DR1M90 recommended dual-thread
ncnn path. The source campaigns are immutable; Task 030 derives a reporting
view and independently recomputes statistics from their raw samples.

## Frozen workload

Both rows use the same fixed reference image
(`625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071`), batch 1,
FP32 `640x640` input, confidence threshold `0.25`, NMS IoU `0.45`, COCO-80,
and the no-in-graph-NMS YOLOv5n v7.0 contract `[1,3,640,640] -> [1,25200,85]`.
The ONNX model SHA256 is
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121` and the
source-weights SHA256 is
`4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3`.

The PC row is C++ ONNX Runtime 1.18.1 `CPUExecutionProvider` on WSL2. The ARM
row uses ncnn 20240410 with the Task 019 `recommended-dual-thread` OpenMP
profile (`NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, private
libgomp, configured threads 2). ARM uses the validated ncnn param/bin
representation of the same frozen weights; it does not claim the serialized
ONNX and ncnn files are byte-identical.

## Protocol and resource definitions

Each source process performs 10 warmups and repeated timed pipelines. The timed
boundaries are shared preprocessing, inference-only, shared postprocessing, and
their exact sum:

```text
pipeline_ns = preprocess_ns + inference_ns + postprocess_ns
```

Image decode, model/session creation, correctness checks, drawing, and output
writes are excluded from the pipeline and model load is reported separately.
Mean, nearest-rank P50/P95, minimum, maximum, and sample standard deviation use
the retained raw samples. FPS is `1000 / mean pipeline_ms`, never a mean of
per-sample reciprocal latencies. CPU utilization is process user+system
CPU-time delta divided by wall time on a one-core basis. Peak RSS is a
process-level high-water mark. Missing CPU-frequency and temperature readings
remain JSON `null`/unavailable.

The historical source campaign sizes are intentionally preserved: PC C++ ORT
has 6 independent processes × 100 samples (600), while ARM Task 018 has 5
independent processes × 20 samples (100). The common metric definitions make
the reports reproducible; different sample counts and environments remain
visible and are not silently normalized.

## Consolidated results

All values below are generated from and independently checked against
`results/evidence/030/pc_ort_benchmark.json` and
`results/evidence/030/arm_ncnn_benchmark.json`.

### PC C++ ORT (WSL2)

| Stage | Mean (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Sample SD (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Preprocess | 1.833570 | 1.790252 | 2.082433 | 1.637727 | 3.411278 | 0.142056 |
| Inference | 45.849137 | 45.639122 | 48.349684 | 43.224541 | 59.337732 | 1.424131 |
| Postprocess | 4.120279 | 4.036812 | 4.577968 | 3.922701 | 5.334411 | 0.203793 |
| Pipeline | 51.802986 | 51.595426 | 54.415443 | 48.863992 | 65.671301 | 1.503313 |

Aggregate FPS is `19.303906657`. Mean process CPU utilization is
`99.998405%` (one-core basis). Peak RSS is `150869.33 KiB` mean and
`151444 KiB` maximum. CPU frequency and temperature were not recorded by the
retained PC campaign.

### ARM ncnn, recommended dual-thread (DR1M90)

| Stage | Mean (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Sample SD (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Preprocess | 43.436489 | 44.324130 | 44.467111 | 41.822460 | 44.580390 | 1.171130 |
| Inference | 1871.134707 | 1873.266138 | 1877.160108 | 1863.085099 | 1877.905069 | 4.648583 |
| Postprocess | 54.830994 | 55.467840 | 55.580611 | 53.755890 | 55.662571 | 0.836261 |
| Pipeline | 1969.402190 | 1973.123870 | 1977.062930 | 1958.800699 | 1977.787789 | 6.577660 |

Aggregate FPS is `0.507768299`. Mean process CPU utilization is
`185.373995%` (one-core basis), consistent with the configured two-thread
OpenMP profile. Peak RSS is `142601.6 KiB` mean and `142668 KiB` maximum.
CPU-frequency and temperature samples are present as JSON `null` for all 100
samples, so no frequency or thermal claim is made.

## Correctness and interpretation

Both rows pass their retained before/after checks with five detections,
finite/valid boxes, class agreement, and the frozen IoU/confidence gates. ARM
minimum class-matched IoU is `0.9999855075776749` and maximum confidence delta
is `0.0000050067901611328125`; the PC C++ ORT checks are exact against their
approved golden (`IoU=1.0`, confidence delta `0.0`).

The PC and ARM values are separate environment/backend results, not a direct
hardware speedup comparison. They differ in CPU architecture, operating
system, runtime, serialized model representation, process count, and historical
campaign size. Task 017's OpenMP-off ARM result remains an immutable historical
reference and is not mixed into the recommended dual-thread row.

## Backend status matrix

| Backend | Status | Meaning |
| --- | --- | --- |
| PC C++ ORT YOLOv5n | `BENCHMARKED_CORRECT` | CPU benchmark above |
| ARM ncnn YOLOv5n | `BENCHMARKED_CORRECT` | CPU benchmark above |
| DR1 vendor face NPU control | `FUNCTIONAL_CONTROL_ONLY` | Task 026 one-shot control model; not YOLOv5n and not benchmarked |
| DR1 YOLOv5n NPU | `NOT_BENCHMARKED` | Task 028/029 remains an external vendor dependency; no NPU FPS claim |

The face NPU control is never used as a proxy for YOLOv5n NPU performance.

## Reproduction

Run the independent consolidation validator from the repository root:

```bash
python3 scripts/validate_task030_benchmark_consolidation.py
```

It reads only the retained Task 012 PC C++ ORT and Task 018 ARM raw evidence,
checks stage-sum equations and frozen identities, recomputes P50/P95/FPS/resource
statistics, and verifies the NPU status boundary. The source evidence and all
large models/binaries remain outside the new Task 030 files.
