# Task 032 — ALHardNPU fusion eligibility

## Result

`FUSION_PREDICATE_NOT_RECOVERABLE`

This is a bounded result for the audited AArch64 `libarmnn.so.32.1` family and
the immutable Task 028/031 records. It is not a statement that DR1M90 hardware
or a future Anlogic backend cannot run YOLOv5n.

The retained Task 028 status remains `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY` with
the scoped blocker
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`.

## What the binary proves

The audited library is an AArch64 stripped shared object, SHA256
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`, SONAME
`libarmnn.so.32`, Build ID
`9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895`. It contains the direct fusion
symbols `RunOptimization`, `findLastLayer`, `Run`, `RunFC`, `checkConv`,
`checkAct`, `checkPool`, weight-transpose helpers, `ALHardNPULayer`,
`AlnpuALHardNPUWorkload`, and `CreateALHardNPU` under
`ConvertConv2dIntoALHardNPUImpl`/ALHardNPU.

The concrete `AlnpuLayerSupport` override set is:

| Alnpu override | Static status |
| --- | --- |
| `IsALHardNPUSupported` | override present |
| `IsConcatSupported` | override present |
| `IsConstantSupported` | override present |
| `IsInputSupported` | override present |
| `IsLayerSupported` | override present |
| `IsMemCopySupported` | override present |
| `IsOutputSupported` | override present |
| `IsPooling2dSupported` | override present |
| `IsPreluSupported` | override present |
| `IsResizeSupported` | override present |

The generic `IsConvolution2dSupported`, `IsActivationSupported`,
`IsSplitterSupported`, `IsAdditionSupported`, `IsMultiplicationSupported`,
and `IsElementwiseUnarySupported` symbols resolve to `LayerSupportBase` in this
build. This is a dispatch fact, not proof that every possible fused graph is
rejected.

The binary contains float, unsigned-8 and signed-8 ALHardNPU template symbols.
Strings indicate checks involving weight/input/bias types, input channels,
output dimensions, padding, kernel/stride modes, broadcast and Add-only
elementwise handling. They are recorded as string-level indications only:
without the backend source or AArch64 disassembly their branches and exact
association with `checkConv`/`checkAct`/`checkPool` cannot be proven.

## Face positive control

The approved Task 026 run used `yolo_face_uint8_15.onnx` (SHA256
`5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c`, opset
14, input `[1,3,416,416]` FLOAT). The ONNX graph has no ALHardNPU custom node.
It contains 13 Conv, 11 Relu, 6 MaxPool, 1 Concat, 1 Resize, 33
QuantizeLinear and 59 DequantizeLinear nodes, and no Split. The strict Alnpu
run reported these three assignments:

```text
135 | Alnpu | ALHardNPU
134 | Alnpu | ALHardNPU
126 | Alnpu | ALHardNPU
```

Parser, `Optimize`, `LoadNetwork` and exit code all passed, with CPU fallback
disabled. These assignments are evidence that the optimizer selected a
vendor-specific fused/custom workload path. The retained log has no parser
layer names, original ONNX node IDs, tensor descriptors, scales or zero-points
for each assignment; therefore the exact three source-node regions cannot be
reconstructed honestly. The common graph inventory is retained in
`results/evidence/032/face_fusion_regions.json`.

## YOLOv5n comparison

The frozen FP32 model is opset 12, input `[1,3,640,640]`, output
`[1,25200,85]`, with 60 Conv, 60 Sigmoid, 69 Mul, 10 Add, 21 Concat, 3 Split,
3 MaxPool, 2 Resize, 4 Floor and 2 Shape nodes. The original graph has no Q/DQ.

The unchanged `AL_onnx_pass` flow is:

```text
onnx.load
→ onnxsim.simplify
→ fixed-shape inference
→ YOLOv5 Detect extraction
→ optional Conv/FC split
→ ONNX opset conversion
→ check_onnx_model
→ ONNX Runtime static QDQ quantization
```

Its official Detect-cropped FP32 output is three raw FLOAT heads
`[1,255,80,80]`, `[1,255,40,40]`, `[1,255,20,20]`; it is intentionally no
longer the original `[1,25200,85]` output. The official UINT8 graph adds 200
Q and 320 DQ nodes around the generic graph. No ALHardNPU custom ONNX node,
`npu_runtime`, `rt.bin`, or `weight.bin` is produced by this path.

The first observed real backend gates were:

| Candidate | First observed gate | Stage |
| --- | --- | --- |
| YOLOv5n UINT8 | QAsymmU8 Conv2d, Activation and ElementwiseBinary | Alnpu `Optimize` |
| YOLOv5n INT8 | QSymmS8 Conv2d, Activation and ElementwiseBinary | Alnpu `Optimize` |
| Vendor YOLOv8n control | QAsymmU8 Splitter | Alnpu `Optimize` |

These are real graph observations with CPU fallback disabled. They identify
the current generic dispatch boundary but do not identify the exact first
`ConvertConv2dIntoALHardNPUImpl` predicate. In particular, the face success
must not be generalized into generic Conv2d support, and the YOLO failures
must not be converted into a claim of inherent YOLO architecture
incompatibility.

## Why the conclusion is conservative

No ArmNN backend source was present in the audited local scopes. The library
is stripped, and the WSL host has no AArch64-capable `objdump`/LLVM
disassembler; host `objdump -f` reports `architecture: UNKNOWN`. Symbols,
vtable dispatch and strings recover the existence of the fused path and a
partial whitelist, but not the complete predecessor/successor pattern,
layout, dilation/groups, exact channel/alignment limits, activation fusion
rules or scale/zero-point matrix. Consequently this audit cannot choose the
user's A or B conclusions without inventing a predicate.

No model, QDQ, runtime, board, bitstream or benchmark was changed or run in
Task 032. A future reopen requires vendor source/build evidence for the
predicate, a backend that supports the required generic quantized YOLO layers,
an APUG1205-compatible native compiler/runtime, or an official GEG400 YOLO
deployment chain.

Structured evidence: `results/evidence/032/`.
