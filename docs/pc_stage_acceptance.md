# PC Stage Acceptance Report — Checkpoint C

Status: **PC STAGE 1 COMPLETED; CHECKPOINT C APPROVED**

This report is generated from the approved first complete Task 012 six-round
campaign. The final document, matrix, risk statements, and Checkpoint C are
human-approved. This completion is not authorization to begin the ARM stage.

## Model relationship

The two ONNX Runtime implementations use the same frozen ONNX model. The ncnn implementation uses a separately frozen TorchScript-to-pnnx model generated from the same YOLOv5n v7.0 weights and validated for semantic equivalence.

## Benchmark boundaries

Each backend has six independent processes, 10 warmups per process, 100 measured
pipelines per process, and 600 retained samples. Pipeline total is the exact sum
of preprocess, inference, and postprocess. It excludes image read, model/runtime
load, drawing, labels, file writes, and video I/O/encoding. Pipeline FPS is
`1000 / aggregate mean pipeline_total_ms`. P50/P90 are nearest-rank.

## Final PC performance

| Backend | Pipeline mean (ms) | P50 | P90 | Min | Max | Pipeline FPS | Six-round spread | Position spread |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Python ORT | 54.881306 | 54.640382 | 56.898155 | 51.590660 | 65.453303 | 18.221141 | 3.098913% | 1.156671% |
| C++ ORT | 51.802986 | 51.595426 | 53.627128 | 48.863992 | 65.671301 | 19.303907 | 3.221212% | 1.383173% |
| C++ ncnn | 77.865349 | 77.618684 | 80.776143 | 73.478461 | 85.075339 | 12.842683 | 1.727134% | 0.438557% |

## Stage analysis

| Backend | Preprocess mean (ms) | Inference mean (ms) | Postprocess mean (ms) | Pipeline mean (ms) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 3.356562 | 45.898201 | 5.626543 | 54.881306 |
| C++ ORT | 1.833570 | 45.849137 | 4.120279 | 51.802986 |
| C++ ncnn | 1.815537 | 71.941530 | 4.108283 | 77.865349 |

Under this fixed WSL2 configuration, C++ ORT has the lowest complete-
pipeline mean at `51.802986 ms`, which is `5.61%`
lower than Python ORT. Python ORT and C++ ORT inference means are
`45.898201 ms` and
`45.849137 ms`, a difference of about
`0.11%`; the observed C++ pipeline advantage is
therefore concentrated in this implementation's preprocess and postprocess
overheads, not evidence that C++ or the ORT inference kernel is universally
faster.

C++ ncnn records `77.865349 ms`, `50.31%` above
C++ ORT for the complete pipeline. Its inference mean is
`71.941530 ms`, `56.91%`
above C++ ORT in this campaign. This is specific to the fixed x86 CPU, WSL2,
runtime versions, model-conversion path, build, and input; it predicts neither
another PC nor ARM behavior.

## Running-position effect

| Backend | Position 1 mean (ms) | Position 2 mean (ms) | Position 3 mean (ms) | Position spread |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 54.472042 | 55.102104 | 55.069772 | 1.156671% |
| C++ ORT | 52.163539 | 51.451871 | 51.793547 | 1.383173% |
| C++ ncnn | 77.956484 | 77.649513 | 77.990051 | 0.438557% |

All position groups contain 200 samples. The measured position spreads are
diagnostic; all samples remain in the aggregate result.

## Fresh correctness

- Python ORT versus C++ ORT: minimum IoU
  `0.999999982537`, maximum
  confidence delta
  `1.64833068306e-08`.
- C++ ORT versus C++ ncnn: minimum IoU
  `0.999997080011`, maximum
  confidence delta
  `2.02655792236e-06`.
- All three contain the same five classes/detections. The earbud-case low-
  confidence `mouse` is a known shared model false positive.
- The three fresh annotated images are human-approved and byte-identical with
  SHA256 `57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.

## CPU and Peak RSS

| Backend | Model load range (ms) | Process CPU range (%) | Peak RSS range (bytes) | Peak RSS range (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 27.340525–34.602837 | 99.942096–99.972122 | 178225152–181420032 | 170.0–173.0 |
| C++ ORT | 53.144442–54.676551 | 99.996220–100.000091 | 153935872–155078656 | 146.8–147.9 |
| C++ ncnn | 30.798871–32.886271 | 99.988997–99.998528 | 187768832–188178432 | 179.1–179.5 |

CPU is `process_cpu_percent_one_core_basis`, not whole-machine utilization.
Configured thread count 1 does not restrict the process to one OS thread. Peak
RSS is full-process peak memory, including language/runtime/library/model/input
costs, and is not pure model memory.

## Acceptance matrix

| Task | Repository state | Automatic evidence | Human review | Evidence |
| ---: | --- | --- | --- | --- |
| 001 | Completed | PASS | APPROVED | `tasks/001_project_bootstrap.md` |
| 002 | Completed | PASS | APPROVED | `results/evidence/002/model_contract.json` |
| 003 | Completed | PASS | APPROVED | `results/evidence/003/raw_tensor_stats.json` |
| 004 | Completed | PASS | APPROVED | `results/evidence/004/python_ort_detections.json` |
| 005 | Completed | PASS | APPROVED | `results/evidence/005/python_test_summary.json` |
| 006 | Completed | PASS | APPROVED | `results/evidence/006/preprocess_alignment.json` |
| 007 | Completed | PASS | APPROVED | `results/evidence/007/python_cpp_ort_comparison.json` |
| 008 | Completed | PASS | APPROVED | `results/evidence/008/cpp_ort_video.json` |
| 009 | Completed | PASS | APPROVED | `results/evidence/009/benchmark_validation.json` |
| 010 | Completed | PASS | APPROVED | `results/evidence/010/ncnn_model_load.json` |
| 011 | Completed | PASS | APPROVED | `results/evidence/011/ncnn_benchmark_validation.json` |
| 012 | Completed | PASS | APPROVED | `results/evidence/012/three_backend_benchmark_validation.json` |

## Limitations and unresolved risks

- WSL2 is not bare-metal Linux; affinity is scheduler managed and CPU pinning is
  disabled.
- Python OpenCV 4.10.0 and C++ OpenCV 4.6.0 limit preprocess attribution.
- ORT and ncnn share source weights but not the same serialized graph.
- Frequency, thermal state, and background load may affect measured latency.
- The approved PC measurements remain specific to this environment, model,
  conversion path, Runtime versions, build, and input.
- PC correctness and speed do not predict ARM compatibility or performance.

## Checkpoint C

Checkpoint C is human-approved after review of raw sample counts/order, per-round
and position statistics, outliers, stability, CPU/RSS definitions, fresh images,
README, matrix, and limitations. PC Stage 1 is complete. Stage 2 remains
`Not implemented / Planned` and has not started.
