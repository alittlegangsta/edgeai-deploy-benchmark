# Final project facts

这是简历、面试和演示中允许引用的最小事实表。正式数字来自
[`results/final/authoritative_results.json`](../../results/final/authoritative_results.json)，
过程事实来自已验证的 Task evidence。除非重新建立独立任务，不要用其他中间
结果替换这里的数字。

## 项目契约

- Model: YOLOv5n v7.0 ONNX。
- Input: batch 1, FP32 `[1,3,640,640]`。
- Raw output: FP32 `[1,25200,85]`，无图内 NMS。
- Deployment postprocess: confidence `0.25`、NMS IoU `0.45`；COCO AP evaluator
  的 `0.001/0.6/max_det=100` 仅属于评估协议。
- 公共 pipeline: OpenCV acquisition/preprocess → explicit backend inference →
  decode/NMS → JSON/overlay/VideoWriter。

## 正式 YOLOv5n benchmark

这些是各平台独立 formal rows，不是跨硬件 speedup 排名。

| Platform / backend | Precision | Backend-call mean (ms) | Pipeline mean (ms) | FPS | Peak RSS |
|---|---:|---:|---:|---:|---:|
| PC CPU ORT 1.18.1 | FP32 | 45.849137 | 51.802986 | 19.303907 | 150869 KiB |
| RTX 4060 Ti TensorRT 10.13.3 / CUDA 12.9 | FP32 | 3.712445 | 9.283727 | 107.715355 | 537596 KiB |
| RTX 4060 Ti TensorRT 10.13.3 / CUDA 12.9 | FP16 | 3.716104 | 9.408935 | 106.281952 | 548172 KiB |
| DR1 ARM ncnn 20240410 | FP32 | 1882.246418 | 1973.145698 | 0.506805 | 166579 KiB |
| DR1 ARM ncnn 20240410 | EQ INT8 | 1173.207637 | 1266.499601 | 0.789578 | 149047 KiB |

### ARM FP32 → EQ INT8

- Calibration/evaluation: 500 calibration images and 4,500 disjoint COCO val2017
  evaluation images。
- FP32 → EQ mAP50: `0.457605 → 0.443309`，absolute delta `-0.014296`。
- FP32 → EQ mAP50-95: `0.279777 → 0.265115`，absolute delta `-0.014662`。
- Accuracy gate: PASS，absolute degradation threshold `0.02`，zero-detection
  images `0`。
- Inference speedup: `1.604359x`；pipeline speedup: `1.557952x`；FPS gain:
  `55.795208%`；peak RSS reduction: `10.417162%`。
- Convolution aggregate diagnostic speedup: `1.938084x`。
- Accepted runtime configuration: ncnn 20240410, `threads=2`, default scheduling,
  packing on, CPU-only FP32/EQ INT8。

### TensorRT FP32 → FP16

- Hardware/runtime: NVIDIA GeForce RTX 4060 Ti, compute capability 8.9, CUDA
  12.9.86, TensorRT 10.13.3。
- COCO gate: FP32 `0.448303/0.274720` → FP16 `0.448105/0.274787` for
  mAP50/mAP50-95; absolute deltas `-0.000197/+0.000066`，gate PASS。
- CUDA execution: `1.674261 → 1.370379 ms`，speedup `1.221751x`。
- Pipeline: `9.283727 → 9.408935 ms`；FP16 没有端到端 pipeline gain。
- Timing boundary: CUDA execution 是 enqueueV3 event；formal cross-backend
  field 是包括 transfer/synchronization 的 backend-call wall time。

## ARM profiling and camera facts

- Task033 runtime tuning: one-thread pipeline `3514.946744 ms` → accepted
  two-thread/default/packing-on `1963.817618 ms`，pipeline speedup `1.789854x`。
- Task034: Convolution `60` layers account for `80.304%` of layer time；inference
  accounts for `95.399611%` of the accepted FP32 pipeline。
- DR1 camera integration only: `/dev/video0`、Sonix USB 2.0 Camera、`uvcvideo`、
  V4L2 YUYV `640x480@25 FPS`；bounded run `3/3/3` captured/processed/written；
  inference `1343.185 ms`、pipeline `1725.077 ms`、effective processing FPS
  `0.564866`、queue capacity `0`。
