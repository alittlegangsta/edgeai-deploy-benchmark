# Task 033 — ARM CPU performance optimization

Task 033 is a correctness-first profiling and optimization track for the
already validated DR1M90 ARM ncnn YOLOv5n v7.0 CPU pipeline. It does not reopen
the frozen NPU vendor handoff from Tasks 028/029/031/032 and does not modify
the Task 017/018/030 evidence.

## Frozen comparison

Every run uses the same ncnn 20240410 model representation, fixed reference
image, 640x640 FP32 input, shared letterbox preprocessing, confidence 0.25,
class-aware NMS IoU 0.45, and the existing five-detection golden. Model load,
image read/decode, visualization and output writes are outside the timed
pipeline. The profiler reports both the historical pipeline sum and an
end-to-end wall-clock sample so any boundary drift is visible.

## Profiler

`edgeai_arm_cpu_profiler` is deliberately separate from the completed formal
benchmark executable. It records preprocessing, ncnn inference, decode, NMS,
postprocess, pipeline and end-to-end timings, process CPU time/utilization,
RSS, process thread count, affinity mask, ncnn build capability, and readable
frequency/temperature values. The extended runtime options are only available
through this Task 033 entry point; the historical integer `NcnnDetector`
constructor keeps its 1/2-thread contract.

Example command (the measured invocation must reference actual board paths and
be retained with its output):

```text
edgeai_arm_cpu_profiler \
  --manifest model/ncnn_manifest.json \
  --config config/yolov5n_v7_inference.json \
  --input input/pc_reference.jpg \
  --reference config/cpp_ncnn_reference.json \
  --output results/task033-threads2.json \
  --threads 2 --warmup 3 --repeat 10 \
  --affinity default --packing on
```

The validator independently recomputes stage summaries using nearest-rank P50
and P95, checks pipeline reconciliation, and rejects any sample that fails the
unchanged golden gate. Host smoke evidence is explicitly a build/API smoke,
not an ARM performance result. Real ARM rows will be added only after a
successful VM cross-build and board run; no result is inferred from the host.

The retained Task 018 dual-thread source currently provides a provisional
attribution reference: inference is about 95.01% of its 1969.40219014 ms
pipeline mean, preprocessing about 2.21%, and shared postprocess about 2.78%.
That source did not instrument decode and NMS separately, so the split remains
pending the Task 033 ARM profiler and is recorded as reference-only evidence in
`results/evidence/033/historical_arm_baseline_reference.json`.

## ARM measurements and accepted configuration

The board was measured after the VM-side AArch64 Release build. The board
reported AArch64, Linux `6.1.111-rt42`, two logical CPUs (Cortex-A53 class
`CPU part 0xd04`), ncnn `1.0.20240410`, `NCNN_OPENMP=ON`, and the OpenMP
backend. Every retained row passed the unchanged five-detection golden gate;
the raw JSON rows and exact commands are in
`results/evidence/033/experiment_matrix.json`.

The same-session default-scheduling comparison was:

| configuration | mean pipeline | P50 | P95 | FPS | inference mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 thread, packing on | 3514.946744 ms | 3513.318755 ms | 3527.416265 ms | 0.284499 | 3423.222259 ms |
| 2 threads, packing on | 1963.817618 ms | 1962.758989 ms | 1976.066480 ms | 0.509212 | 1873.474372 ms |

This yields a 1.789854x pipeline speedup, 78.985396% FPS gain, and 1.827205x
inference-only speedup. Peak RSS changed from 167860 KiB to 168064 KiB
(+0.121530%). The best row remains CPU-only; it is not an NPU or camera
benchmark and does not replace the Task 017/018 formal evidence.

Preprocess, inference, decode, NMS, postprocess and end-to-end timings are
recorded per sample. In the accepted rows, inference is the dominant cost
(95.3996% of the two-thread pipeline mean); decode is about 53.821807 ms and
NMS about 0.015582 ms. The main actionable change is the validated OpenMP
thread count of two. Explicit CPU0 or both-core affinity, packing off, and
FP16 packed/storage/arithmetic options all passed correctness but were slower
in this session, so they were not accepted as optimizations. Threads 3 and 4
were not run because the board exposes only two logical CPUs. Frequency and
thermal sysfs readouts were unavailable and are recorded as unavailable rather
than inferred.

The profiling tool deliberately keeps the historical benchmark executable and
protocol unchanged. The NPU YOLOv5n track remains frozen at
`WAITING_FOR_VENDOR_INPUT` and is `NOT_BENCHMARKED`.

## Planned experiment matrix

The DR1M90 topology is observed before selecting thread candidates. At least
1/2/3/4 are considered, but candidates exceeding the available topology are
recorded as skipped rather than silently oversubscribing the board. For each
meaningful thread count, default scheduling is compared with explicit CPU
affinity. Packing and FP16 storage/arithmetic are independent A/B options and
are accepted only after the same golden gate passes. All baseline, rejected,
and intermediate outputs remain retained.

NPU YOLOv5n remains `NOT_BENCHMARKED` and no CPU fallback is accepted anywhere
in the NPU workstream.
