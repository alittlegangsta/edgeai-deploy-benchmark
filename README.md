# EdgeAI Deploy Benchmark

EdgeAI Deploy Benchmark is a reproducible PC deployment and measurement baseline
for a fixed YOLOv5n v7.0 detector. The PC implementation contains Python ONNX
Runtime, C++ ONNX Runtime, and C++ ncnn image/video paths with shared correctness
and benchmark contracts.

## Current status

Tasks 001–012 are completed, Checkpoint C is human-approved, and PC Stage 1 is
complete. Stage 2 for the Anlogic DR1 ARM CPU has not been implemented or started.
Its status remains `Not implemented / Planned`.

## PC architecture and model lineage

```text
YOLOv5n v7.0 weights
├── frozen ONNX ──> Python ORT / C++ ORT
└── frozen TorchScript ──> pnnx 20240410 ──> ncnn param/bin ──> C++ ncnn
```

The two ONNX Runtime implementations use the same frozen ONNX model. The ncnn implementation uses a separately frozen TorchScript-to-pnnx model generated from the same YOLOv5n v7.0 weights and validated for semantic equivalence.

YOLOv5n was selected as a small, established detector suitable for learning and
comparing deployment pipelines. The source weights SHA256 is
`4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3`;
the frozen ONNX SHA256 is
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`.
The input contract is batch 1, FP32, NCHW `[1,3,640,640]`.

## Environment and dependencies

- WSL2 Linux x86_64; CPU affinity scheduler managed; pinning disabled.
- Python 3.12.3, ONNX Runtime 1.18.1 CPUExecutionProvider, OpenCV 4.10.0.
- GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1, system OpenCV 4.6.0.
- C++ ONNX Runtime SDK 1.18.1 and ncnn 1.0.20240410.
- ORT intra/inter-op threads 1, ncnn threads 1, OpenCV threads 1.
- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
  `NUMEXPR_NUM_THREADS` are all 1.

The Python/C++ OpenCV version difference limits single-cause attribution of
preprocess performance even though tensor and detection correctness pass.

## Repository structure

- `python/`: Python ORT applications and common processing.
- `cpp/`: C++ common modules and ORT/ncnn applications.
- `configs/`: frozen inference and benchmark contracts.
- `models/`: manifests; generated model binaries remain Git-ignored.
- `tasks/`: auditable task state and execution records.
- `results/`: committed small evidence and generated local outputs.
- `docs/`: model, benchmark, and PC acceptance documentation.

## Model preparation

Model weights, ONNX, TorchScript, ncnn param/bin, SDKs, and large videos are
intentionally Git-ignored. Put the official v7.0 weights at
`models/yolov5n-v7.0/yolov5n.pt`, verify the Task 002 SHA256, and export ONNX
from a read-only YOLOv5 v7.0 checkout:

```bash
export YOLOV5_SOURCE=/path/to/yolov5-v7.0
.venv/bin/python "$YOLOV5_SOURCE/export.py" \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --imgsz 640 640 --batch-size 1 --device cpu \
  --include onnx --opset 12
```

Do not add `--simplify`, `--dynamic`, `--half`, or graph NMS. For ncnn, follow
Task 010's fixed CPU/FP32 chain using the same weights: TorchScript export, pnnx
from ncnn tag `20240410` revision
`56775de50990ab7f16627efdcf5529b49541206f`, `inputshape=[1,3,640,640]f32`,
`device=cpu`, `fp16=0`, and `optlevel=2`. The manifests and Task 010 validators
must reproduce the recorded SHA256 values before inference. Do not substitute a
different model, pnnx revision, input size, precision, or threshold.

## Build

```bash
export ONNXRUNTIME_ROOT=/path/to/onnxruntime-linux-x64-1.18.1
export NCNN_ROOT=/path/to/ncnn-linux-x64-20240410-local
cmake -S cpp -B build/pc-acceptance-release -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT="$ONNXRUNTIME_ROOT" \
  -DNCNN_ROOT="$NCNN_ROOT"
cmake --build build/pc-acceptance-release --parallel
ctest --test-dir build/pc-acceptance-release --output-on-failure
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py' -v
```

## Single-image and video commands

```bash
mkdir -p build/reproduction
PYTHONPATH=python .venv/bin/python python/apps/ort_image.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/python_ort_reference.png \
  --output-json build/reproduction/python_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_image \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/cpp_ort_reference.png \
  --output-json build/reproduction/cpp_ort_reference.json