- Camera numbers are integration evidence, not formal realtime benchmark and not
  evidence that all source frames were processed。

## NPU facts and exact boundaries

### 可以说

- DR1 NPU runtime/driver bring-up and controlled deployment path were validated。
- Vendor face model `yolo_face_uint8_15.onnx` ran through the project-owned C++
  runner with `Alnpu | ALHardNPU` assignment。
- CPU fallback was disabled and not accepted (`PASS_ALNPU_ONLY`)。
- The face control produced structured detections and annotated output。
- The project has a vendor handoff with runtime/backend capability evidence。

### 不能说

- 不能说 custom YOLOv5n 已经运行在 DR1 NPU。
- 不能说 vendor face 与 YOLOv5n CPU/GPU 有任何倍数加速关系。
- 不能发布 custom YOLOv5n NPU FPS 或 benchmark。
- 不能把 `FUNCTIONAL_CONTROL_ONLY` 改写为通用 YOLO backend ready。
- 不能把当前 blocker 泛化为 DR1M90 硬件永久不支持 NPU；准确表述是当前
  audited Arm NN/Alnpu backend 和 native vendor chain 需要厂商输入。

## Backend capability matrix

| Backend | Allowed status | Scope |
|---|---|---|
| ONNX Runtime CPU | `YOLOV5N_CPU_FORMAL_READY` | YOLOv5n formal benchmark |
| TensorRT/CUDA | `TENSORRT_FP32_FP16_FORMAL_READY` | YOLOv5n formal benchmark |
| ARM ncnn | `NCNN_FP32_EQ_INT8_FORMAL_READY` | YOLOv5n formal benchmark |
| `Alnpu \| ALHardNPU` | `FUNCTIONAL_CONTROL_ONLY` | vendor face model only |
| custom DR1 YOLOv5n NPU | `WAITING_FOR_VENDOR_INPUT` | not benchmarked |

## 常见追问的安全回答

- **为什么 YOLOv5n？** 轻量、契约清晰、适合在同一输入输出语义下比较多种
  runtime；本项目不把结论外推到其他模型。
- **为什么 ONNX？** 作为 parser/runtime 之间的稳定图契约，方便 ORT、TensorRT
  和 ncnn 转换链分别验证。
- **为什么 TensorRT？** 用于 RTX 4060 Ti 的 CUDA GPU deployment；FP16 的
  execution gain 与 pipeline gain 分开计时。
- **为什么 ncnn？** 适合无 Python 的 ARM Linux、NEON/packing/OpenMP 和官方
  INT8 工具链。
- **为什么 INT8？** ARM convolution 是主要瓶颈；EQ 在独立 COCO gate 内接受，
  再进入同协议 benchmark。
- **为什么 FP16 inference 快但 pipeline 没快？** GPU execution 只是 pipeline
  的一部分，transfer、同步、CPU preprocessing/postprocess 占据剩余时间。
- **为什么 camera 只有约 0.56 FPS？** 这是 bounded synchronous integration
  run；DR1 ncnn inference 本身约 0.79 FPS，不能和 camera source 25 FPS 混为一谈。
- **为什么 NPU custom YOLO 没完成？** 当前 audited Alnpu generic layer support
  与 YOLO graph 的兼容边界未闭合，公开 compiler/runtime 资产不足，因此形成
  vendor handoff，而不是随机改图或 CPU fallback。
- **如何证明 NPU 没有 CPU fallback？** runner 只请求 Alnpu、设置
  `fallback_allowed=false`，日志有 `Alnpu | ALHardNPU` 和
  `PASS_ALNPU_ONLY`，没有接受 CpuAcc/CpuRef assignment。

## Canonical sources

- [Authoritative results](../../results/final/authoritative_results.json)
- [Final provenance](../FINAL_BENCHMARK_RESULTS.md)
- [Project presentation](../PROJECT_PRESENTATION.md)
- [Final demo guide](../FINAL_DEMO_GUIDE.md)
- [Vendor handoff](../vendor_handoff/dr1m90_npu/README.md)
