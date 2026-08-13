# Task 034 — ARM ncnn inference-kernel and build optimization

Task 034 profiles the validated DR1M90 ARM CPU path without reopening the NPU
route or changing the frozen YOLOv5n contract. The Task 033 configuration is
the only production baseline: ncnn 20240410, OpenMP, two threads, default
scheduling, packing on, FP32, 640×640 input, confidence 0.25 and NMS IoU 0.45.

## Baseline and boundaries

Task 033's accepted row remains immutable:

| configuration | pipeline mean | inference mean | correctness |
| --- | ---: | ---: | --- |
| threads=2, default, packing=on, FP32 | 1963.817618 ms | 1873.474372 ms | PASS_TARGET |

Inference is 95.399611% of that pipeline. Preprocess and postprocess are not
the next primary optimization targets, and NMS is negligible. Task 034 does
not change the model, input, thresholds, kernel, boot files, board runtime or
NPU state.

## Layer profile

The profiling build enables ncnn's `NCNN_BENCHMARK` facility only in an
isolated diagnostic library. The normal A/B libraries have it disabled, so the
production path and its timing semantics are unchanged. On the board the
profile retained 206 layers over six repeated layer sequences (one initial
result, two warmups and three measured repeats); the structured profiler kept
the three formal samples and passed the unchanged golden.

The measured profile's summed layer time is 1826.823333 ms. Operator totals:

| operator | layers | total layer time | share |
| --- | ---: | ---: | ---: |
| Convolution | 60 | 1467.013333 ms | 80.304% |
| Swish | 57 | 196.483333 ms | 10.755% |
| Sigmoid | 3 | 45.616667 ms | 2.497% |
| Permute | 3 | 37.098333 ms | 2.031% |
| Concat | 17 | 29.723333 ms | 1.627% |
| Reshape | 6 | 24.935000 ms | 1.365% |
| Pooling | 3 | 8.001667 ms | 0.438% |

The ten hottest individual layers are retained in
`results/evidence/034/layer_profile.json`; the first is the 6×6 stride-2
input convolution (`conv_3`, 256.862 ms mean, 14.061% of summed layer time).
The profile run itself is slower than the Task 033 baseline because per-layer
logging is enabled; it is diagnostic evidence, not a replacement benchmark.

## Build audit and A/B

The clean ncnn input is commit
`56775de50990ab7f16627efdcf5529b49541206f` (tag `20240410`), archived with
SHA256 `328fe282b98457d85ab56184fa896467f6bf640d4e48e91fcefc8d31889f92b7`.
The VM uses CMake 3.16.9 and Linaro AArch64 GCC/G++ 7.5.0. All variants are
Release, OpenMP ON, internal threads ON, SimpleOMP OFF, runtime CPU dispatch
ON, VFPV4 and GNU inline assembly ON, BF16 enabled, INT8/Vulkan/LTO disabled,
and explicit `NCNN_VERSION=20240410`.

Candidate A is the same-source/options control (`-O3 -DNDEBUG`,
`NCNN_BENCHMARK=OFF`). Candidate B changes only the compiler tuning flag to
`-mtune=cortex-a35`; an earlier `-mcpu=cortex-a35` attempt was rejected by the
toolchain/source architecture flags and was not accepted. Both successful
variants pass correctness on the board:

| candidate | inference mean | pipeline mean | pipeline P50 | pipeline P95 | FPS | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 1890.049681 ms | 1984.896740 ms | 1983.248720 ms | 1999.116860 ms | 0.503805 | 168136 KiB |
| B (`-mtune=cortex-a35`) | 1901.869501 ms | 1996.950938 ms | 1996.040330 ms | 2010.986300 ms | 0.500763 | 168324 KiB |

B is 0.625371% slower in inference and 0.607296% slower in pipeline, so it
is rejected. A is a correctness-passing control for this audit, not a claim
that its static archive is byte-identical to the historical Task 033 archive
(the latter remains `bd76f70f...`). Full identities are in
`results/evidence/034/build_audit.json` and `build_matrix.json`.

## Graph optimization

The frozen conversion manifest records the same-revision pnnx 20240410 path,
CPU FP32 input, `optlevel=2`, zero unsupported conversion operators, no custom
layers, 207 ncnn layers and 237 blobs. It is therefore recorded as
`ALREADY_OPTIMIZED` for this frozen conversion path. The manifest does not
separately quantify Conv/BN fusion or dead-node elimination, so those are not
claimed independently. No new graph candidate was created.

## PMU and attribution

The board reports two logical AArch64 CPUs (`CPU part 0xd04`) with NEON/ASIMD
features. `perf` is not installed (observed exit code 127), and readable CPU
frequency and thermal sysfs values were unavailable. Consequently cycles,
instructions and cache-miss rates cannot be claimed. The layer distribution
does establish that convolution/kernel throughput is the dominant measured
cost; memory/cache pressure remains unseparated without PMU data.

## Decision

No FP32 build change is accepted beyond the frozen Task 033 runtime profile.
The next useful optimization work, if pursued, should target convolution/kernel
throughput with vendor/toolchain evidence rather than preprocess or NMS. INT8
is not silently enabled here; it is a separate future experiment only if a
representative calibration/accuracy gate and an ARM ncnn INT8 build are
available. No INT8 result is part of Task 034.

Evidence and the reproducible audit helper are kept in:

- `results/evidence/034/`
- `scripts/validate_task034_ncnn_optimization.py`
- `scripts/vendor/audit_task034_ncnn_build.sh`
- `scripts/vendor/run_task034_ncnn_layer_profile.sh`

Large board logs, model files, libraries and build trees remain outside Git.
