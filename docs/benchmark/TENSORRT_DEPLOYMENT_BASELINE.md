# TensorRT YOLOv5n baseline

Task 037 established a PC GPU TensorRT baseline without changing the frozen
YOLOv5n v7.0 contract. The run used the Ubuntu WSL2 GPU bridge for an NVIDIA
GeForce RTX 4060 Ti (compute capability 8.9), CUDA Toolkit 12.9.86 and
TensorRT 10.13.3. CUDA was installed as toolkit/development components only;
no Linux NVIDIA display driver was installed.

The frozen ONNX is `models/yolov5n-v7.0/yolov5n.onnx` (SHA256
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`) with
static FP32 input `[1,3,640,640]`, raw FP32 output `[1,25200,85]`, and no graph
NMS. The project-owned `edgeai_tensorrt_image` runner reuses the common
preprocess, decode, NMS, visualization and Golden comparison code.

## Accepted FP32 configuration

TensorRT's default TF32-enabled build exceeded the existing confidence gate.
The accepted engine was built with `--noTF32`:

```text
trtexec --onnx=models/yolov5n-v7.0/yolov5n.onnx \
  --saveEngine=/tmp/task037/yolov5n_fp32_no_tf32.engine \
  --memPoolSize=workspace:2048M --builderOptimizationLevel=3 \
  --noTF32 --skipInference
```

Engine SHA256 is
`a3ad9715f3560e46cae2cacfa06ca11d1468c42947eea9487a15c82d84b968d6`.
With 10 warmups and 100 timed repetitions, the project runner reported:

| stage | mean | P50 | P95 |
| --- | ---: | ---: | ---: |
| host inference wall | 3.712445 ms | 3.482152 ms | 5.222537 ms |
| CUDA H2D | 0.457854 ms | 0.449760 ms | 0.525312 ms |
| CUDA inference | 1.674261 ms | 1.460416 ms | 2.739680 ms |
| CUDA D2H | 0.828420 ms | 0.802208 ms | 0.961152 ms |
| preprocess | 1.583344 ms | 1.560376 ms | 1.821055 ms |
| postprocess | 4.019569 ms | 3.960571 ms | 4.588547 ms |
| end-to-end pipeline | 9.283727 ms | 9.104986 ms | 10.790646 ms |

Pipeline throughput was 107.715355 FPS and peak process RSS was 537596 KiB.
The Golden gate passed with five detections, minimum class-matched IoU
`0.9999971389770508`, and maximum confidence delta
`0.0000020265579223632812`.

## FP16 result and COCO gate

A real FP16 engine was built with TensorRT's `--fp16` flag (SHA256
`7f99cc9f628613a71ec993898a9825c0c45f4c5129862f8350fea0161e653c8a`). Its
single-image Golden diagnostic remains five detections, minimum IoU
`0.9935288429260254`, and maximum confidence delta `0.005570024251937866`.
This diagnostic is retained without changing any tolerance, model, threshold or
postprocess.

Before reviewing performance, the exact Task035 independent COCO split was
evaluated with confidence `0.001`, NMS IoU `0.6`, maxDet `100`, the standard
COCO80 category mapping and original-pixel xywh boxes. It contains 4,500
images, disjoint from the 500 calibration images. TensorRT FP32 scores
`mAP50=0.448302671`, `mAP50-95=0.274720465`; TensorRT FP16 scores
`0.448105440` and `0.274786550`, respectively. FP16 deltas are `-0.000197230`
and `+0.000066085`, with zero detection images, passing the frozen absolute
`0.01/0.01` gate. FP16 is therefore `TENSORRT_FP16_READY`; the dependency-free
evaluator and all identities are in `results/evidence/037/coco_accuracy.json`.

With the same ten warmups and 100 repetitions, FP16 CUDA inference mean is
`1.370379 ms` and end-to-end pipeline mean `9.408935 ms` (106.281952 FPS),
versus FP32 `1.674261 ms` and `9.283727 ms` (107.715355 FPS). This is a
`1.221751x` inference speedup but a `0.986693x` pipeline ratio (1.3307%
regression), so no end-to-end FPS improvement is claimed. GPU inference is
18.034% of the FP32 pipeline, while preprocessing, postprocess and H2D+D2H
account for 17.055%, 43.297% and 13.855%; the remaining bottleneck is CPU
pipeline work. Serialized engines, raw output, images and large logs remain
outside Git. Structured evidence is checked by
`scripts/validate_task037_tensorrt.py`.

The TensorRT reference command used for an inference-only sanity check was:

```text
trtexec --loadEngine=/tmp/task037/yolov5n_fp32_no_tf32.engine \
  --iterations=100 --warmUp=200 --duration=1 --noDataTransfers \
  --percentile=50,95
```

It completed successfully and reported 1.43621 ms mean GPU compute with no
data transfers; this is a tool reference, not the project end-to-end result.
