# STAR / 技术故事

这些故事用于行为面和技术面展开。数字来自冻结 evidence；每个故事最后的
“边界”是回答时主动声明的范围。

## 1. ARM 性能优化：先 profiling，再接受单变量改动

**Situation**：DR1M90 是双逻辑 CPU 的 ARM Linux 设备，初始 ncnn FP32 单图
pipeline mean 为 `3514.946744 ms`。

**Task**：在不改模型、输入尺寸、阈值和正确性 contract 的前提下，找出可解释
的 CPU 优化。

**Action**：先比较 threads 和调度，再做 packing、affinity、FP16 选项 A/B；
逐层 profiler 显示 60 个 Convolution 占 `80.304%` layer time，inference 占
accepted pipeline 的 `95.399611%`。只保留 correctness 通过且更快的
`threads=2`、默认调度、packing on；拒绝较慢的 affinity、packing-off 和 FP16
候选。

**Result**：Task033 best FP32 pipeline 为 `1963.817618 ms`，相对单线程
`1.789854x`；Task034 将主要瓶颈定位为 convolution/kernel throughput，而
不是 NMS。

**边界**：PMU 不可用，因此没有声称 cache-miss 归因；这不是 NPU 优化。

## 2. INT8 量化：从 evaluator bug 到可接受 gate

**Situation**：早期 INT8 评估得到异常低的 FP32 mAP，无法判断是量化还是评估器
错误。

**Task**：修正评估语义，并用独立数据决定是否让 EQ INT8 进入 ARM benchmark。

**Action**：发现 evaluator 将 500 张 prediction 与完整 5,000 张 GT 混算，修正
`imgIds`、COCO80 category mapping、原图 pixel `xyxy→xywh` 和 AP threshold。
然后用 500 张 calibration 与互不重叠的 4,500 张 evaluation 比较 FP32/EQ；不改
deployment confidence `0.25` 或 NMS IoU `0.45`。EQ 的 mAP50/mAP50-95 为
`0.443309/0.265115`，相对 `0.457605/0.279777` 的绝对下降
`0.014296/0.014662`，通过 `0.02` gate。

**Result**：同一 AArch64 NCNN_INT8=ON 配置测得 inference `1173.208 ms` 对
FP32 `1882.246 ms`，`1.604359x` speedup；pipeline `1.557952x`，RSS reduction
`10.417162%`。EQ 被正式接受，ACIQ 保留为 secondary，KL 因 zero detection
被拒绝。

**边界**：这是 ARM CPU INT8，不是 NPU 量化；mAP 是本项目独立工程 gate，不是
COCO leaderboard 宣称。

## 3. TensorRT：GPU 变快，但 pipeline 没变快

**Situation**：RTX 4060 Ti 上需要比较 TensorRT FP32/FP16，同时避免把不同
timing boundary 混在一起。

**Task**：建立正确性先行的 GPU baseline，并解释 FP16 的收益位置。

**Action**：使用 CUDA 12.9、TensorRT 10.13.3 现场构建 engine；分别记录
host backend-call wall 和 CUDA event `enqueueV3` execution。FP16 COCO gate
通过，mAP50/mAP50-95 从 `0.448303/0.274720` 变为
`0.448105/0.274787`。执行区从 `1.674261` 降到 `1.370379 ms`，但 pipeline
从 `9.283727` 变为 `9.408935 ms`。

**Result**：得到 `1.221751x` GPU execution speedup，同时明确不能宣称端到端
提升；瓶颈迁移到数据传输、同步、预处理和 postprocess。

**边界**：Task038 的 integration timing 不覆盖 Task037 formal row；不能用
CUDA event 数字替代 backend-call 或 pipeline。

## 4. DR1 camera：从 V4L2 设备到 ncnn INT8 闭环

**Situation**：模型推理明显慢于 USB camera source，需要证明动态输入接口和
输出链确实工作。

**Task**：在不宣称实时性能的前提下完成真实 ARM camera integration。

**Action**：审计 `/dev/video0` 的设备身份、V4L2 backend 和 YUYV 协商，复用
统一 `edgeai_demo` ncnn INT8 path，限制 bounded run 为 3 帧，生成 JSON 和
MJPEG VideoWriter 输出，并重新解码验证。

**Result**：Sonix USB 2.0 Camera / `uvcvideo` / YUYV `640x480@25 FPS`，
`captured=3`、`processed=3`、`written=3`、exit 0；effective processing FPS
`0.564866`，inference mean `1343.185 ms`。输出视频可重新解码。

**边界**：实现是同步 pipeline，`queue capacity=0`；0 dropped 只属于这次 bounded
run，不代表处理了 camera 的全部 25 FPS，也不是 formal benchmark。

## 5. DR1 NPU：跑通 control，同时合理停止 custom YOLO

**Situation**：DR1 NPU 资料混合了不同板型和工具链；不能为了展示而把 vendor
face 结果包装成 YOLOv5n NPU。

**Task**：先闭合真实可复现的 vendor face control，再判断 custom YOLO 是否
具备证据条件。

**Action**：完成 driver/runtime bring-up 和隔离部署，使用项目自有 C++ face
runner 强制 Arm NN `Alnpu`，检查 `Alnpu | ALHardNPU` assignment、CMA buffer、
JSON/annotated image，并将 fallback 设为 false。对 custom YOLO，保留 parser/network
通过但 Alnpu LayerSupport 阻塞的证据；静态确认 fusion symbols，却不假装恢复
完整 predicate，也不随机修改 graph。

**Result**：vendor face 得到 `PASS_ALNPU_ONLY`，CPU fallback 未接受；custom
YOLOv5n 状态收敛为 `WAITING_FOR_VENDOR_INPUT`，并形成精确 vendor handoff。

**边界**：不能说“DR1 NPU 不支持 YOLO”，只能说当前审计 runtime/backend 和
公开 native toolchain 不足以完成 custom YOLO；没有 YOLOv5n NPU FPS。

## 6. 统一 C++：把实验结果变成可展示应用

**Situation**：三套 backend 脚本容易产生不同预处理和 fallback 行为。

**Task**：用最小架构统一 image/video/camera 的展示入口。

**Action**：将 ORT、TensorRT、ncnn 适配为 `InferenceBackend`，公共层负责
OpenCV acquisition、preprocess、decode/NMS、overlay、JSON 和 VideoWriter；
CLI 显式要求 backend/model/source，并对不支持组合返回错误。

**Result**：同一 `edgeai_demo` 接口覆盖静态图、视频文件和 camera；Task039 的
PC/DR 运行保留为 integration evidence，Task040 formal rows 不被覆盖。

**边界**：这不是新的 benchmark 或异步队列优化，camera 实现的 `queue capacity=0`
仍需如实说明。