./build/pc-acceptance-release/edgeai_ort_video \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output build/reproduction/cpp_ort_reference.mp4 \
  --output-json build/reproduction/cpp_ort_video.json

./build/pc-acceptance-release/edgeai_ncnn_image \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image build/reproduction/cpp_ncnn_reference.png \
  --output-json build/reproduction/cpp_ncnn_reference.json

./build/pc-acceptance-release/edgeai_ncnn_video \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --input data/samples/videos/pc_reference.mp4 \
  --output build/reproduction/cpp_ncnn_reference.mp4 \
  --output-json build/reproduction/cpp_ncnn_video.json
```

These reproduction outputs stay under the Git-ignored build tree and do not
overwrite approved evidence. The known low-confidence second `mouse` on the
earbud case is retained as a model false positive; it is not hidden with
threshold or coordinate rules.

## Task 012 benchmark method

Six rounds execute all permutations of Python ORT, C++ ORT, and C++ ncnn. Every
backend appears twice in each position. Every invocation is an independent
process with 10 warmups and 100 formal iterations, yielding 600 samples per
backend. Every formal iteration performs preprocess, inference, and postprocess.

Pipeline total is the exact unrounded sum of those stages. It excludes image
read, model/runtime load, drawing, labels, writes, video decode, and encoding.
Pipeline FPS is `1000 / aggregate mean pipeline_total_ms`, not a mean of per-run
FPS and not video application throughput. P50/P90 use nearest-rank.

To reproduce the campaign without overwriting the approved Task 012 files, use
new paths under the Git-ignored build tree:

```bash
mkdir -p build/reproduction/benchmark
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
PYTHONPATH=python .venv/bin/python scripts/generate_pc_acceptance.py run-campaign \
  --config configs/benchmark_pc_three_backend.json \
  --base-config configs/benchmark_pc.json \
  --python .venv/bin/python \
  --python-benchmark python/apps/benchmark_ort.py \
  --cpp-ort build/pc-acceptance-release/edgeai_benchmark_ort \
  --cpp-ncnn build/pc-acceptance-release/edgeai_benchmark_ncnn \
  --ncnn-manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --reference-detections results/evidence/007/cpp_ort_detections.json \
  --python-output build/reproduction/benchmark/python_ort.json \
  --cpp-ort-output build/reproduction/benchmark/cpp_ort.json \
  --cpp-ncnn-output build/reproduction/benchmark/cpp_ncnn.json \
  --summary build/reproduction/benchmark/summary.json \
  --csv build/reproduction/benchmark/summary.csv \
  --validation build/reproduction/benchmark/validation.json \
  --log build/reproduction/benchmark/campaign.log
