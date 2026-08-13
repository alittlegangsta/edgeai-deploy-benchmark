# DR1M90 NPU enablement handoff

Status: `WAITING_FOR_VENDOR_INPUT`

This is a minimal support package derived only from the completed Task 028
evidence. It is intended for Anlogic/Milianke technical support. It contains
identity, commands, observations, capability limits and questions; it does not
contain vendor binaries, SDKs, ONNX models, datasets, board logs, credentials
or private keys.

The package is ready to send. `WAITING_FOR_VENDOR_INPUT` means that the next
step is an answer from Anlogic/Milianke, not more local reverse engineering.

## Executive result

The audited AArch64 `libarmnn.so.32.1` accepts the parser and creates an Arm NN
network, but its compiled `AlnpuLayerSupport` boundary rejects the generic
quantized YOLO layer slots needed by YOLOv5n. The face control is a real
`Alnpu|ALHardNPU` positive path, not evidence that generic Arm NN Conv2d is
supported. Task 028 therefore ended as:

```text
primary: BLOCKED_EXTERNAL_VENDOR_DEPENDENCY
scoped blocker: CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE
```

This is scoped to the recorded library identity and observed graph dialects. It
is not a claim about DR1M90 hardware or a future vendor backend.

## Task 032 fusion addendum

The latest bounded fusion audit is included by reference and does not alter
Task 028/031 evidence:

- `yolo_face_uint8_15.onnx` contains no `ALHardNPU` custom node.
- During ArmNN `Optimize`, the audited AArch64 `libarmnn.so.32.1` forms three
  `Alnpu|ALHardNPU` assignments for the face positive control.
- The binary contains `ConvertConv2dIntoALHardNPUImpl`, `checkConv`, `checkAct`
  and `checkPool`.
- Public logs and the stripped binary are insufficient to recover the complete
  fusion predicate or exact source-node regions.
- Therefore this handoff does not claim that YOLOv5n is inherently
  incompatible. Task 028 remains `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY` pending
  a vendor-supported backend, compiler/runtime, or deployment chain.

The authoritative Task 032 records are
`results/evidence/032/fusion_symbol_audit.json`,
`results/evidence/032/face_fusion_regions.json`, and
`results/evidence/032/fusion_eligibility_verdict.json`.

## Files

- [environment.md](environment.md) — board, source, runtime and model identity.
- [reproduction.md](reproduction.md) — minimal commands and observed stages.
- [capability_boundary.md](capability_boundary.md) — compiled support matrix.
- [questions.md](questions.md) — exact information requested from support.
- [vendor_support_request.md](vendor_support_request.md) — concise Chinese
  request ready to send.
- [manifest.json](manifest.json) — package schema and evidence hashes.

The authoritative runtime measurements remain in `results/evidence/028/`; the
fusion addendum is the immutable static audit in `results/evidence/032/`. This
package references both by repository-relative path and SHA256.
