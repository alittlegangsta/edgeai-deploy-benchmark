# Task 002

## Title

Freeze the YOLOv5n v7.0 model manifest, ONNX export constraints, and model contract.

## Status

Completed

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
source .venv/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/dministrator/src/yolov5-v7.0
export YOLOv5_CONFIG_DIR=/tmp/edgeai-yolov5-config
export MPLCONFIGDIR=/tmp/edgeai-matplotlib-config
mkdir -p models/yolov5n-v7.0 results/evidence/002 results/logs
sha256sum models/yolov5n-v7.0/yolov5n.pt
python3 /home/dministrator/src/yolov5-v7.0/export.py \
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
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --source-path /home/dministrator/src/yolov5-v7.0 \
  --export-command "python3 /home/dministrator/src/yolov5-v7.0/export.py --weights models/yolov5n-v7.0/yolov5n.pt --imgsz 640 640 --batch-size 1 --device cpu --include onnx --opset 12" \
  --output results/evidence/002/model_contract.json \
  --contract docs/model_contract.md \
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

Started: `2026-07-20T15:24:25+08:00`

Branch: `feature/pc-batch-a-python-baseline`

Starting commit: `d5bd28d`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output).

Current step: checking the local Task 002 inputs and environment. No tensor name,
shape, hash, model size, or model-contract result has been recorded yet.

Blocked: `2026-07-20T15:26:02+08:00`

Environment observed:

```text
Python 3.12.3
torch: unavailable (ModuleNotFoundError)
onnx: unavailable (ModuleNotFoundError)
cv2: unavailable (ModuleNotFoundError)
```

Input checks:

```text
models/yolov5n-v7.0/yolov5n.pt: missing
models/yolov5n-v7.0/yolov5n.onnx: missing
repository-local YOLOv5 export.py: not found
```

No repair attempt was made because obtaining the model/exporter or installing
packages is a mandatory human stop, not an implementation defect.

## Blocking Report

```text
Current Task: Task 002 - Freeze the YOLOv5n v7.0 model contract
Current Status: Blocked
Last Successful Step: Selected Task 002, verified Batch A branch/dependency, marked it In Progress, and recorded Python 3.12.3.
Failed Command: test -f models/yolov5n-v7.0/yolov5n.pt
Exit Code: 1
Relevant Error: Required yolov5n.pt and yolov5n.onnx are absent; no local YOLOv5 export.py was found; imports of torch, onnx, and cv2 each failed with ModuleNotFoundError.
Files Changed: TASKS.md; tasks/002_model_contract.md
Attempts Made: 0 repair attempts; the initial read-only environment/input audit triggered mandatory stop conditions.
Why Automatic Recovery Is Unsafe: Recovery requires trusted model/source acquisition and Python package installation or environment activation, all prohibited for Codex; model provenance cannot be inferred.
Exact Human Action Required: Provide a trusted YOLOv5 v7.0 checkout and its exact path; place the trusted v7.0 yolov5n.pt at models/yolov5n-v7.0/yolov5n.pt; explicitly authorize read access to the checkout path; and provide/activate a Python environment where torch, onnx, and cv2 import successfully. If installation is needed, the user must perform it and preserve the exact commands/version output.
Commands to Resume: git branch --show-current; git status --short --untracked-files=all; test -f models/yolov5n-v7.0/yolov5n.pt; git -C <authorized-yolov5-v7.0-path> describe --tags --exact-match; python3 -c 'import torch, onnx, cv2; print(torch.__version__, onnx.__version__, cv2.__version__)'
Git Status: TASKS.md and tasks/002_model_contract.md modified; no other paths changed.
```

