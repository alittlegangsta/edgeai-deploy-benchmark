# 安路 / 米联客技术支持请求（可直接发送）

当前 NPU 状态：`WAITING_FOR_VENDOR_INPUT`。本请求等待厂商提供兼容
backend、fusion约束或官方部署链；不代表已批准新的板端操作。

主题：MLK-F3P-CZ02 / DR1M90GEG400 — YOLOv5n ArmNN/Alnpu 通用图支持与官方部署链请求

我们在 MLK-F3P-CZ02（DR1M90GEG400，Buildroot 2022.02.6，Linux
6.1.111-rt42）上完成了只读、不可回退的 Task 028 复现。当前使用的
`libarmnn.so.32.1` SHA256 为
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`，
Arm NN 版本标记为 `v32.1.0 / ed5ae24`。项目模型是 YOLOv5n v7.0、opset12、
FP32、输入 `[1,3,640,640]`、输出 `[1,25200,85]`，模型 SHA256 为
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`。

现象如下：

- 官方 `AL_onnx_pass.py`（SHA256
  `f61bc7ab424726d08881f1e9ef8a3fbcfbee8fdcb612eeb6d944c450aed4540a`）
  在未修改模型上完成 host 转换；
- ArmNN Parser 和 Network 创建通过，但 Alnpu LayerSupport 在真实
  YOLOv5n 量化图的 Conv2d/Activation/ElementwiseBinary 处阻塞；
- 官方 YOLOv8n 量化控制也在 `QAsymmU8 Splitter` 处阻塞；
- `yolo_face_uint8_15.onnx` 的独立控制可通过 `Alnpu|ALHardNPU`，说明它
  走的是厂商融合/定制路径，并不证明 generic Conv2d 支持；该 ONNX 本身
  不包含 `ALHardNPU` custom node，而是 ArmNN/Alnpu 在 Optimize 阶段形成
  3 个 `Alnpu|ALHardNPU` workload；
- 当前 `libarmnn.so.32.1` 中确认存在
  `ConvertConv2dIntoALHardNPUImpl`、`checkConv`、`checkAct`、`checkPool`，
  但公开资料和剥离二进制不足以恢复完整 fusion predicate；因此我们不
  断言 YOLOv5n 天然不兼容；
- 未接受 CPU fallback，未运行 benchmark，未修改 SD/eMMC、bitstream、
  kernel 或 DTB。

请协助提供：

1. 请提供 DR1M90 GEG400（MLK-F3P-CZ02）自定义 YOLO 的官方部署和转换
   流程，包括模型输入、导出、量化、融合和运行命令；
2. `AL_onnx_pass` 之后是否应直接进入 ArmNN/Alnpu，还是必须执行额外的
   ALHardNPU fusion、graph lowering 或 model compiler 步骤；
3. 请提供支持 generic quantized YOLO layers 的 Alnpu backend 版本和
   获取方式，以及 `ConvertConv2dIntoALHardNPUImpl` 对应的完整
   fusion/model constraints；
4. 请说明 APUG1205 `convert_tool`、`al_ai_flow`、native runtime、C/C++
   头文件和阳性 YOLO 示例的当前获取方式、版本、授权和依赖；
5. 请提供与 GEG400 匹配的 YOLO NPU HPF/TD 工程、SoftNPU bitstream、
   Device Tree 和驱动/Runtime 配套说明；
6. 请提供 SDK、model-tool、runtime、Alnpu backend、bitstream、DTB 和
   kernel module 的精确版本兼容矩阵。

请对每个文件给出版本、目标板卡、SHA256、许可证和完整运行命令。我们
可以按要求提供仓库内的结构化证据引用，但不会发送私有密钥、完整模型或
未经许可的厂商二进制。
