# Interview Q&A

回答原则：先说已测事实，再说工程判断，最后主动划定证据边界。所有数字以
[FINAL_PROJECT_FACTS.md](FINAL_PROJECT_FACTS.md) 和 Task040 manifest 为准。

## 一、模型与 ONNX

### Q1. 为什么选择 YOLOv5n？

**推荐回答：** YOLOv5n 是轻量、结构清晰、社区工具链成熟的检测模型，适合
展示从 ONNX 到 PC GPU、ARM CPU 和动态输入的完整部署链。我没有为了某个
backend 临时换模型，始终保持 v7.0、640 输入、raw `[1,25200,85]` 契约。

**可能追问：** 为什么不是 YOLOv8 或更大的模型？

**不可越界事实：** 只能说本项目冻结的是 YOLOv5n v7.0；不能声称对其他
YOLO版本有相同 accuracy 或 backend 结论。

### Q2. 为什么使用 ONNX？

**推荐回答：** ONNX 把模型图和 runtime 解耦，让 ORT、TensorRT parser 和
ncnn 转换链共享一个可检查的输入输出契约。我先用 ONNX checker、shape/dtype
和 raw output correctness 固定语义，再分别构建 backend。

**可能追问：** 图里为什么不放 NMS？

**不可越界事实：** 当前冻结图没有 graph NMS，decode/NMS 是项目公共后处理；
不能说所有导出版本都没有 NMS。

### Q3. 你如何证明不同 backend 结果仍是同一个模型？

**推荐回答：** 统一输入、letterbox、输出 shape、decode/NMS 和阈值，比较
class、box IoU、confidence 和 detection count；formal accuracy 再使用相同
COCO evaluator 和明确 image/category/bbox mapping。

**可能追问：** 视觉上框一样是否足够？

**不可越界事实：** 不够；视觉图是辅助证据，正式 gate 使用结构化数值。

## 二、C++ 工程

### Q4. 统一接口如何划分职责？

**推荐回答：** `InferenceBackend` 返回 raw tensor；ORT、TensorRT、ncnn 是
适配器。OpenCV source acquisition、预处理、decode/NMS、overlay 和 JSON 属于
公共层。backend 不可用时显式报错，不允许隐式 fallback。

**可能追问：** 为什么不把后处理放在每个 backend？

**不可越界事实：** 这样容易产生语义漂移；本项目的统一 contract 要求公共
后处理，NPU face 因模型 contract 不同被保留为独立 control。

### Q5. 如何让动态输入不污染单图 benchmark？

**推荐回答：** image、video、camera 共用 pipeline，但 formal benchmark 只
使用固定协议和固定输入；Task038/039 的 unified-app/video/camera timing 单独
标为 integration evidence。

**可能追问：** camera 为什么没有无限队列？

**不可越界事实：** 当前 Task039 同步实现 `queue capacity=0`，没有宣称
latest-frame 或实时处理所有源帧。

## 三、TensorRT / CUDA

### Q6. FP16 明明更快，为什么 pipeline 没有变快？

**推荐回答：** CUDA event 的 execution 从 `1.674261` 降到 `1.370379 ms`，
但端到端 pipeline 从 `9.283727` 变为 `9.408935 ms`。FP16 只改善 GPU execution；
H2D/D2H、同步、CPU preprocessing 和 postprocess 仍在总时间里。

**可能追问：** 你会如何继续优化？

**不可越界事实：** Task037 已冻结，不应把未做的 transfer overlap、GPU NMS
或新 benchmark 说成已验证收益。

### Q7. TensorRT 的哪个 timing 才能和其他 backend 比？

**推荐回答：** Task040 的 cross-backend 字段使用 `detector.infer()` host wall
time（含 H2D、enqueue、D2H 和同步）；CUDA execution 是单独的 kernel-region
诊断，不能混用。FP32/FP16 两者边界一致。

**可能追问：** 为什么 README 同时有两个数？

**不可越界事实：** 两个数语义不同；不能挑较小的 CUDA event 数字冒充端到端。

### Q8. 为什么禁用 TF32？

**推荐回答：** 初始 TensorRT FP32 需要通过已有 Golden contract；接受的 engine
使用 `--noTF32`，先保证数值正确，再测 FP16 的 COCO gate。

**可能追问：** 这是不是永远更快？

**不可越界事实：** 不是。这里只能陈述当前 RTX 4060 Ti、模型和协议下的接受
配置，不能泛化到其他 GPU。

## 四、ARM / ncnn

### Q9. 为什么选 ncnn？

