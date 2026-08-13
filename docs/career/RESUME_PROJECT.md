# Resume project entry

## 推荐项目名称

**EdgeAI Deploy Benchmark — YOLOv5n 跨平台端侧部署与性能验证平台**

## 一句话项目描述（中文）

围绕固定 YOLOv5n v7.0 ONNX 契约，使用 C++/OpenCV 统一 ORT、TensorRT/CUDA
和 ARM Linux ncnn 推理链，并在真实 Anlogic DR1M90 上完成 INT8、V4L2 摄像头
和 vendor NPU face control 的可复核部署验证。

## 中文简历 bullets

- 设计 C++17 `InferenceBackend` 统一接口，复用 OpenCV 预处理、YOLO raw
  output decode/NMS 和可视化，使 ONNX Runtime CPU、TensorRT/CUDA FP32/FP16
  与 ARM ncnn FP32/EQ INT8 使用同一模型输入输出契约，并对不支持的 backend
  显式报错、禁止静默 fallback。
- 在真实 Anlogic DR1M90 ARM Linux 上完成 ncnn 20240410 的线程/packing
  profiling：固定 `threads=2`、默认调度、packing on；进一步用 500 张
  calibration 和 4,500 张独立 COCO val2017 图像验证 EQ INT8，mAP50/mAP50-95
  绝对下降 `0.014296/0.014662`，推理加速 `1.604359x`、pipeline 加速
  `1.557952x`，峰值 RSS 降低 `10.417162%`。
- 在 RTX 4060 Ti（CUDA 12.9、TensorRT 10.13.3）现场构建并验证 FP32/FP16
  engine；FP16 COCO gate 通过，CUDA execution 从 `1.674261 ms` 降至
  `1.370379 ms`（`1.221751x`），同时识别出 host preprocessing、传输、同步
  和 postprocess 使端到端 pipeline 没有提升。
- 在 DR1 上完成 V4L2 UVC camera → ncnn INT8 → JSON/VideoWriter 的真实闭环，
  并将 vendor face model 通过项目自有 C++ runner 严格分配到
  `Alnpu | ALHardNPU`、禁止 CPU fallback；custom YOLOv5n NPU 仍诚实标记为
  `WAITING_FOR_VENDOR_INPUT`。

## English version

**One-line description**

Built a reproducible C++ deployment and profiling pipeline for a frozen YOLOv5n
v7.0 ONNX contract across ONNX Runtime, TensorRT/CUDA and ARM Linux ncnn, with
real Anlogic DR1M90 INT8, V4L2 camera and vendor NPU-control validation.

**Resume bullets**

- Designed a small C++17 `InferenceBackend` interface with shared OpenCV
  preprocessing, raw-output decode/NMS and visualization across ORT CPU,
  TensorRT/CUDA FP32/FP16 and ARM ncnn FP32/EQ INT8; unsupported backends fail
  explicitly instead of silently falling back.
- Profiled and optimized the real DR1M90 ARM ncnn path with two threads,
  default scheduling and packing enabled.  An independent COCO gate using 500
  calibration and 4,500 held-out images accepted EQ INT8 at
  `0.014296/0.014662` absolute mAP50/mAP50-95 degradation, with `1.604359x`
  inference and `1.557952x` pipeline speedup.
- Built and validated TensorRT FP32/FP16 engines on an RTX 4060 Ti with CUDA
  12.9 and TensorRT 10.13.3.  FP16 reduced measured CUDA execution from
  `1.674261 ms` to `1.370379 ms` (`1.221751x`) while profiling showed that the
  complete pipeline remained transfer/CPU-postprocess bound.
- Closed a real DR1 V4L2 UVC-camera-to-ncnn-INT8 path and a project-owned vendor
  face runner with strict `Alnpu | ALHardNPU` assignment and no CPU fallback;
  custom YOLOv5n NPU execution remains `WAITING_FOR_VENDOR_INPUT`.

## 技术栈关键词

`C++17` · `ONNX` · `ONNX Runtime` · `TensorRT` · `CUDA` · `OpenCV` · `ncnn` ·
`INT8` · `FP16` · `ARM Linux` · `AArch64` · `V4L2` · `UVC` · `NPU` · `Arm NN` ·
`Alnpu` · `profiling` · `benchmark` · `CMake` · `Buildroot`

## 事实来源

- [Task040 authoritative results](../../results/final/authoritative_results.json)
- [Final benchmark provenance](../FINAL_BENCHMARK_RESULTS.md)
- [ARM INT8 report](../benchmark/ARM_NCNN_INT8_QUANTIZATION_FEASIBILITY.md)
- [TensorRT report](../benchmark/TENSORRT_DEPLOYMENT_BASELINE.md)
- [DR1 NPU handoff](../vendor_handoff/dr1m90_npu/README.md)
