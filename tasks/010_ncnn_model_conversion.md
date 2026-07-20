# Task 010

## Title

Convert the frozen ONNX model to ncnn and verify model loading.

## Status

Planned

## Batch

Batch C

## Dependencies

Task 009 (`Completed`) and human approval of Checkpoint B.

## Recommended Branch

`feature/pc-batch-c-ncnn-acceptance`

## Recommended Commit

`feat(ncnn): add reproducible model conversion`

## Goal

Use one explicitly identified local ncnn converter to transform the exact frozen
ONNX graph, record every artifact identity, and prove the generated param/bin pair
loads with the matching local ncnn runtime before implementing inference.

## Why This Task Exists

Conversion is a separate source of graph, blob-name, layout, precision, and
version drift. Isolating it prevents inference code from hiding a converter or
model incompatibility.

## Knowledge Covered

- Converter/runtime version identity.
- Reproducible model transformation and artifact hashing.
- ncnn param/bin structure and blob discovery.
- Native model-load error handling.
- Traceability back to a frozen ONNX source.

## Scope

Convert only the Task 002 ONNX model with the locally available `onnx2ncnn` tool
from the same pinned ncnn build used at runtime. Record converter/runtime source
revision or package version, executable SHA256, command, source/artifact hashes,
byte sizes, and observed input/output blob names. Build a load-only C++ smoke test.

Do not run inference, optimize the graph with another tool, quantize, change
precision, simplify/re-export ONNX, or replace the source model.

## Allowed Files

```text
TASKS.md
tasks/010_ncnn_model_conversion.md
cpp/CMakeLists.txt
cpp/apps/ncnn_model_smoke.cpp
models/yolov5n-v7.0/yolov5n.ncnn.param
models/yolov5n-v7.0/yolov5n.ncnn.bin
models/yolov5n-v7.0/ncnn_manifest.json
scripts/validate_ncnn_conversion.py
tests/python/test_ncnn_manifest.py
results/evidence/010/ncnn_model_load.json
results/logs/010_ncnn_conversion.log
```

The ONNX graph and Task 002 manifest/contract are read-only. The generated ncnn
binary remains ignored and uncommitted; committing the small param file requires
user confirmation and license review.

## Forbidden Files

- Changes to the source `.pt`, `.onnx`, Task 002 manifest/contract, or hashes.
- Downloaded/vendored ncnn, alternate converters, graph optimizers, quantizers,
  inference code, detections, images, video, or benchmark results.
- Silent blob renaming or hand-editing converted artifacts.
- Any file outside Allowed Files.

## Inputs

- The frozen Task 002 ONNX graph with matching SHA256.
- A user-provided compatible local ncnn installation and `onnx2ncnn` executable
  whose exact version/revision and relationship to the runtime can be proven.
- Existing C++17/CMake/Ninja/OpenCV toolchain.

If ncnn/converter is absent or incompatible, stop; do not download, build, install,
or choose a different converter automatically.

## Expected Outputs

- Generated ncnn param/bin artifacts tied to the frozen ONNX SHA.
- `ncnn_manifest.json` with ncnn/converter identities, commands, hashes, sizes,
  conversion settings, and observed blob contract.
- `edgeai_ncnn_model_smoke` that loads both files without executing inference.
- Real validation/load JSON and log.

## Implementation Requirements

- Validate the ONNX SHA against Task 002 immediately before conversion and again
  when creating the ncnn manifest.
- Record ncnn runtime and converter version/revision, paths, binary SHA256 values,
  build/compiler information when available, and exact conversion command.
- Require the converter and linked runtime to come from the same pinned ncnn
  version/build; stop if this cannot be established.
- Invoke only `onnx2ncnn <frozen.onnx> <output.param> <output.bin>` unless the
  pinned tool's verified interface differs, in which case stop for approval.
- Do not run `ncnnoptimize`, quantization, FP16 conversion, or ONNX re-export.
- Hash and size the generated param/bin. Validate that paths are regular files,
  nonempty, and not symlinks escaping the repository.
- Parse the generated param as evidence but do not edit it. Observe rather than
  guess input/output blob names and relevant shapes.
