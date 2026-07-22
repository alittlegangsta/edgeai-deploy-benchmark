# YOLOv5n v7.0 Model Contract

This contract records values observed from the real Task 002 artifacts.
It is not an expected-output template.

## Provenance

- Source: `https://github.com/ultralytics/yolov5.git`
- Tag: `v7.0`
- Revision: `915bbf294bb74c859f0b41f1c23bc395014ea679`
- Source-weight SHA256: `4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3`
- Source-weight size: `4062133` bytes
- Source-weight reference: `https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt`
- ONNX SHA256: `78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`
- ONNX size: `7921360` bytes

## Export Configuration

- Input size: `[640, 640]`
- Batch: `1`
- Precision/layout: `FP32 NCHW`
- ONNX opset: `12`
- Dynamic axes: `False`
- Simplify: `False`
- Graph NMS requested: `False`

## Observed ONNX Interface

| Kind | Name | Shape | Dtype |
| --- | --- | --- | --- |
| Input | `images` | `[1, 3, 640, 640]` | `FLOAT` |
| Output | `output0` | `[1, 25200, 85]` | `FLOAT` |

Observed class count: `80`.

## Graph Validation

- ONNX checker: `PASS`
- Default opset imports: `[{'domain': '', 'version': 12}]`
- Node count: `292`
- Graph contains NMS: `False`
- Dynamic dimensions: none observed in the public inputs or outputs.
- Simplification was not requested; the exact exporter command omits `--simplify`.
