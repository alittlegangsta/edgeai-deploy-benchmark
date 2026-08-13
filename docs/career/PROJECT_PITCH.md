# Project pitch

这份话术面向端侧 AI、嵌入式推理和模型部署岗位。数字只采用
[Task040 authoritative manifest](../../results/final/authoritative_results.json)。

## 30 秒介绍

这是一个把同一个 YOLOv5n v7.0 模型部署到不同推理后端的 EdgeAI 工程。我
用 C++ 和 OpenCV 统一了 ONNX Runtime CPU、RTX 4060 Ti 上的 TensorRT/CUDA、
以及 Anlogic DR1M90 ARM Linux 上的 ncnn，并把预处理、decode/NMS、正确性和
benchmark 协议固定下来。ARM 端最终接受 EQ INT8，推理约有 `1.60x` 提升；
TensorRT FP16 的 GPU execution 有 `1.22x` 提升。DR1 还跑通了真实 UVC camera
和独立的 `Alnpu | ALHardNPU` vendor face control，但 custom YOLOv5n NPU 仍
等待厂商 backend/toolchain。

## 1 分钟介绍

我先固定了 YOLOv5n v7.0 的 ONNX 契约：batch 1、`640x640`、raw output
`[1,25200,85]`，图内不带 NMS。然后把 ORT、TensorRT 和 ncnn 的 backend 适配器
放到统一 C++ 接口后面，共享 OpenCV letterbox、tensor 转换、decode、NMS 和
可视化，这样每次比较的是同一模型语义而不是三套脚本。

在 PC 上，RTX 4060 Ti 使用 CUDA 12.9/TensorRT 10.13.3，FP16 通过独立 COCO
正确性 gate；CUDA execution 从 `1.674261 ms` 降到 `1.370379 ms`，但 pipeline
仍被 H2D/D2H、同步、预处理和 postprocess 影响，所以没有把 GPU kernel 提升
夸成端到端提升。

在真实 DR1 ARM Linux 上，我先做 ncnn threads/packing profiling，发现
Convolution 占 layer time `80.304%`，inference 占 pipeline `95.399611%`，
最终固定两线程、默认调度、packing on。ncnn EQ INT8 用 500 张 calibration、
4,500 张独立 COCO 图像验证后，mAP50 和 mAP50-95 绝对下降小于 `0.02`，再做
ARM benchmark，得到 `1.604359x` inference speedup。

最后，DR1 的 V4L2 UVC camera 使用同一动态输入接口产生 JSON 和标注视频。NPU
部分只把已验证的 vendor face model 作为功能控制：日志明确显示
`Alnpu | ALHardNPU` 且 fallback 禁止；custom YOLOv5n 没有被包装成成功案例。

## 3 分钟介绍

### 1. 问题和契约

目标不是做一个只能在 PC 上跑的 demo，而是验证同一模型在 CPU、GPU 和 ARM
边缘设备上的部署闭环。为了避免“换模型后比较速度”，我冻结 YOLOv5n v7.0
ONNX、输入 `[1,3,640,640]`、输出 `[1,25200,85]`、FP32 和无图内 NMS，并
固定部署 confidence `0.25`、NMS IoU `0.45`。COCO accuracy evaluator 使用
独立的 evaluation threshold，但不会改变部署阈值。

### 2. 统一 C++ 工程

`InferenceBackend` 只负责 raw tensor inference；OpenCV 预处理、输出 decode/NMS
和可视化是 backend-independent。CLI 能处理 image、video 和 camera，明确指定
`ort|tensorrt|ncnn`，不支持的 precision/backend 直接报错。这样可以把错误
定位到模型、runtime 或 pipeline 阶段，而不是被静默 fallback 掩盖。

### 3. PC GPU 结果和瓶颈迁移

TensorRT FP32/FP16 engine 在 RTX 4060 Ti 上现场构建。FP16 COCO gate 的
mAP50/mAP50-95 为 `0.448105/0.274787`，相对 FP32 的绝对变化为
`-0.000197/+0.000066`。CUDA execution 是 `1.674261 → 1.370379 ms`，但
正式 pipeline 是 `9.283727 → 9.408935 ms`。所以面试时我会区分 kernel
execution、backend-call wall time 和 end-to-end pipeline，结论是瓶颈从算力
转移到了传输、同步、CPU 预处理和 postprocess，而不是宣称 FP16 全链路加速。

### 4. ARM CPU 和 INT8

DR1 ncnn 先做 runtime tuning 和 layer profiling。两逻辑 CPU 只接受 threads=2；
packing on、默认调度通过正确性后保留，Convolution 仍是主要成本。INT8 采用
ncnn 官方 ACIQ/KL/EQ 流程；早期 evaluator 把 500 张 prediction 与 5,000 张
GT 混算，导致异常 mAP。修复 image IDs、COCO80 category mapping、原图 xywh
坐标和 AP threshold 后，重新用 500 calibration 与 4,500 independent
evaluation 评估。EQ 的 mAP50/mAP50-95 为 `0.443309/0.265115`，绝对下降
`0.014296/0.014662`，通过 gate，再在相同协议下测得 `1.604359x` inference
speedup 和 `10.417162%` RSS reduction。

### 5. 动态输入和 NPU 边界

DR1 UVC camera 是真实 `/dev/video0`、V4L2 YUYV `640x480@25 FPS`，bounded
run 处理 3 帧并输出可重新解码的视频；`queue capacity=0`，因此不能说它是
25-FPS realtime pipeline。NPU 方面，driver/runtime bring-up 和 vendor face
control 已闭环，但这是不同模型：Arm NN Optimize/LoadNetwork 后日志出现
`Alnpu | ALHardNPU`，并且 project runner 拒绝 CPU fallback。对 generic
YOLOv5n，当前公开 backend 的 LayerSupport 边界仍无法闭合，所以状态是
`WAITING_FOR_VENDOR_INPUT`，而不是“硬件不支持 NPU”。

### 6. 收束方式

项目的核心价值是把正确性、性能边界和失败边界都写成 evidence：formal
benchmark、camera integration、NPU functional control 和 vendor-blocked
结果分开。这样后续如果厂商提供兼容 backend 或 compiler，可以在不改动现有
CPU/GPU基线的前提下新增一条可审计路径。

## 备用一句话

“我做的是一个 correctness-first 的跨平台推理部署工程：同一个 YOLOv5n
契约贯通 ORT、TensorRT 和 ncnn，在 ARM 上用量化获得可接受精度和实际收益，
同时把 camera、NPU control 和 vendor blocker 都保留为可验证的边界。”