- The smoke executable must validate manifest/source/artifact hashes, call ncnn
  load APIs, report actual blob/model metadata available from the pinned runtime,
  and return nonzero on every mismatch/load failure.
- Keep ncnn discovery target-level and fail clearly without dependency fetching.

## Build Commands

```bash
rm -rf build/pc-ncnn-release
cmake \
  -S cpp \
  -B build/pc-ncnn-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DNCNN_ROOT=<verified-local-ncnn-root>
cmake --build build/pc-ncnn-release --parallel
```

## Run Commands

```bash
mkdir -p models/yolov5n-v7.0 results/evidence/010 results/logs
sha256sum models/yolov5n-v7.0/yolov5n.onnx
<verified-onnx2ncnn-path> \
  models/yolov5n-v7.0/yolov5n.onnx \
  models/yolov5n-v7.0/yolov5n.ncnn.param \
  models/yolov5n-v7.0/yolov5n.ncnn.bin \
  2>&1 | tee results/logs/010_ncnn_conversion.log
python3 scripts/validate_ncnn_conversion.py \
  --onnx models/yolov5n-v7.0/yolov5n.onnx \
  --onnx-manifest models/yolov5n-v7.0/manifest.json \
  --param models/yolov5n-v7.0/yolov5n.ncnn.param \
  --bin models/yolov5n-v7.0/yolov5n.ncnn.bin \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json
./build/pc-ncnn-release/edgeai_ncnn_model_smoke \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json \
  --output results/evidence/010/ncnn_model_load.json
```

## Test Commands

```bash
python3 -m unittest tests/python/test_ncnn_manifest.py
python3 -m json.tool models/yolov5n-v7.0/ncnn_manifest.json >/dev/null
python3 -m json.tool results/evidence/010/ncnn_model_load.json >/dev/null
ctest --test-dir build/pc-ncnn-release --output-on-failure
git diff --check
```

## Acceptance Criteria

- Frozen ONNX SHA matches Task 002 immediately before conversion.
- ncnn runtime and `onnx2ncnn` are pinned to one proven version/build, with real
  version/path/executable-hash evidence.
- Exact conversion command succeeds without alternate model, optimizer,
  simplification, quantization, or precision change.
- Generated param/bin are nonempty and have recorded SHA256 and byte sizes.
- Actual input/output blob names are observed and recorded, not guessed or edited.
- Release smoke target builds without warnings and loads both artifacts.
- Manifest validation, smoke load, tests, and `git diff --check` pass.
- No inference/detection/benchmark is run and no model binary is staged.
- Only Allowed Files changed.

## Evidence to Preserve

Source ONNX hash, converter/runtime version/revision/path/hash, exact command and
exit, param/bin hashes and sizes, observed blobs, Release configure/build output,
load output, tests, attempts, diff check, and Git status.

## Automatic Retry Rules

At most three complete repair loops may address manifest/checker/smoke-code bugs.
Do not retry by changing converter, source ONNX, opset, optimization, precision,
or generated artifacts manually. Dependency/version/conversion/blob ambiguity is
an immediate mandatory stop.

## Human Stop Conditions

Stop for all model-contract/environment/file-safety conditions, any converter and
runtime mismatch, changed ONNX hash, unexpected blobs, need for optimization or
manual param editing, or any proposal to commit a large binary.

## Codex Responsibilities

Prove tool and model identity, run exactly one approved transformation, avoid
inference, validate/load outputs, preserve actual evidence, and report incompatibility.

## User Responsibilities

Provide and identify the local pinned ncnn tool/runtime, resolve installation or
version problems, review artifact licensing/commit policy, and inspect blob evidence.

## Known Risks

- `onnx2ncnn` compatibility varies by ncnn revision and ONNX operators.
- Tool binaries may not expose a machine-readable version.
- Conversion can succeed while producing an unusable graph.
- Generated blob names may differ from ONNX names.

## Completion Report Format

Report files, frozen source hash, ncnn/converter identity, conversion command,
artifact hashes/sizes/blobs, build/load/tests, staged-binary check, attempts,
stops/skips, risks, and final Git status.

## Execution Record

Not started. No ncnn version, conversion artifact, blob name, or load result exists.
