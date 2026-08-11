# Task 031: Official NPU asset recovery and GEG400 compatibility

Task 031 is a read-only archaeology of the three locally cloned official
repositories. The checkouts, LFS stores, models, libraries, archives and board
media remain outside Git. No vendor executable, build script, module, bitstream
or board was executed or modified.

## Result

The audit is complete with primary verdict
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. No newly recovered public asset is
sufficient to reopen YOLOv5n NPU integration. This is a scoped result for the
audited AArch64 Arm NN/Alnpu build and the reachable public repository history;
it is not a claim that DR1M90 hardware or a future vendor release cannot run
YOLO.

The two earlier routes remain frozen:

| Route | Result | Evidence |
| --- | --- | --- |
| Raw ONNX → ArmNN/Alnpu | `BLOCKED_UNSUPPORTED_ALNPU_GRAPH` | Task 028 C3 evidence |
| APUG1205 native compiler/runtime | `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE` | Task 028 native evidence |
| Official `AL_onnx_pass` | C1 conversion `PASS`; C2 paused; C3 LayerSupport blocked; C4 not run | Task 028 Track C evidence |

## Repository and history scope

The audited sources are represented as `<vendor-root>/sdk`,
`<vendor-root>/dr1m90_npu`, and `<vendor-root>/dr1_demo_prjs` in the evidence.
Their committed identities are recorded in
`results/evidence/031/official_repo_inventory.json`; all three checkouts were
already dirty and were not changed. The audit covered current trees, all
reachable refs, deleted-file names, Git LFS pointer rules/local objects, and
README/download/archive references. The local Git LFS executable was
unavailable, so LFS pointers and the available object store were inspected
without pretending that a missing remote object had been recovered.

`npuv1_release/release_2024_06_25` occurs only as a historical workspace path
in documentation. No compiler, archive, `tmfile`, `rt.bin`, `weight.bin`,
`convert_tool`, `al_ai_flow`, `nn_compiler`, `npu_runtime` or `npu_c_api.h` was
found in reachable objects. The README reference to
`yolov5s_sim_quant_uint8.onnx` is not the model itself; no reachable file,
LFS payload, download script or archive supplied it.

## Face ONNX provenance

The SDK tag blob and the dr1m90_npu LFS pointer identify the same external
model, SHA256
`5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c`, size
8,709,145 bytes. Static ONNX parsing reports PyTorch 1.13.0, IR version 7,
opset 14, no custom domain, 124 nodes and 113 initializers. Its input is
`FLOAT [1,3,416,416]`; outputs are `FLOAT [1,18,26,26]` and
`FLOAT [1,18,13,13]`. The graph contains Conv, MaxPool, Relu, Resize,
QuantizeLinear and DequantizeLinear nodes, but no `ALHardNPU` node/domain.

Consequently `ALHardNPU` is produced after parsing by the Arm NN optimization
path. Retained Task 028 execution evidence measured three
`Alnpu|ALHardNPU` fused/custom assignments for this face control. That is a
different path from generic quantized YOLO Conv2d/Activation/Splitter/Add/Mul
support; it does not prove that the ONNX graph carries a vendor custom op.

## Arm NN capability boundary

Two SHA256-deduplicated AArch64 `libarmnn.so.32.1` families were found:

* the SDK 2024.10/2025.01 family:
  `9cd854c95c9992920aee26195bee3953357b315bce8baddb2d6c4e7327efc547`;
* the SDK 2025.07/2026.01 and dr1m90_npu release family:
  `5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`.

The matching parser hashes are recorded in the JSON evidence. Static
`nm`/`readelf`/`objdump` and RTTI/vtable review found the same ten concrete
`AlnpuLayerSupport` overrides in both builds:

`IsALHardNPUSupported`, `IsConcatSupported`, `IsConstantSupported`,
`IsInputSupported`, `IsLayerSupported`, `IsMemCopySupported`,
`IsOutputSupported`, `IsPooling2dSupported`, `IsPreluSupported`, and
`IsResizeSupported`.

`IsConvolution2dSupported`, `IsActivationSupported`, `IsSplitterSupported`,
`IsAdditionSupported`, `IsMultiplicationSupported`, and
`IsElementwiseUnarySupported` are not Alnpu overrides and resolve to the
generic `LayerSupportBase` rejection path. Both binaries do contain
`ConvertConv2dIntoALHardNPUImpl` and ALHardNPU workload symbols. This explains
the face positive without constituting a standalone ALHardNPU generator or a
more capable generic backend. No materially different Alnpu backend build
was recovered.

## GEG400 HPF/TD matrix

The SDK's named HPFs are AD101V20/AD103V20. Reachable D20.1, D20.2 and D20.3
YOLO HPFs are AD101/AD103 and encode GEG484/MEG484-family devices; their
metadata has `SOFT_YOLO=1` but does not identify a GEG400 project. Generic C20
metadata contains mixed GEG400/GEG484 strings but lacks the YOLO SoftNPU
design flags and is not a GEG400 YOLO HPF/TD.

The retained Task 028 05-5 package is a separate GEG400 context: its selected
platform bitstream is
`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`, and its
HPF flags include `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1` and
`SOFT_RESIZE=1`. This evidence is reused, not overwritten. No additional
official `DR1M90GEG400 + NPU_Yolo` HPF/TD was found in the three repositories.

## Public chain and next action

The public `AL_onnx_pass.py` path is an ONNX simplification/shape/Detect
extraction/versioning/ONNX Runtime QDQ quantization pipeline. The public demo
then uses ArmNN OnnxParser → `armnn::Optimize` → `LoadNetwork`; it does not
invoke a native compiler or `npu_runtime`. No hidden conversion step is
documented in the source. This is sufficient for the retained face demo, but
not for the generic YOLOv5n graph boundary demonstrated in Task 028.

Task 029 remains the correct next action: send the frozen handoff to
Anlogic/Milianke and request a generic quantized-YOLO Alnpu backend, an
APUG1205-compatible compiler/native runtime, or a version-matched GEG400 YOLO
deployment package. No benchmark, CPU fallback, model edit or bitstream
change is justified by this audit.

Structured evidence: `results/evidence/031/`.
