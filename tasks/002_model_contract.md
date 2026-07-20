# Task 002

## Title

Freeze the YOLOv5n v7.0 model manifest, ONNX export constraints, and model contract.

## Status

Planned

## Batch

Batch A

## Dependencies

Task 001 (`Completed`).

## Recommended Branch

`feature/pc-batch-a-python-baseline`

## Recommended Commit

`feat(model): freeze YOLOv5n v7.0 ONNX contract`

## Goal

Create an auditable manifest for one real YOLOv5n v7.0 model and freeze its
verified ONNX interface before any runtime integration begins.

## Why This Task Exists

Later Python, C++ ONNX Runtime, and ncnn results are comparable only if they use
the same source weights, export settings, graph, input dimensions, and interface.
This task prevents downstream code from silently adapting to a different model.

## Knowledge Covered

- Model provenance and cryptographic identity.
- Reproducible ONNX export constraints.
- Static versus dynamic tensor dimensions.
- ONNX graph inputs, outputs, dtypes, and NMS placement.
- Separation of observed facts from expected configuration.

## Scope

Freeze YOLOv5n from the upstream YOLOv5 v7.0 release with batch 1, FP32,
NCHW input, a default spatial size of 640 by 640, ONNX opset 12, graph-internal
NMS disabled, dynamic axes disabled, and first-pass simplification disabled.
Record the real source location, source revision, source-weight SHA256, exported
ONNX SHA256, file sizes, export command, and inspected graph contract.

Do not implement preprocessing, inference, decoding, or visualization.

## Allowed Files

```text
TASKS.md
tasks/002_model_contract.md
docs/model_contract.md
models/yolov5n-v7.0/manifest.json
models/yolov5n-v7.0/yolov5n.pt
models/yolov5n-v7.0/yolov5n.onnx
scripts/inspect_onnx_contract.py
tests/python/test_model_contract.py
results/evidence/002/model_contract.json
results/logs/002_model_contract.log
```

The `.pt` and `.onnx` artifacts are local inputs/outputs and must remain ignored
and uncommitted. Only the small manifest, contract, checker, test, task record,
and genuine text evidence may be committed.

## Forbidden Files

- Task 001 files or evidence.
- Python or C++ inference applications.
- Runtime backend adapters.
- ncnn artifacts.
- Benchmark results.
- Vendored YOLOv5 or other third-party source.
- Any file outside Allowed Files.

## Inputs

- A user-provided local clone or working tree of upstream `ultralytics/yolov5`
  exactly at tag `v7.0`; Codex must not download it.
- The real `yolov5n.pt` associated with YOLOv5 v7.0, supplied locally by the
  user with a trustworthy source reference.
- A Python environment that already contains exporter dependencies and an ONNX
  graph-inspection package.

If any input is absent, its source is ambiguous, or environment modification is
needed, stop without exporting.

## Expected Outputs

- `manifest.json` containing provenance, exact version/tag, both SHA256 values,
  byte sizes, export constraints, export command, and inspection timestamp.
- `model_contract.md` documenting only interface values observed from the real
  exported graph.
- Machine-readable graph inspection evidence and a real command log.
- A local FP32 ONNX graph produced without NMS or simplification.

The final input name, output name or names, output dimensions, and candidate-box
count are deliberately unresolved until inspection; they must not be guessed or
pre-filled as final values.

## Implementation Requirements

- Identify the model as `YOLOv5n v7.0` and record the canonical upstream source
  reference and exact local source revision.
- Hash the source weights before export and the ONNX model after export using
  SHA256.
- Use `imgsz=640 640`, `batch-size=1`, FP32, static NCHW, and opset 12.
- Do not enable `--half`, `--dynamic`, `--simplify`, or graph-internal NMS.
- Preserve the exact exporter command and actual exporter/library versions.
- Inspect the real ONNX graph for input/output names, shapes, dtypes, opset, and
  NMS nodes. A checker may reject unknown or symbolic dimensions, but may not
  invent replacements.
