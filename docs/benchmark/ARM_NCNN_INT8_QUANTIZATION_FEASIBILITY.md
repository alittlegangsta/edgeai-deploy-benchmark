# ARM ncnn INT8 quantization feasibility (Task 035)

Task 035 audits the pinned ncnn `20240410` / commit
`56775de50990ab7f16627efdcf5529b49541206f` INT8 toolchain against the frozen
YOLOv5n v7.0 ncnn contract. It does not use AL_onnx_pass, change the model,
thresholds, preprocessing, postprocessing, boot assets or board system.

## Toolchain and data

The pinned host tools are `ncnnoptimize`, `ncnn2table`, and `ncnn2int8` from
the 20240410 build. The official flow is optimize → calibration table →
`ncnn2int8`; tested table methods are ACIQ, KL and EQ. The ARM source contains
NEON INT8 convolution/depthwise/quantize/dequantize/requantize kernels. Task
034 established an AArch64 Cortex-A35-class ASIMD/NEON path without dot-product
or I8MM.

The user supplied the official local `annotations_trainval2017.zip` and
`val2017.zip` archives. Their sizes, MD5/SHA256 and extracted annotation
identity are frozen in `results/evidence/035/coco_accuracy_readiness.json`.
The 18GB `train2017` image archive was not supplied. Therefore the expanded
host validation uses a deterministic fallback from `val2017`: 500 images for
calibration and all remaining 4,500 images for independent evaluation. Image
IDs are sorted, shuffled with `random.Random(35035)`, and the first block is
calibration. The evaluation manifest is disjoint from calibration; this is a
large independent engineering gate, not a COCO leaderboard claim.

The earlier bounded 22-image calibration and one-image FP32-reference
regression remain retained as historical evidence. The prior "43" is a Python
test count, not a 43-image Golden set.

## Expanded host evaluation and evaluator repair

The first held-out report was invalidated: its evaluator loaded predictions for
500 images but summed the ground-truth denominator over all 5000 annotation
image IDs, and its fixed deployment confidence `0.25`/NMS IoU `0.45` output was
not a COCO AP confidence sweep. The old values remain in the evidence as
`SUPERSEDED_INVALID_SCOPE_AND_THRESHOLD`.

The corrected evaluator constrains `COCOeval.params.imgIds` to exactly the
evaluation manifest (the earlier 500-image report is retained; the final
4,500-image manifest is `a219a5...` with IDs `3b3b23...`), verifies matching
prediction IDs for every model, maps model classes by COCO category name, and
converts original-pixel `xyxy` boxes to COCO `xywh`. AP uses confidence `0.001`,
NMS IoU `0.6`, and max 100 detections per image; deployment remains unchanged
at confidence `0.25` and NMS IoU `0.45`. Crowd annotations are retained for
COCO-style ignore matching; non-crowd annotations form the AP denominator.

The final independent result is:

| model | predictions | mAP50 | mAP50-95 | ΔmAP50 | ΔmAP50-95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| FP32 | 776899 | 0.457605 | 0.279777 | 0 | 0 |
| EQ | 800831 | 0.443309 | 0.265115 | -0.014296 | -0.014662 |

Both absolute degradations are at most `0.02` and neither model has a
zero-detection evaluation image, so the final independent accuracy gate is
`PASS`. The earlier 500-image table (including ACIQ/KL) remains in evidence as
a corrected intermediate comparison; ACIQ is secondary and KL is no longer a
primary path.

The exact ID, category, bbox, prediction and metric identities are in
`results/evidence/035/coco_evaluator_audit.json`. The FP32 sanity floor
(`mAP50 >= 0.25`, `mAP50-95 >= 0.15`) passes, so the earlier anomalous FP32
value was an evaluator defect rather than evidence of a broken model.

The earlier bounded ACIQ candidate produced 3 rather than 5 frozen-reference
detections (minimum matched IoU `0.9154784851416163`, maximum confidence delta
`0.0782729983329773`) and KL produced zero; those facts remain unchanged as
secondary diagnostics. On the frozen `pc_reference.jpg`, the
expanded-calibration candidates produced 4 (ACIQ), 1 (KL), and 5 (EQ)
detections; the IoU/confidence deviations remain recorded, but are not alone a
final INT8 verdict after the evaluator repair.

## ARM result and status boundary

The user-defined accuracy gate is explicit: absolute ΔmAP50 and ΔmAP50-95 must
each be no greater than `0.02`, with no catastrophic zero-detection failure.
EQ passes on all 4,500 independent images and becomes the
`EQ_INT8_ARM_BENCHMARK_CANDIDATE`.

The same AArch64 `NCNN_INT8=ON` Release profiler ELF was then used for FP32 and
EQ on the DR1 board. Five independent processes per variant ran three warmups
and ten retained samples, with threads=2, default scheduling and packing on.

| variant | inference mean / P50 / P95 (ms) | pipeline mean / P50 / P95 (ms) | FPS | peak RSS (KiB) |
| --- | --- | --- | ---: | ---: |
| FP32 | 1882.246 / 1877.733 / 1888.663 | 1973.146 / 1968.619 / 1984.812 | 0.506805 | 168376 |
| EQ INT8 | 1173.208 / 1172.656 / 1187.336 | 1266.500 / 1264.251 / 1285.630 | 0.789578 | 150836 |

EQ gives `1.604359x` inference speedup, `1.557952x` pipeline speedup,
`55.795208%` FPS gain and `-10.417162%` peak RSS change. The diagnostic layer
build shows 60 Convolution layers falling from `1467.013 ms` to `756.940 ms`
aggregate (`1.938084x`). The strict single-image frozen-reference comparison
remains a retained secondary `FAIL_CORRECTNESS_GATE`; it is not silently
relabeled because the primary task-level decision comes from the annotated
independent COCO gate.

The resulting decision is `INT8_ACCEPTED`. Task 033/034's FP32 configuration
remains the historical baseline; EQ INT8 is an additional accepted ARM CPU
candidate. This is an ARM CPU benchmark, not an NPU result or NPU benchmark.
Frequency and temperature
were unavailable and remain null.

The VM `UtilBindVsockAnyPort:307: socket failed 1` condition is recorded as an
independent infrastructure issue and is not used as an INT8 model verdict.

## Required evidence

```text
results/evidence/035/
  int8_source_build_audit.json
  int8_tool_audit.json
  calibration_manifest.json
  evaluation_manifest.json
  int8_quantization_run.json
  int8_correctness.json
  int8_build_matrix.json
  int8_layer_profile.json
  arm_int8_benchmark.json
  int8_bounded_validation.json
  coco_accuracy_readiness.json
  validation.json
```

Large source archives, build trees, model files, calibration images, libraries,
board logs and binaries remain outside Git. Evidence stores identities, hashes,
commands, summaries and explicit limitations.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/035_arm_ncnn_int8_quantization_inference_feasibility.md
cpp/apps/arm_cpu_profiler.cpp
cpp/tests/test_arm_cpu_profiler.cpp
docs/benchmark/ARM_NCNN_INT8_QUANTIZATION_FEASIBILITY.md
scripts/validate_task035_ncnn_int8.py
scripts/vendor/audit_task035_ncnn_int8.sh
scripts/vendor/run_task035_ncnn_int8.sh
results/evidence/035/**
```

No dependency installation, board access, SD/eMMC change, NPU change, commit or
push is part of this validation continuation.
