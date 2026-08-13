# Task 040 — README-ready frozen results

> These are provenance-linked results. Formal benchmark rows are reported independently; no cross-hardware speedup is claimed.

## A. Cross-platform YOLOv5n performance (independent formal rows)

| Platform | Hardware | Backend / precision | Backend-call mean (p50/p95 ms) | GPU execution mean (p50/p95 ms) | Pipeline mean (p50/p95 ms) | FPS | RSS / GPU memory | Scope |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| PC WSL2 x86_64 | CPU | ONNX Runtime 1.18.1 / CPUExecutionProvider / FP32 | 45.849137 (45.639122/48.349684) | n/a | 51.802986 (51.595426/54.415443) | 19.303907 | RSS 150869.333333 KiB | formal_benchmark |
| PC WSL2 x86_64 | NVIDIA GeForce RTX 4060 Ti (compute capability 8.9) | TensorRT 10.13.3 / CUDA 12.9 / FP32 | 3.712445 (3.482152/5.222537) | 1.674261 (1.460416/2.739680) | 9.283727 (9.104986/10.790646) | 107.715355 | RSS 537596.000000 KiB; GPU free-end 7353663488 B | formal_benchmark |
| PC WSL2 x86_64 | NVIDIA GeForce RTX 4060 Ti (compute capability 8.9) | TensorRT 10.13.3 / CUDA 12.9 / FP16 | 3.716104 (3.455037/5.107800) | 1.370379 (1.241536/2.234560) | 9.408935 (9.013034/11.427198) | 106.281952 | RSS 548172.000000 KiB | formal_benchmark |
| DR1 MLK-F3P-CZ02-DR1M90 | AArch64 dual-core Cortex-A35-class CPU | ncnn 20240410 / FP32 | 1882.246418 (1877.732749/1888.663099) | n/a | 1973.145698 (1968.618889/1984.811900) | 0.506805 | RSS 166579.200000 KiB | formal_benchmark |
| DR1 MLK-F3P-CZ02-DR1M90 | AArch64 dual-core Cortex-A35-class CPU | ncnn 20240410 / EQ INT8 | 1173.207637 (1172.655522/1187.335782) | n/a | 1266.499601 (1264.250773/1285.629763) | 0.789578 | RSS 149047.200000 KiB | formal_benchmark |

## B. Accuracy/performance trade-off

| Platform / comparison | Reference mAP50 / mAP50-95 | Candidate mAP50 / mAP50-95 | Accuracy delta | Performance comparison | Gate |
|---|---:|---:|---:|---|---|
| DR1 MLK-F3P-CZ02-DR1M90 (dr1_fp32_vs_eq_int8) | 0.457605 / 0.279777 | 0.443309 / 0.265115 | -0.014296 / -0.014662 | backend-call 1.604359x; pipeline 1.557952x; FPS +55.795209% | PASS |
| PC WSL2 NVIDIA RTX 4060 Ti (rtx4060ti_fp32_vs_fp16) | 0.448303 / 0.274720 | 0.448105 / 0.274787 | -0.000197 / 0.000066 | GPU execution 1.221751x; backend-call delta 0.098575%; pipeline delta -1.330733% | PASS |

## C. Deployment capability matrix

| Backend | Platform | Model | Status | Scope |
|---|---|---|---|---|
| ORT | PC CPU | YOLOv5n v7.0 | `YOLOV5N_CPU_FORMAL_READY` | formal benchmark; no fallback |
| TensorRT | RTX 4060 Ti | YOLOv5n v7.0 | `TENSORRT_FP32_FP16_FORMAL_READY` | formal benchmark; FP16 accepted by COCO gate |
| ncnn | DR1 CPU | YOLOv5n v7.0 | `NCNN_FP32_EQ_INT8_FORMAL_READY` | formal benchmark; EQ accepted by COCO gate |
| Alnpu \| ALHardNPU | DR1 NPU | vendor face control | `FUNCTIONAL_CONTROL_ONLY` | different face model; no YOLOv5n performance substitution |
| Alnpu | DR1 NPU | YOLOv5n v7.0 | `WAITING_FOR_VENDOR_INPUT` | NOT_BENCHMARKED; Task028 external dependency blocker |

## Integration-only evidence

Task038 unified-app image timings and Task039 PC video/DR camera timings are retained in the manifest as `integration_evidence` / `CAMERA_INTEGRATION_EVIDENCE`. They do not overwrite the formal rows above and are not presented as a realtime camera benchmark.

TensorRT timing note: the main cross-backend inference column is the backend-call wall boundary. For TensorRT this is `detector.infer()` wall time (H2D + enqueueV3 + D2H + synchronization): FP32 3.712445 ms and FP16 3.716104 ms. The separate GPU execution column is CUDA event time around enqueueV3 only: FP32 1.674261 ms and FP16 1.370379 ms. Thus FP16 GPU execution speedup is 1.221751x, while pipeline timing is 9.283727 to 9.408935 ms and is not an end-to-end improvement. Task038 integration timing is a separate boundary (4.255539/7.397064 ms backend-call means) and does not overwrite Task037 formal values.

Source: `results/final/authoritative_results.json`.
