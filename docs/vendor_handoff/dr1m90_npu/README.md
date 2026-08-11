# DR1M90 NPU enablement handoff

Status: `READY_FOR_VENDOR_HANDOFF`

This is a minimal support package derived only from the completed Task 028
evidence. It is intended for Anlogic/Milianke technical support. It contains
identity, commands, observations, capability limits and questions; it does not
contain vendor binaries, SDKs, ONNX models, datasets, board logs, credentials
or private keys.

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

## Files

- [environment.md](environment.md) — board, source, runtime and model identity.
- [reproduction.md](reproduction.md) — minimal commands and observed stages.
- [capability_boundary.md](capability_boundary.md) — compiled support matrix.
- [questions.md](questions.md) — exact information requested from support.
- [vendor_support_request.md](vendor_support_request.md) — concise Chinese
  request ready to send.
- [manifest.json](manifest.json) — package schema and evidence hashes.

The authoritative measurements remain in `results/evidence/028/`; this package
references those files by repository-relative path and SHA256.
