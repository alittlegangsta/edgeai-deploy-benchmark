# PC ORT Benchmark Methodology

Task 009 compares the existing Python and C++ ONNX Runtime implementations. It
does not benchmark ncnn, ARM hardware, video I/O, rendering, or encoding. The
results documented below were human-approved on 2026-07-21 as the current formal
PC ORT result for this fixed WSL2 environment and implementation.

## Frozen workload and runtime

The machine-readable source of truth is `configs/benchmark_pc.json`. The workload
is YOLOv5n v7.0 ONNX with its frozen SHA256, the fixed repository reference JPEG
and SHA256, batch 1, FP32, and 640 by 640 input. Both implementations explicitly
use ONNX Runtime 1.18.1 with `CPUExecutionProvider`, one intra-op thread, one
inter-op thread, sequential execution, all graph optimizations, and one OpenCV
thread.

Every command exports `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, and `NUMEXPR_NUM_THREADS=1`. CPU affinity remains scheduler
managed and pinning is disabled. The environment is WSL2, so the result must not
be described as a bare-metal or pinned-physical-core microbenchmark.

## Rounds and lifecycle

Each backend runs five independent processes. Every process loads the config,
reads and decodes the reference image once, constructs one ORT session, records
session/model load time separately, executes 10 full-pipeline warmups, then
records 100 full-pipeline samples before exiting. The decoded BGR image is reused;
the preprocessed tensor is not. Each formal iteration performs preprocessing,
ORT inference, output validation/copy, and complete postprocessing.

The process order is:

1. Python then C++.
2. C++ then Python.
3. Python then C++.
4. C++ then Python.
5. Python then C++.

This produces 500 retained samples per backend. All samples and all outliers are
kept; a slow sample may not be deleted, replaced, or hidden by rerunning.

## Timing boundaries

Each raw sample stores integer nanoseconds for `preprocess`, `inference`,
`postprocess`, and `pipeline_total`. The exact definition is:

```text
pipeline_total_ns = preprocess_ns + inference_ns + postprocess_ns
```

The stage timers use `time.perf_counter_ns` in Python and
`std::chrono::steady_clock` in C++. Millisecond values are derived only by the
common summarizer, after the exact integer relation has been validated.

Image file read/decode, model loading, session creation, drawing, text labels,
image and JSON/CSV writes, video reading, and video encoding are excluded. Model
load time is reported separately and is never included in pipeline latency.

## Statistics, CPU, and memory

`scripts/validate_benchmark.py` is the only statistics implementation used for
both languages. It calculates per-round and 500-sample aggregate mean,
nearest-rank P50, nearest-rank P90, minimum, and maximum. It also reports the
fastest and slowest sample identities and the five-round pipeline-mean relative
difference:

```text
(maximum round mean - minimum round mean) / minimum round mean * 100
```

Pipeline FPS is only:

```text
1000 / aggregate mean pipeline_total_ms
```

It is not the mean of per-sample reciprocal latencies. Each process measures CPU
over exactly its 100 formal pipelines:

```text
process_cpu_percent_one_core_basis =
  100 * delta(process user + system CPU seconds) / delta(wall-clock seconds)
```

Peak RSS is Linux `getrusage(RUSAGE_SELF).ru_maxrss * 1024`. It is a process-level
peak from startup through formal measurement completion, not pure model memory.
Python includes interpreter and imported-module overhead; C++ includes executable
and dynamically loaded library overhead.

## Correctness and review gates

Every process runs an untimed comparison with the approved golden detections
before warmup and after the measurement window. Detection count and class must
match; class-matched IoU must be at least 0.99 and confidence difference at most
0.001. Timed postprocessing may not omit decoding, threshold filtering,
class-aware NMS, coordinate restoration, or clipping.

If either backend's five round means differ by more than 10 percent, or the raw
evidence suggests an obvious system-load anomaly, Task 009 stops for human review.
The preserved data passed that review. No outlier was removed or replaced.

## Approved aggregate results

All values below come from 500 retained formal samples per backend. P50 and P90
use nearest-rank. The columns are mean, P50, P90, minimum, and maximum in
milliseconds.

| Backend | Stage | Mean | P50 | P90 | Min | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Python ORT | preprocess | 3.208576 | 3.143332 | 3.625834 | 2.573579 | 5.031788 |
| Python ORT | inference | 42.185939 | 41.979068 | 43.452668 | 40.109507 | 51.634398 |
| Python ORT | postprocess | 5.171687 | 5.060641 | 5.779656 | 4.423278 | 7.848948 |
| Python ORT | pipeline total | 50.566201 | 50.255584 | 52.321040 | 47.851400 | 61.066230 |
| C++ ORT | preprocess | 1.655221 | 1.621770 | 1.768998 | 1.532662 | 2.144182 |
| C++ ORT | inference | 41.528575 | 41.383756 | 42.836305 | 39.795074 | 44.671321 |
| C++ ORT | postprocess | 3.684627 | 3.642040 | 3.841475 | 3.540840 | 4.740303 |
| C++ ORT | pipeline total | 46.868423 | 46.713867 | 48.182646 | 45.058795 | 50.014768 |

Python pipeline FPS is 19.776055 and C++ pipeline FPS is 21.336327. These values
are calculated from aggregate mean pipeline latency only. They exclude image
file reading, model/session creation, drawing, labels, output writing, and video
I/O or encoding; they are not end-to-end application FPS.

Under the fixed WSL2 CPU benchmark configuration, the C++ ONNX Runtime pipeline
achieved a mean latency of 46.87 ms, compared with 50.57 ms for Python ONNX
Runtime, corresponding to a 7.31% lower mean pipeline latency in this
implementation and environment. This does not establish that the C++ inference
kernel is inherently 7.31% faster, and the difference must not be attributed
entirely to the programming language.

## Interpretation boundaries

Python used OpenCV 4.10.0 and C++ used OpenCV 4.6.0. Detection correctness and
Python/C++ input-tensor alignment passed their frozen tolerances, so this version
difference does not invalidate the approved complete-pipeline comparison. It does
limit any single-cause attribution of the preprocess timing difference.

The CPU metric is `process_cpu_percent_one_core_basis`. ORT intra-op and inter-op
thread counts were both 1, ORT execution was sequential, OpenCV threads were 1,
CPU affinity was scheduler managed, CPU pinning was disabled, and the environment
was WSL2. On this scale, approximately 100% means sustained use of one logical
CPU. The observed values near 111% indicate limited additional thread or
Runtime/system activity in the measurement window. Configuring these libraries
to one thread does not guarantee that the entire process has exactly one thread;
this experiment is not a pinned-physical-core strict single-thread microbenchmark.

Peak RSS is process-level peak memory, not model-only memory. Python includes the
interpreter, imported modules, ONNX Runtime, model, and session. C++ includes the
executable, dynamic libraries, ONNX Runtime, model, and session.

The approved conclusion applies only to this WSL2 instance, frozen model and
image, ORT 1.18.1 CPU provider, thread settings, benchmark implementation, and
recorded code. It must not be generalized to bare-metal Linux, other machines,
ARM, other models, or other runtime/configuration choices.