**推荐回答：** ncnn 适合无 Python 的 AArch64 CPU 部署，提供 NEON/packing、
OpenMP 和官方 INT8 工具链，能在 Buildroot/ARM Linux 里保持较小 runtime。
项目还验证了动态库、线程数和板端 ABI，而不是只在 PC 上跑。

**可能追问：** ncnn 是否用了 NPU？

**不可越界事实：** 正式 DR1 YOLO rows 是 CPU-only ncnn；EQ INT8 不是 NPU
结果。

### Q10. 为什么 threads=2？

**推荐回答：** 实机拓扑只有两个逻辑 CPU。Task033 对 1/2 线程做同协议
对比，2 threads、默认调度、packing on 正确且更快；没有为了“更多线程”运行
3/4 线程过度超配。

**可能追问：** affinity 或 FP16 有帮助吗？

**不可越界事实：** 已测 affinity、packing-off 和 FP16 选项没有带来接受收益；
不能说所有 CPU/版本都没有收益。

### Q11. profiling 发现了什么？

**推荐回答：** Convolution 占 layer time `80.304%`，Task033 accepted FP32
pipeline 中 inference 占 `95.399611%`，所以主要瓶颈是 convolution/kernel
throughput，而不是 NMS。后续 INT8 的 convolution aggregate speedup 是
`1.938084x` 的诊断证据。

**可能追问：** 你是否证明了 cache miss？

**不可越界事实：** perf/PMU 不可用，没有声称 cache-miss 归因。

## 五、INT8 量化

### Q12. 如何证明 EQ INT8 可接受？

**推荐回答：** calibration 使用 500 张 COCO val2017 图像，evaluation 使用互不
重叠的 4,500 张；先修复 COCO evaluator 的 image IDs、category mapping 和
原图 xywh，再以 mAP50/mAP50-95 degradation gate 判定。EQ 的绝对下降
`0.014296/0.014662`，小于 `0.02`，且没有 zero-detection image。

**可能追问：** 为什么早期报告很低？

**不可越界事实：** 早期 evaluator 将 500 张预测与完整 5,000 张 GT 混算，已
保留为无效历史证据；不能使用早期数值作最终结论。

### Q13. ACIQ 和 KL 怎么处理？

**推荐回答：** 三种官方 ncnn 流程都做过有界评估；KL 出现 catastrophic zero
 detection，ACIQ 只保留为 secondary comparison，EQ 是唯一通过最终 gate 并
进入 ARM benchmark 的候选。

**可能追问：** 你是否通过改 threshold 救了 EQ？

**不可越界事实：** 没有。部署阈值始终保持 confidence `0.25`、NMS IoU `0.45`；
COCO AP evaluation threshold 只用于 evaluator，不能混为部署配置。

### Q14. 量化后的性能收益来自哪里？

**推荐回答：** 最终 ARM formal benchmark 中 inference `1882.246 → 1173.208 ms`，
`1.604359x`；pipeline `1973.146 → 1266.500 ms`，`1.557952x`；同时
convolution aggregate 诊断为 `1.938084x`。这些都是同一 DR1 平台、同一协议的
FP32/EQ 对比。

**可能追问：** INT8 是否改变模型语义？

**不可越界事实：** 有可量化的 accuracy degradation，gate 认为可接受；不能
说“无损”或宣称所有数据集精度不变。

## 六、Linux / 交叉编译

### Q15. ARM 部署最难的工程问题是什么？

**推荐回答：** 不是只生成 AArch64 ELF，还要闭合 sysroot、OpenMP/private
libgomp、OpenCV/videoio、loader、DT_NEEDED、模型 manifest 和板端目录。Task
025 的 SD preflight 和 Task027 persistent runtime 都把这些写成可检查的部署
资产。

**可能追问：** 为什么不直接换系统库？

**不可越界事实：** 没有替换板端系统库，也没有用 sudo 改系统；私有库通过
隔离路径部署。

### Q16. 你如何处理模块或 runtime ABI 风险？

**推荐回答：** 记录架构、loader、glibc、SONAME、DT_NEEDED 和 hash；对驱动
还要看 vermagic、内核 config、符号来源和 Device Tree，而不是只看文件名。

**不可越界事实：** 当前 generic YOLO NPU 的 vendor runtime/backend 仍未闭合，
不能说项目有通用 NPU ABI。

## 七、V4L2 / camera

### Q17. camera 闭环如何证明？

**推荐回答：** 实机识别 `/dev/video0`、Sonix USB 2.0 Camera、`uvcvideo`，协商
YUYV `640x480@25 FPS`，用同一个 `edgeai_demo` ncnn INT8 path 处理 3 帧并写出
MJPEG 视频，重新解码通过。

