# Questions for Anlogic / Milianke support

Please answer with exact release names, commit/tag, file names, SHA256 values,
target board/package, and compatibility notes where applicable.

1. What is the supported official deployment and conversion flow for a custom
   YOLO model on DR1M90 GEG400, specifically MLK-F3P-CZ02? Is there a complete
   GEG400 YOLO package rather than the AD101V20/GEG484 example?
2. After `AL_onnx_pass`, should the generated graph enter ArmNN/OnnxParser and
   `Alnpu` directly, or is an additional vendor conversion/fusion stage required?
3. Is there an Alnpu backend build that supports the generic quantized YOLO
   layer set, including Conv2d, Activation, Splitter/Concat and elementwise
   Add/Mul for QAsymmU8 or QSymmS8?
4. Does deployment require an additional ALHardNPU fused graph pass, model
   compiler, operator lowering step, or backend configuration not present in
   the public `AL_onnx_pass` path?
5. How can an authorized customer obtain the APUG1205-compatible
   `convert_tool`, `al_ai_flow`, native runtime, headers and their versioned
   positive-control example?
6. Which HPF/SoftNPU/bitstream and TD project are the supported YOLO NPU
   design for DR1M90 GEG400? Please provide the matching addresses, IRQs,
   `SOFT_YOLO`/resize settings and board identity.
7. Please provide the compatibility matrix linking SDK, Linux/Buildroot,
   Arm NN/OnnxParser/Alnpu runtime, model compiler, model format, HPF,
   bitstream, Device Tree and kernel modules.
8. Please explain why the face `ALHardNPU` control can load while real
   quantized YOLOv5n and YOLOv8n graphs fail at `Alnpu Optimize`, and identify
   the exact supported graph dialect or conversion contract.
9. Please provide the complete `ALHardNPU` fusion/model constraints, including
   the complete fusion predicate and eligibility predicate corresponding to
   `ConvertConv2dIntoALHardNPUImpl`,
   `checkConv`, `checkAct` and `checkPool`. The public audit cannot recover
   these conditions and therefore does not classify YOLOv5n as inherently
   incompatible.
