# Minimal reproduction

The commands below are the shortest reproduction sequence. Angle-bracketed
locations are placeholders for files already held by the vendor or by the
engineer running the reproduction; they are not repository assets.

## 1. Host conversion

Use the exact `dr1m90_npu` `release` checkout and its unchanged requirements in
an isolated environment. Do not change the frozen model.

```bash
python -m pip install -r <DR1_NPU_SCRIPTS>/requirements.txt
python <DR1_NPU_SCRIPTS>/AL_onnx_pass.py \
  --input_model <FROZEN>/yolov5n.onnx \
  --calibrate_dataset <CALIBRATION_DIR> \
  --quant_type uint8 \
  --yolo_type yolov5
```

Task 028 observed exit code `0`. The official path produced a valid
Detect-cropped FP32 graph and a uint8 QDQ graph. It reported SoftNPU operators
`Add`, `MaxPool`, `Concat`, and `Resize`. The output contract intentionally
changes from `[1,25200,85]` to three raw YOLO heads; this is a vendor-tool
contract, not a changed project baseline.

The frozen FP32 host reference retained five detections and passed the existing
golden. The quantized host gate was not accepted: the one-image uint8 result
had minimum IoU `0.8421554845490358` and maximum confidence delta
`0.09312496031303408`; the deterministic 500-image smoke also failed. These
are diagnostic host results, not an NPU benchmark or a reason to hand-edit the
graph.

## 2. Strict Arm NN/Alnpu probe

Build or use the recorded AArch64 diagnostic runner and request Alnpu only:

```bash
<AARCH64_RUNNER> \
  --model <MODEL> --input <INPUT> \
  --backend Alnpu --allow-cpu-fallback 0
```

The exact runner and library identities are in `environment.md`. Preserve
`LD_LIBRARY_PATH` so the recorded Arm NN closure is loaded; do not silently
add `CpuAcc` or `CpuRef`.

## 3. Expected stage outcomes

| Stage | Expected observed result |
|---|---|
| Parser | PASS; network is created |
| Arm NN Network | PASS |
| Alnpu LayerSupport | BLOCKED for generic quantized YOLO layer slots |
| Optimize | Fails on real YOLO graph (`QAsymmU8` Splitter for YOLOv8n; quantized Conv2d/Activation/ElementwiseBinary for YOLOv5n) |
| LoadNetwork | `NOT_REACHED` |
| NPU execution | `NOT_REACHED` |
| CPU fallback | Not accepted |

The face positive control is a separate check:

```text
request: Alnpu only
parser/Optimize/LoadNetwork: completed
assignment: three Alnpu|ALHardNPU workloads
fallback: false
```

The ONNX file itself contains no `ALHardNPU` custom node. ArmNN/Alnpu forms
three `Alnpu|ALHardNPU` workloads during `Optimize`; this is a vendor
fused/custom backend path and does not prove generic Conv2d support. The
audited binary exposes `ConvertConv2dIntoALHardNPUImpl`, `checkConv`,
`checkAct` and `checkPool`, but the complete fusion predicate remains
unrecoverable from public evidence.

## Evidence references

- `trackc_environment.json` — source checkout and host environment.
- `trackc_official_smoke.json` — unmodified conversion and host outcomes.
- `trackc3_board_smoke.json` and `trackc3_board_int8_smoke.json` — real graph
  Alnpu-only failures.
- `trackc3_runtime_compatibility_matrix.json` — matched runtime comparison.
- `trackc3_capability_face_path_audit.json` — final capability interpretation.