**可能追问：** 为什么 effective FPS 只有 `0.564866`？

**不可越界事实：** ncnn INT8 推理约 0.79 FPS，camera source 25 FPS；这个
bounded run 是 integration evidence，不是实时性能 benchmark。

### Q18. 为什么不说 dropped=0 就是实时？

**推荐回答：** 因为当前实现是同步 pipeline，`queue capacity=0`，只统计了该次
bounded run 的 3 帧，没有无限队列也没有证明源端所有帧都被 AI 处理。

**不可越界事实：** 不要把 Task021 的 latest-frame 语义混入 Task039；Task039
使用的是同步动态 pipeline。

## 八、性能 profiling

### Q19. formal benchmark 和 integration timing 如何区分？

**推荐回答：** formal row 有固定 warmup/repeat、阶段边界和 correctness gate，
进入 Task040 authoritative manifest；Task038 unified-app 与 Task039 video/camera
只证明接口/功能闭环，不替换 formal backend rows。

**可能追问：** 为什么不把最短的一次 timing 放 README？

**不可越界事实：** 不能选择性挑数；Task040 对 TensorRT 还明确区分 backend-call
wall 和 CUDA execution。

### Q20. 你如何保证性能结果可复现？

**推荐回答：** 冻结模型/input hash、backend/runtime identity、threads/packing、
warmup/repeat、p50/p95、RSS 和 source evidence hash；validator 会重新校验
manifest arithmetic 和证据身份。

**不可越界事实：** 未记录的频率/温度不能补写；跨硬件不直接宣称 speedup。

## 九、NPU / Arm NN / Alnpu

### Q21. NPU 到底跑通了吗？

**推荐回答：** DR1 的 NPU runtime/driver bring-up 已完成，vendor face model
通过项目自有 C++ runner 在 `Alnpu | ALHardNPU` 上运行，日志证明 fallback 禁止。
这是 functional control；custom YOLOv5n 仍是 `WAITING_FOR_VENDOR_INPUT`。

**可能追问：** 为什么不能把 face 结果当 YOLO 加速？

**不可越界事实：** face 是不同模型和输出 contract，禁止与 YOLOv5n CPU/GPU
性能比较，也没有 custom YOLOv5n NPU FPS。

### Q22. 为什么 custom YOLOv5n 没完成？

**推荐回答：** 当前 Arm NN parser/network 创建通过，但 audited AArch64
AlnpuLayerSupport 在 generic quantized YOLO layer 边界阻塞；公开 binary 只够
确认有限 support/fusion symbols，不能恢复完整 predicate。Native compiler/runtime
和官方 GEG400 YOLO deployment chain 也没有完整可用资产，所以结论是
vendor dependency，而不是“DR1 硬件不支持 NPU”。

**可能追问：** 你做过哪些排查？

**不可越界事实：** 保留 face positive、vendor YOLOv8n fail、Track A/B/C 证据；
没有随机改模型、换 YOLOv5s 或 CPU fallback 伪造成功。

### Q23. 如何证明没有 CPU fallback？

**推荐回答：** project runner 只请求 `Alnpu`，配置 `fallback_allowed=false`；
stdout 出现 `Alnpu | ALHardNPU`，stderr/structured result 为
`PASS_ALNPU_ONLY`，并且没有接受 CpuAcc/CpuRef assignment。

**不可越界事实：** 这项证明只适用于已验证 vendor face control，不外推到 custom
YOLOv5n。

## 十、系统设计

### Q24. 如果要把它产品化，你会如何演进？

**推荐回答：** 保持公共 preprocessing/postprocessing 和显式 backend factory，
增加配置/资产 manifest、设备 health-check、受控 runtime packaging 和统一
telemetry；每个新 backend 先通过 shape/dtype/correctness gate，再进入 benchmark。

**可能追问：** 会不会马上加异步队列和零拷贝？

**不可越界事实：** 这些是后续设计方向，不是本项目已验证结果；不要把 camera
同步实现包装成异步性能。

### Q25. 这个项目最重要的工程取舍是什么？

**推荐回答：** 我优先保证可解释性：固定契约、一次改一个变量、correctness
先于 performance、区分 formal/integration/control/blocker。这样得到的不是
“所有路径都成功”的宣传，而是一条知道哪里可用、哪里需要厂商输入的部署链。

**可能追问：** 这对团队协作有什么价值？

**不可越界事实：** 可以交付 manifest、复现命令、证据 hash 和 vendor handoff，
但不能声称已经有厂商回复或生产级 NPU YOLO 支持。