If the user needs to create an isolated environment, the commands below are for
the user to run, not Codex. They create `.venv/` and may download/install Python
packages, so exact resolved versions and output must be retained:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r /absolute/path/to/verified/yolov5-v7.0/requirements.txt
python3 -m pip install onnx
python3 -c 'import torch, onnx, cv2; print(torch.__version__, onnx.__version__, cv2.__version__)'
```

The model must be supplied from a source the user trusts. After obtaining it,
place it without changing bytes and verify the local file before resume:

```bash
mkdir -p models/yolov5n-v7.0
cp /absolute/path/to/trusted/yolov5n.pt models/yolov5n-v7.0/yolov5n.pt
sha256sum models/yolov5n-v7.0/yolov5n.pt
```

These commands modify `.venv/` and the ignored local model path. They are needed
to provide the exporter runtime, ONNX graph inspection support, and the real
source artifact. Successful imports, an exact `v7.0` tag check, file existence,
and the real SHA256 are the required verification before recovery.

## Recovery Audit: 2026-07-20T15:53:24+08:00

The user-rebuilt project environment was verified from the repository shell. The
environment portion of the previous blocker is resolved:

```text
python executable: /home/dministrator/projects/edgeai-deploy-benchmark/.venv/bin/python
Python: 3.12.3
pip check: No broken requirements found.
torch: 2.2.2+cpu
torchvision: 0.17.2+cpu
numpy: 1.26.4
scipy: 1.12.0
onnx: 1.16.2
opencv-python: 4.10.0
torch CUDA available: False
all imported module paths under project .venv: PASS
```

The exact failed command from the earlier Blocking Report was rerun and still
failed:

```text
command: test -f models/yolov5n-v7.0/yolov5n.pt
exit code: 1
```

Repository-local checks also found no `yolov5n.onnx` and no `export.py`. The ONNX
file is not expected until the task export runs, but the trusted source weight and
an authorized verifiable YOLOv5 v7.0 checkout remain required inputs.

Two user-created untracked files were present but are not in Task 002 Allowed
Files, so Codex did not modify, delete, stage, or treat them as accepted evidence:

```text
results/logs/002_pip_check.txt
results/logs/002_python_environment_freeze.txt
```

### Recovery Blocking Report

```text
Current Task: Task 002 - Freeze the YOLOv5n v7.0 model contract
Current Status: Blocked
Last Successful Step: Verified the rebuilt project .venv, exact frozen package versions, pip check, CPU-only PyTorch state, and that all imported modules load from the project .venv.
Failed Command: test -f models/yolov5n-v7.0/yolov5n.pt
Exit Code: 1
Relevant Error: The trusted source weight is still absent; no repository-local YOLOv5 export.py exists; no external YOLOv5 v7.0 checkout path/read authorization was provided; two untracked environment logs are outside Allowed Files.
Files Changed: TASKS.md and tasks/002_model_contract.md remain the legitimate blocked-state changes; user-created results/logs/002_pip_check.txt and results/logs/002_python_environment_freeze.txt are untracked and untouched.
Attempts Made: 0 repair attempts; 1 recovery audit. The failed command was rerun exactly once and still returned 1.
Why Automatic Recovery Is Unsafe: Codex cannot acquire or guess the official model/source, read an unspecified external checkout, delete user files, or expand Allowed Files to absorb after-the-fact evidence.
Exact Human Action Required: Place the trusted YOLOv5n v7.0 weight at models/yolov5n-v7.0/yolov5n.pt; provide the exact local YOLOv5 checkout path and explicitly authorize Codex to read it; ensure its exact tag is v7.0; and remove or otherwise resolve the two unlisted logs so the worktree contains only Allowed Files.
Commands to Resume: source .venv/bin/activate; test -f models/yolov5n-v7.0/yolov5n.pt; sha256sum models/yolov5n-v7.0/yolov5n.pt; git -C <authorized-yolov5-v7.0-path> describe --tags --exact-match; git status --short --untracked-files=all
Git Status: TASKS.md and tasks/002_model_contract.md modified; results/logs/002_pip_check.txt and results/logs/002_python_environment_freeze.txt untracked.
```

## Recovery Resumed: 2026-07-20T16:01:25+08:00

The second recovery audit satisfied every recorded human action without erasing
the earlier Blocked history:

```text
branch: feature/pc-batch-a-python-baseline
worktree changes: TASKS.md and tasks/002_model_contract.md only
Python: 3.12.3
torch: 2.2.2+cpu
torchvision: 0.17.2+cpu
numpy: 1.26.4
scipy: 1.12.0
onnx: 1.16.2
opencv-python: 4.10.0
pip check: PASS
YOLOv5 tag: v7.0
YOLOv5 revision: 915bbf294bb74c859f0b41f1c23bc395014ea679
YOLOv5 worktree: clean before and after checkpoint loading
YOLOv5 path: /home/dministrator/src/yolov5-v7.0 (read-only authorization)
source weights size: 4062133 bytes
source weights SHA256: 4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3
source weights ignored by Git: PASS
checkpoint CPU load: PASS
loaded model type: models.yolo.DetectionModel
loaded model device: cpu
loaded model dtype: torch.float32
observed class count: 80
observed parameter count: 1872157
```

Task 002 is restored to `In Progress`. No ONNX input/output name, output shape,
candidate count, opset result, or graph NMS conclusion has been assumed; those
remain pending real export and inspection.

## Completion Record: 2026-07-20T16:11:00+08:00

Task 002 completed after real export and inspection. Earlier Blocked and recovery
records above remain preserved as execution history.

### Actual Environment and Source

```text
Python: 3.12.3
torch: 2.2.2+cpu
torchvision: 0.17.2+cpu
numpy: 1.26.4
scipy: 1.12.0
onnx: 1.16.2
opencv-python: 4.10.0
YOLOv5 origin: https://github.com/ultralytics/yolov5.git
YOLOv5 tag: v7.0
YOLOv5 revision: 915bbf294bb74c859f0b41f1c23bc395014ea679
YOLOv5 worktree before/after export: clean
official weight reference recorded by v7.0 README: https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt
```

### Actual Artifact Identity

```text
source weights size: 4062133 bytes
source weights SHA256: 4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3
ONNX size: 7921360 bytes
ONNX SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
manifest SHA256: 764f3e4980c1f6b18ea245262af99703d13e817fedc52bf97bbfc5a1389f06c2
machine evidence SHA256: fdd98109ec870fa662318d3f25fb5a321190d39fd539446356cfbb93ef69c047
run log SHA256: 9d385e03d5acf2d2a4e80adf5719a2165affd7a83ecf237b4822990ae9b3a0d9
```

### Actual Export and Contract

```text
export command: python3 /home/dministrator/src/yolov5-v7.0/export.py --weights models/yolov5n-v7.0/yolov5n.pt --imgsz 640 640 --batch-size 1 --device cpu --include onnx --opset 12
export exit code: 0
exporter flags: half=False, dynamic=False, simplify=False, nms=False, agnostic_nms=False
input: name=images, shape=[1, 3, 640, 640], dtype=FLOAT
output: name=output0, shape=[1, 25200, 85], dtype=FLOAT
observed class count: 80
default ONNX opset: 12
ONNX node count: 292
graph contains NMS: False
ONNX checker: PASS
contract validation: PASS
```

The input/output names, shapes, candidate dimension, class count, opset, and NMS
finding above were recorded only after the real exporter and ONNX checker ran.

### Commands and Tests

```text
python3 -m py_compile scripts/inspect_onnx_contract.py: PASS
python3 -m unittest tests/python/test_model_contract.py: PASS (8 tests)
YOLOv5 CPU ONNX export: PASS
manifest/evidence/contract generation: PASS
manifest --check-only validation: PASS
manifest and evidence JSON parsing: PASS
git diff --check: PASS
external YOLOv5 worktree post-run: clean
```

Repair attempts: `0`. The provenance refinement was made before acceptance and
did not respond to a build, test, export, or validation failure.

Skipped required checks: none. No inference, detection, visualization, or
benchmark was run because each is outside Task 002.

The source `.pt`, generated `.onnx`, and `.log` remain ignored. Neither model
binary will be staged or committed. The local atomic commit hash is reported by
Git immediately after the content-addressed commit is created; it cannot be
self-referentially embedded in the commit that contains this record.