- Record class-label provenance and the expected 80-class COCO label set without
  treating label metadata as proof of output shape.
- Treat any graph with embedded NMS, any unverified provenance, or any contract
  mismatch as a mandatory stop.

## Build Commands

Run from the repository root after the checker has been implemented:

```bash
python3 -m py_compile scripts/inspect_onnx_contract.py
```

## Run Commands

The exact verified local YOLOv5 checkout path must be recorded in the Execution
Record. From that checkout, use its v7.0 exporter without download-related flags:

```bash
mkdir -p models/yolov5n-v7.0 results/evidence/002 results/logs
sha256sum models/yolov5n-v7.0/yolov5n.pt
python3 <verified-yolov5-v7.0-path>/export.py \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --imgsz 640 640 \
  --batch-size 1 \
  --device cpu \
  --include onnx \
  --opset 12
sha256sum models/yolov5n-v7.0/yolov5n.onnx
python3 scripts/inspect_onnx_contract.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --write-manifest \
  --output results/evidence/002/model_contract.json \
  2>&1 | tee results/logs/002_model_contract.log
```

No `--simplify`, `--dynamic`, `--half`, or NMS option may be added. If the
verified v7.0 exporter uses different option spelling, stop and document it
instead of improvising a different export strategy.

## Test Commands

```bash
python3 -m unittest tests/python/test_model_contract.py
python3 scripts/inspect_onnx_contract.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --check-only
git diff --check
```

## Acceptance Criteria

- The source is proven to be YOLOv5n v7.0 and provenance is recorded.
- Source-weight and ONNX SHA256 values are computed from local real files.
- The exported model is batch 1, FP32, NCHW, static 640 by 640, opset 12.
- Simplification and graph-internal NMS are confirmed disabled by real inspection.
- Actual input/output names, shapes, and dtypes are recorded from the graph.
- No final output name or candidate count was assumed before inspection.
- The manifest checker and its tests pass.
- Required commands and real summaries are preserved.
- No model binary is staged for commit.
- `git diff --check` passes and only Allowed Files changed.

## Evidence to Preserve

- Source tag/revision and provenance reference.
- Exporter and dependency versions.
- Exact export command and exit code.
- Source and ONNX SHA256 values and byte sizes.
- Real graph I/O, opset, node-level NMS check, and checker/test output.
- Final Git status and diff check.

## Automatic Retry Rules

At most three complete diagnose-modify-rebuild-retest-rerun attempts are allowed
for checker or manifest bugs. A missing dependency, export failure caused by the
environment, provenance ambiguity, or graph-contract mismatch is not recoverable
automatically and requires an immediate stop.

## Human Stop Conditions

Stop for every model-contract condition in the PC protocol, and whenever the
model/exporter must be downloaded, the v7.0 revision cannot be proven, the graph
contains NMS, or a different opset/input size/export option appears necessary.

## Codex Responsibilities

Verify rather than guess; create only Allowed Files; keep binaries uncommitted;
record commands and hashes; update status only after real acceptance; and issue
the full Blocking Report when stopped.

## User Responsibilities

Supply the trusted local v7.0 source and weights, confirm licensing/provenance,
inspect the frozen contract and hashes, and approve Checkpoint A only after Task
005. The user performs any needed environment installation or download.

## Known Risks

- Upstream exporter dependencies may be absent or incompatible.
- A file named `yolov5n.pt` may not actually match v7.0.
- Exporter updates or option differences can change names or graph structure.
- ONNX shape inference may expose symbolic dimensions requiring human review.

## Completion Report Format

Report changed files; provenance; versions; exact export and inspection commands;
hashes and sizes; observed I/O contract; NMS/simplify findings; test results;
skips; attempts; risks; and final Git status. Label each item passed, failed,
environment-blocked, or static-only.

## Execution Record

Not started. Do not add expected tensor names, shapes, hashes, or model sizes here.