```

This command intentionally launches a new campaign; its outputs are not the
approved data below and must not replace files under `results/benchmarks/`.

### Final PC performance — campaign approved

| Backend | Pipeline mean (ms) | P50 | P90 | Min | Max | Pipeline FPS | Six-round spread | Position spread |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Python ORT | 54.881306 | 54.640382 | 56.898155 | 51.590660 | 65.453303 | 18.221141 | 3.098913% | 1.156671% |
| C++ ORT | 51.802986 | 51.595426 | 53.627128 | 48.863992 | 65.671301 | 19.303907 | 3.221212% | 1.383173% |
| C++ ncnn | 77.865349 | 77.618684 | 80.776143 | 73.478461 | 85.075339 | 12.842683 | 1.727134% | 0.438557% |

### Stage means

| Backend | Preprocess mean (ms) | Inference mean (ms) | Postprocess mean (ms) | Pipeline mean (ms) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 3.356562 | 45.898201 | 5.626543 | 54.881306 |
| C++ ORT | 1.833570 | 45.849137 | 4.120279 | 51.802986 |
| C++ ncnn | 1.815537 | 71.941530 | 4.108283 | 77.865349 |

Under this fixed WSL2 configuration, C++ ORT has the lowest complete-
pipeline mean at `51.802986 ms`, which is `5.61%`
lower than Python ORT. Python ORT and C++ ORT inference means are
`45.898201 ms` and
`45.849137 ms`, a difference of about
`0.11%`; the observed C++ pipeline advantage is
therefore concentrated in this implementation's preprocess and postprocess
overheads, not evidence that C++ or the ORT inference kernel is universally
faster.

C++ ncnn records `77.865349 ms`, `50.31%` above
C++ ORT for the complete pipeline. Its inference mean is
`71.941530 ms`, `56.91%`
above C++ ORT in this campaign. This is specific to the fixed x86 CPU, WSL2,
runtime versions, model-conversion path, build, and input; it predicts neither
another PC nor ARM behavior.

### Running-position effect

| Backend | Position 1 mean (ms) | Position 2 mean (ms) | Position 3 mean (ms) | Position spread |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 54.472042 | 55.102104 | 55.069772 | 1.156671% |
| C++ ORT | 52.163539 | 51.451871 | 51.793547 | 1.383173% |
| C++ ncnn | 77.956484 | 77.649513 | 77.990051 | 0.438557% |

Every position group contains 200 samples. All round spreads are below 3.3% and
all position spreads are below 1.4%; the execution position did not change the
backend ranking in this campaign. Position spread is diagnostic and no sample
was removed because of it.

### Model load, CPU, and Peak RSS

| Backend | Model load range (ms) | Process CPU range (%) | Peak RSS range (bytes) | Peak RSS range (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Python ORT | 27.340525–34.602837 | 99.942096–99.972122 | 178225152–181420032 | 170.0–173.0 |
| C++ ORT | 53.144442–54.676551 | 99.996220–100.000091 | 153935872–155078656 | 146.8–147.9 |
| C++ ncnn | 30.798871–32.886271 | 99.988997–99.998528 | 187768832–188178432 | 179.1–179.5 |

All 1,800 samples and outliers are preserved. The table applies only to this
fixed WSL2 environment, code, model lineage, input, thread configuration, and
campaign. It is not a universal language/runtime ranking and cannot be projected
to bare-metal Linux, another PC, or ARM.

## Correctness

Python/C++ ORT use the frozen golden tolerances. ncnn matches ORT at the
pre-registered target of class-matched IoU at least 0.99 and confidence delta at
most 0.01. Each formal process performs untimed checks before warmup and after
measurement. The approved final values are minimum IoU `0.999999982537` and
maximum confidence delta `1.64833068306e-08` for Python/C++ ORT, and minimum IoU
`0.999997080011` and maximum delta `2.02655792236e-06` for C++ ORT/ncnn. The
three annotated images are human-approved and byte-identical with SHA256
`57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2`.

## CPU and memory definitions

`process_cpu_percent_one_core_basis` is 100 times process CPU-time delta divided
by wall-time delta. About 100% represents sustained use of one logical CPU;
values above 100% can reflect auxiliary Runtime or system activity. A configured
thread count of 1 does not mean the process owns exactly one OS thread.

Peak RSS is the complete process peak, not model-only memory. Python includes the
interpreter/modules; C++ includes executable and linked-library costs; every
backend includes its Runtime, model, and input state.

## Evidence, limitations, and reproduction

- Benchmark summary: `results/benchmarks/pc_three_backend_summary.json` and CSV.
- Validation: `results/evidence/012/three_backend_benchmark_validation.json`.
- Approved annotated outputs: `results/acceptance/python_ort_reference.png`,
  `results/acceptance/cpp_ort_reference.png`, and
  `results/acceptance/cpp_ncnn_reference.png`.
- PC acceptance: `docs/pc_stage_acceptance.md` and
  `results/evidence/012/pc_acceptance.json`.
- Task 009/011 campaigns remain immutable historical evidence and are not used as
  substitute rows in the Task 012 main table.
- WSL2 scheduling, frequency/thermal state, background activity, unpinned CPU,
  distinct OpenCV versions, and distinct ONNX/ncnn serialized graphs limit causal
  attribution.
- Generated models, SDKs, logs, videos, and other large reproducible artifacts
  remain Git-ignored. Reproduction requires the exact recorded hashes and local
  tool versions.

## Next stage

Checkpoint C is approved, but Stage 2 remains `Not implemented / Planned` and
requires separate authorization before work begins. No ARM build, deployment,
compatibility, or performance result exists yet.
