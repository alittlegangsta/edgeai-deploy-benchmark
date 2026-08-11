# Audited Alnpu capability boundary

## Scope

This matrix describes only the exact AArch64 `libarmnn.so.32.1` identified in
Task 028 (`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`,
build ID `9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895`). It is not a claim about
all DR1M90 hardware, all SoftNPU bitstreams, or future vendor library builds.

## Compiled method matrix

| Arm NN support method | Observed implementation | Handoff interpretation |
|---|---|---|
| `IsALHardNPUSupported` | `AlnpuLayerSupport` override | Specialized path observed; face control assigns `ALHardNPU` |
| `IsConcatSupported` | `AlnpuLayerSupport` override | Override exists; generic YOLO closure not proven |
| `IsConstantSupported` | `AlnpuLayerSupport` override | Override exists |
| `IsInputSupported` | `AlnpuLayerSupport` override | Override exists |
| `IsLayerSupported` | `AlnpuLayerSupport` override | Dispatch entry exists |
| `IsMemCopySupported` | `AlnpuLayerSupport` override | Override exists |
| `IsOutputSupported` | `AlnpuLayerSupport` override | Override exists |
| `IsPooling2dSupported` | `AlnpuLayerSupport` override | Override exists |
| `IsPreluSupported` | `AlnpuLayerSupport` override | Override exists |
| `IsResizeSupported` | `AlnpuLayerSupport` override | Override exists; tested contracts remain limited |
| `IsConvolution2dSupported` | `LayerSupportBase` default | Generic YOLO Conv2d rejected in real quantized graph |
| `IsActivationSupported` | `LayerSupportBase` default | Generic YOLO Activation rejected in real quantized graph |
| `IsSplitterSupported` | `LayerSupportBase` default | Vendor YOLOv8n first fails at `QAsymmU8 Splitter` |
| `IsAdditionSupported` | `LayerSupportBase` default | No generic Add support claim |
| `IsMultiplicationSupported` | `LayerSupportBase` default | No generic Mul support claim |
| `IsElementwiseUnarySupported` | `LayerSupportBase` default | Generic elementwise path is not a YOLO deployment proof |

The generic rejection strings in the binary include `Do Not Supported`, type
mismatch, shape-limit and `only support add now` messages. Synthetic QDQ probes
remain parser-dialect-inconclusive; the real YOLOv5n and YOLOv8n graph failures
are the authoritative boundary evidence.

## Why the face control passes

The face control is FLOAT input `[1,3,416,416]` with two FLOAT outputs and no
Split node. Its strict Alnpu-only run completed and reported three
`Alnpu|ALHardNPU` assignments. This is a vendor fused/custom workload path;
individual ONNX Conv nodes must not be interpreted as generic Arm NN Conv2d
coverage.

## Conclusion for support

```text
CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE
```

The result is scoped to the audited binary and graph dialect. Runtime version
skew was not proven: the available release runtime objects are byte-identical
to the retained board runtime. No CPU fallback or benchmark was accepted.
